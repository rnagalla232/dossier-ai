#!/usr/bin/env bash
set -euo pipefail

# Default behavior: install and initialize a single-node control-plane with Flannel
INSTALL_ONLY=false
POD_CIDR="10.244.0.0/16"   # Works with Flannel out of the box
K8S_SERIES="v1.30"         # Stable series repo (adjust to pin a different minor)

if [[ "${1:-}" == "--install-only" ]]; then
  INSTALL_ONLY=true
fi

require_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "Please run as root (use sudo)." >&2
    exit 1
  fi
}

detect_os() {
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    OS_ID=$ID
    OS_CODENAME=${VERSION_CODENAME:-}
  else
    echo "Cannot detect OS." >&2
    exit 1
  fi

  if [[ "$OS_ID" != "ubuntu" && "$OS_ID" != "debian" ]]; then
    echo "This script targets Ubuntu/Debian. Detected: $OS_ID" >&2
    exit 1
  fi
}

disable_swap() {
  echo "Disabling swap..."
  swapoff -a || true
  # Comment out any swap entries in /etc/fstab
  sed -ri 's/^\s*([^#]\S*\s+\S+\s+swap\s+\S+.*)$/# \1/' /etc/fstab || true
}

kernel_prep() {
  echo "Configuring kernel modules and sysctls for Kubernetes networking..."
  cat >/etc/modules-load.d/k8s.conf <<EOF
overlay
br_netfilter
EOF

  modprobe overlay
  modprobe br_netfilter

  cat >/etc/sysctl.d/99-kubernetes-cri.conf <<EOF
net.bridge.bridge-nf-call-iptables = 1
net.bridge.bridge-nf-call-ip6tables = 1
net.ipv4.ip_forward = 1
EOF
  sysctl --system
}

install_base_tools() {
  apt-get update
  apt-get install -y ca-certificates curl gnupg lsb-release apt-transport-https
  install -m 0755 -d /etc/apt/keyrings
}

install_docker_engine() {
  echo "Installing Docker Engine..."
  if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
    curl -fsSL https://download.docker.com/linux/${OS_ID}/gpg \
      | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
  fi

  echo \
"deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${OS_ID} ${OS_CODENAME} stable" \
    >/etc/apt/sources.list.d/docker.list

  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

  # Docker daemon: use systemd cgroups for better k8s compatibility
  mkdir -p /etc/docker
  cat >/etc/docker/daemon.json <<'EOF'
{
  "exec-opts": ["native.cgroupdriver=systemd"],
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m"
  },
  "storage-driver": "overlay2"
}
EOF
  systemctl enable docker
  systemctl daemon-reload
  systemctl restart docker
}

install_containerd_and_configure() {
  echo "Ensuring containerd is configured for Kubernetes..."
  # containerd is already installed as docker dependency, but we configure it explicitly
  mkdir -p /etc/containerd
  containerd config default >/etc/containerd/config.toml

  # Set SystemdCgroup = true
  sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

  systemctl enable containerd
  systemctl restart containerd
}

install_kubernetes_binaries() {
  echo "Installing Kubernetes (kubelet/kubeadm/kubectl)..."
  # New upstream repo (pkgs.k8s.io)
  if [[ ! -f /etc/apt/keyrings/kubernetes-archive-keyring.gpg ]]; then
    curl -fsSL "https://pkgs.k8s.io/core:/stable:/${K8S_SERIES}/deb/Release.key" \
      | gpg --dearmor -o /etc/apt/keyrings/kubernetes-archive-keyring.gpg
    chmod a+r /etc/apt/keyrings/kubernetes-archive-keyring.gpg
  fi

  echo "deb [signed-by=/etc/apt/keyrings/kubernetes-archive-keyring.gpg] https://pkgs.k8s.io/core:/stable:/${K8S_SERIES}/deb/ /" \
    >/etc/apt/sources.list.d/kubernetes.list

  apt-get update
  apt-get install -y kubelet kubeadm kubectl
  apt-mark hold kubelet kubeadm kubectl

  systemctl enable kubelet
}

maybe_kubeadm_init() {
  if $INSTALL_ONLY; then
    echo "Install-only mode: skipping kubeadm init."
    return
  fi

  echo "Initializing single-node control-plane with kubeadm (containerd runtime)..."
  # Use the containerd CRI socket explicitly
  kubeadm init \
    --pod-network-cidr="${POD_CIDR}" \
    --cri-socket=unix:///run/containerd/containerd.sock

  # Setup kubeconfig for the current (likely) default user
  local USER_HOME
  local USER_NAME
  USER_NAME=${SUDO_USER:-${USER:-root}}
  USER_HOME=$(getent passwd "$USER_NAME" | cut -d: -f6)
  mkdir -p "${USER_HOME}/.kube"
  cp -i /etc/kubernetes/admin.conf "${USER_HOME}/.kube/config"
  chown -R "${USER_NAME}:${USER_NAME}" "${USER_HOME}/.kube"

  # Install a simple CNI: Flannel (compatible with 10.244.0.0/16)
  echo "Installing Flannel CNI..."
  # Note: If you change POD_CIDR, make sure the manifest matches.
  kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml

  # Allow scheduling pods on the control-plane (single-node dev)
  kubectl taint nodes --all node-role.kubernetes.io/control-plane- || true

  echo "Kubernetes control-plane initialized."
  echo
  echo "To add workers, run the 'kubeadm join ...' command shown above on each worker node."
}

