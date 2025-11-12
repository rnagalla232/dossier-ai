#!/usr/bin/env bash
set -euo pipefail

# ---- Config (override via env vars) ----
MONGO_IMAGE="${MONGO_IMAGE:-mongo:7}"                      # MongoDB image tag
MONGO_CONTAINER_NAME="${MONGO_CONTAINER_NAME:-mongo}"     # Container name
MONGO_DATA_DIR="${MONGO_DATA_DIR:-$PWD/mongo_data}"       # Persistent data dir
MONGO_PORT="${MONGO_PORT:-27017}"                         # Host port
MONGO_RS_NAME="${MONGO_RS_NAME:-}"                        # e.g. "rs0" to enable single-node replica set
MONGO_DOCKER_RUN_EXTRA="${MONGO_DOCKER_RUN_EXTRA:-}"      # e.g. "--cpus=2 --memory=4g"

# Root credentials (optional; recommended on first run / empty data dir)
MONGO_ROOT_USER="${MONGO_ROOT_USER:-}"                    # e.g. "root"
MONGO_ROOT_PASS="${MONGO_ROOT_PASS:-}"                    # e.g. "supersecret"

# Optional: create an app DB + user after start (works whether data is new or existing)
APP_DB="${APP_DB:-}"                                      # e.g. "mydb"
APP_USER="${APP_USER:-}"                                  # e.g. "appuser"
APP_PASS="${APP_PASS:-}"                                  # e.g. "apppass"
APP_ROLE="${APP_ROLE:-readWrite}"                         # default role for APP_USER

# If you're on SELinux (RHEL/Fedora), leave :z. On Ubuntu/Debian it's ignored.
VOLUME_SUFFIX=":z"