main() {
  require_root
  detect_os
  disable_swap
  kernel_prep
  install_base_tools
  install_docker_engine
  install_containerd_and_configure
  install_kubernetes_binaries
  maybe_kubeadm_init

  echo
  echo "✅ Done."
  echo "Docker:    $(docker --version || true)"
  echo "containerd: $(containerd --version || true)"
  echo "kubectl:    $(kubectl version --client -o yaml 2>/dev/null | head -n 5 || true)"
  echo
  if $INSTALL_ONLY; then
    echo "Install-only mode complete. To initialize later:"
    echo "  sudo kubeadm init --pod-network-cidr=${POD_CIDR} --cri-socket=unix:///run/containerd/containerd.sock"
    echo "Then install a CNI (e.g. Flannel) and untaint the node if you want workloads on control-plane."
  else
    echo "Your kubeconfig is set for user '${SUDO_USER:-$USER}'. Try:"
    echo "  kubectl get nodes"
  fi
}

main "$@"

123gkc@instance-20251018-034451:~/iaac$ cat setup-qdrant-docker.sh
#!/usr/bin/env bash
set -euo pipefail

# ---- Config (override via env vars) ----
QDRANT_IMAGE="${QDRANT_IMAGE:-qdrant/qdrant:latest}"
QDRANT_CONTAINER_NAME="${QDRANT_CONTAINER_NAME:-qdrant}"
QDRANT_DATA_DIR="${QDRANT_DATA_DIR:-$PWD/qdrant_storage}"
QDRANT_PORT_HTTP="${QDRANT_PORT_HTTP:-6333}"   # REST
QDRANT_PORT_GRPC="${QDRANT_PORT_GRPC:-6334}"   # gRPC
QDRANT_DOCKER_RUN_EXTRA="${QDRANT_DOCKER_RUN_EXTRA:-}"  # e.g. "--cpus=2 --memory=4g"

# If you're on SELinux (RHEL/Fedora), leave :z. On Ubuntu/Debian it's ignored.
VOLUME_SUFFIX=":z"

log() { echo -e "[qdrant-setup] $*"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

ensure_data_dir() {
  mkdir -p "$QDRANT_DATA_DIR"
  chmod 775 "$QDRANT_DATA_DIR" || true
}

pull_image() {
  log "Pulling image $QDRANT_IMAGE ..."
  docker pull "$QDRANT_IMAGE"
}

container_exists() {
  docker ps -a --format '{{.Names}}' | grep -Fxq "$QDRANT_CONTAINER_NAME"
}

container_running() {
  docker ps --format '{{.Names}}' | grep -Fxq "$QDRANT_CONTAINER_NAME"
}

start_existing() {
  log "Starting existing container '$QDRANT_CONTAINER_NAME' ..."
  docker start "$QDRANT_CONTAINER_NAME" >/dev/null
}

create_and_run() {
  log "Creating and starting container '$QDRANT_CONTAINER_NAME' ..."
  docker run -d \
    --name "$QDRANT_CONTAINER_NAME" \
    --restart unless-stopped \
    -p "${QDRANT_PORT_HTTP}:6333" \
    -p "${QDRANT_PORT_GRPC}:6334" \
    -v "${QDRANT_DATA_DIR}:/qdrant/storage${VOLUME_SUFFIX}" \
    $QDRANT_DOCKER_RUN_EXTRA \
    "$QDRANT_IMAGE" >/dev/null
}

wait_ready() {
  log "Waiting for Qdrant to become ready on http://localhost:${QDRANT_PORT_HTTP} ..."
  for i in {1..60}; do
    if curl -fsS "http://localhost:${QDRANT_PORT_HTTP}/collections" >/dev/null 2>&1; then
      log "Qdrant is ready."
      return 0
    fi
    sleep 1
  done
  log "Warning: Timed out waiting for readiness (it may still be starting)."
}

main() {
  require_cmd docker
  ensure_data_dir
  pull_image

  if container_exists; then
    if container_running; then
      log "Container '$QDRANT_CONTAINER_NAME' is already running. Reusing it."
    else
      start_existing
    fi
  else
    create_and_run
  fi

  wait_ready

  log "Done."
  log "REST  : http://localhost:${QDRANT_PORT_HTTP}"
  log "gRPC  : localhost:${QDRANT_PORT_GRPC}"
  log "Data  : ${QDRANT_DATA_DIR}"
  log "Name  : ${QDRANT_CONTAINER_NAME}"
  log "Try   : curl -s http://localhost:${QDRANT_PORT_HTTP}/collections | jq ."
}

main "$@"