log() { echo -e "[mongo-setup] $*"; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

ensure_data_dir() {
  mkdir -p "$MONGO_DATA_DIR"
  chmod 700 "$MONGO_DATA_DIR" || true
}

pull_image() {
  log "Pulling image $MONGO_IMAGE ..."
  docker pull "$MONGO_IMAGE"
}

container_exists() {
  docker ps -a --format '{{.Names}}' | grep -Fxq "$MONGO_CONTAINER_NAME"
}

container_running() {
  docker ps --format '{{.Names}}' | grep -Fxq "$MONGO_CONTAINER_NAME"
}

start_existing() {
  log "Starting existing container '$MONGO_CONTAINER_NAME' ..."
  docker start "$MONGO_CONTAINER_NAME" >/dev/null
}

create_and_run() {
  log "Creating and starting container '$MONGO_CONTAINER_NAME' ..."

  # Base args
  local run_args=(
    -d
    --name "$MONGO_CONTAINER_NAME"
    --restart unless-stopped
    -p "${MONGO_PORT}:27017"
    -v "${MONGO_DATA_DIR}:/data/db${VOLUME_SUFFIX}"
  )

  # Root creds only make effect on first init (empty /data/db)
  if [[ -n "${MONGO_ROOT_USER}" && -n "${MONGO_ROOT_PASS}" ]]; then
    run_args+=( -e "MONGO_INITDB_ROOT_USERNAME=${MONGO_ROOT_USER}" -e "MONGO_INITDB_ROOT_PASSWORD=${MONGO_ROOT_PASS}" )
  fi

  # Enable replica set if requested
  if [[ -n "${MONGO_RS_NAME}" ]]; then
    run_args+=( "$MONGO_IMAGE" --replSet "${MONGO_RS_NAME}" )
  else
    run_args+=( "$MONGO_IMAGE" )
  fi

  # shellcheck disable=SC2086
  docker run "${run_args[@]}" $MONGO_DOCKER_RUN_EXTRA >/dev/null
}

mongosh_exec() {
  # Helper to run mongosh inside the container with proper auth if provided
  local db="${1:-admin}"
  local js="${2:-db.runCommand({ ping: 1 })}"
  if [[ -n "${MONGO_ROOT_USER}" && -n "${MONGO_ROOT_PASS}" ]]; then
    docker exec -i "$MONGO_CONTAINER_NAME" mongosh --quiet "mongodb://localhost:27017/${db}" \
      -u "${MONGO_ROOT_USER}" -p "${MONGO_ROOT_PASS}" --eval "${js}"
  else
    docker exec -i "$MONGO_CONTAINER_NAME" mongosh --quiet "mongodb://localhost:27017/${db}" --eval "${js}"
  fi
}

wait_ready() {
  log "Waiting for MongoDB to become ready on localhost:${MONGO_PORT} ..."
  for i in {1..90}; do
    if docker exec "$MONGO_CONTAINER_NAME" bash -c "pgrep mongod >/dev/null"; then
      if mongosh_exec "admin" "db.runCommand({ ping: 1 })" >/dev/null 2>&1; then
        log "MongoDB is ready."
        return 0
      fi
    fi
    sleep 1
  done
  log "Warning: Timed out waiting for readiness (it may still be starting)."
}

init_replica_set() {
  [[ -z "${MONGO_RS_NAME}" ]] && return 0
  log "Initializing (or verifying) single-node replica set '${MONGO_RS_NAME}' ..."
  local status
  status="$(mongosh_exec 'admin' 'rs.status().ok' 2>/dev/null || true)"
  if [[ "$status" == "1" ]]; then
    log "Replica set already initialized."
    return 0
  fi

  mongosh_exec "admin" "
    try {
      rs.initiate({
        _id: '${MONGO_RS_NAME}',
        members: [{ _id: 0, host: 'localhost:27017' }]
      });
      let ok = 0; 
      for (let i=0; i<60; i++) {
        const s = rs.status();
        if (s.ok === 1 && s.members && s.members[0] && s.members[0].stateStr === 'PRIMARY') { ok = 1; break; }
        sleep(1000);
      }
      ok;
    } catch (e) { print(e); 0; }
  " >/dev/null || true
  log "Replica set init attempted (ignore if already configured)."
}

create_app_user_if_needed() {
  if [[ -z "$APP_DB" || -z "$APP_USER" || -z "$APP_PASS" ]]; then
    return 0
  fi
  log "Ensuring application user '${APP_USER}' exists on DB '${APP_DB}' ..."
  mongosh_exec "$APP_DB" "
    const dbName='${APP_DB}';
    const user='${APP_USER}';
    const pass='${APP_PASS}';
    const role='${APP_ROLE}';
    db.getSiblingDB(dbName);
    const existing = db.getUser(user);
    if (!existing) {
      db.createUser({ user, pwd: pass, roles: [ { role: role, db: dbName } ] });
      print('Created user');
    } else {
      print('User already exists');
    }
  " >/dev/null || true
}

main() {
  require_cmd docker
  ensure_data_dir
  pull_image

  if container_exists; then
    if container_running; then
      log "Container '$MONGO_CONTAINER_NAME' is already running. Reusing it."
    else
      start_existing
    fi
  else
    create_and_run
  fi

  wait_ready
  init_replica_set
  create_app_user_if_needed

  log "Done."
  log "Mongo URI hints:"
  if [[ -n "${MONGO_ROOT_USER}" && -n "${MONGO_ROOT_PASS}" ]]; then
    log "  Admin: mongodb://${MONGO_ROOT_USER}:${MONGO_ROOT_PASS}@localhost:${MONGO_PORT}/admin"
  else
    log "  No root credentials set (good only for local dev on fresh data)."
  fi
  if [[ -n "${APP_DB}" && -n "${APP_USER}" && -n "${APP_PASS}" ]]; then
    log "  App  : mongodb://${APP_USER}:${APP_PASS}@localhost:${MONGO_PORT}/${APP_DB}"
  fi
  if [[ -n "${MONGO_RS_NAME}" ]]; then
    log "  RS   : ${MONGO_RS_NAME} (single-node) — add '?replicaSet=${MONGO_RS_NAME}' to connection string if needed."
  fi
  log "Data  : ${MONGO_DATA_DIR}"
  log "Name  : ${MONGO_CONTAINER_NAME}"
  log "Try   : docker exec -it ${MONGO_CONTAINER_NAME} mongosh"
}

main "$@"