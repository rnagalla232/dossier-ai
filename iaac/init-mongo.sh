#!/usr/bin/env bash
set -euo pipefail

# -------- Config (override via env vars) --------
MONGO_HOST="${MONGO_HOST:-localhost}"
MONGO_PORT="${MONGO_PORT:-27017}"
MONGO_DB="${MONGO_DB:-dossier}"
MONGO_USER="${MONGO_USER:-}"
MONGO_PASSWORD="${MONGO_PASSWORD:-}"
MONGO_AUTH_DB="${MONGO_AUTH_DB:-admin}"

# Collections to create
COLLECTIONS=("users" "documents" "categories")

# ------------------------------------------------
say() { echo "[mongo-init] $*"; }

# Detect OS type
detect_os() {
  if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    echo "$ID"
  elif [[ "$(uname)" == "Darwin" ]]; then
    echo "macos"
  else
    echo "unknown"
  fi
}

# Install mongosh based on OS
install_mongosh() {
  local os_type=$(detect_os)
  say "Detected OS: ${os_type}"
  say "Installing mongosh..."
  
  case "$os_type" in
    ubuntu|debian)
      say "Installing mongosh for Debian/Ubuntu..."
      # Import MongoDB public GPG key
      if ! command -v wget &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y wget
      fi
      
      wget -qO- https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg --dearmor -o /usr/share/keyrings/mongodb-archive-keyring.gpg 2>/dev/null || true
      
      # Add MongoDB repository
      if [[ "$os_type" == "ubuntu" ]]; then
        echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-archive-keyring.gpg ] https://repo.mongodb.org/apt/ubuntu $(lsb_release -cs)/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
      else
        # Debian
        echo "deb [ signed-by=/usr/share/keyrings/mongodb-archive-keyring.gpg ] https://repo.mongodb.org/apt/debian $(lsb_release -cs)/mongodb-org/7.0 main" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
      fi
      
      sudo apt-get update
      sudo apt-get install -y mongodb-mongosh
      ;;
      
    rhel|centos|fedora|rocky|almalinux)
      say "Installing mongosh for RHEL/CentOS/Fedora..."
      # Create MongoDB repository file
      sudo tee /etc/yum.repos.d/mongodb-org-7.0.repo > /dev/null <<EOF
[mongodb-org-7.0]
name=MongoDB Repository
baseurl=https://repo.mongodb.org/yum/redhat/\$releasever/mongodb-org/7.0/x86_64/
gpgcheck=1
enabled=1
gpgkey=https://www.mongodb.org/static/pgp/server-7.0.asc
EOF
      
      sudo yum install -y mongodb-mongosh
      ;;
      
    macos)
      say "Installing mongosh for macOS..."
      if ! command -v brew &> /dev/null; then
        say "ERROR: Homebrew not found. Please install Homebrew first: https://brew.sh"
        exit 1
      fi
      brew install mongosh
      ;;
      
    *)
      say "ERROR: Unsupported OS: ${os_type}"
      say "Please install mongosh manually: https://www.mongodb.com/docs/mongodb-shell/install/"
      exit 1
      ;;
  esac
  
  say "mongosh installation completed."
}

# Ensure mongosh is available
ensure_mongosh() {
  if command -v mongosh &> /dev/null; then
    say "mongosh is already installed."
    return 0
  fi
  
  say "mongosh not found. Attempting to install..."
  install_mongosh
  
  # Verify installation
  if command -v mongosh &> /dev/null; then
    say "mongosh successfully installed."
  else
    say "ERROR: Failed to install mongosh."
    exit 1
  fi
}

# Build MongoDB connection string
build_connection_string() {
  local conn_str="mongodb://"
  
  if [[ -n "$MONGO_USER" ]] && [[ -n "$MONGO_PASSWORD" ]]; then
    conn_str="${conn_str}${MONGO_USER}:${MONGO_PASSWORD}@"
  fi
  
  conn_str="${conn_str}${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB}"
  
  if [[ -n "$MONGO_USER" ]]; then
    conn_str="${conn_str}?authSource=${MONGO_AUTH_DB}"
  fi
  
  echo "$conn_str"
}

# Check if mongosh is available, fallback to mongo
get_mongo_cli() {
  if command -v mongosh &> /dev/null; then
    echo "mongosh"
  elif command -v mongo &> /dev/null; then
    say "Using legacy 'mongo' CLI (consider upgrading to mongosh)"
    echo "mongo"
  else
    say "ERROR: Neither 'mongosh' nor 'mongo' CLI found."
    exit 1
  fi
}

ensure_collection() {
  local collection_name=$1
  local conn_str=$(build_connection_string)
  local mongo_cli=$(get_mongo_cli)
  
  say "Checking collection '${collection_name}' in database '${MONGO_DB}' ..."
  
  # Check if collection exists
  local check_result=$(${mongo_cli} "${conn_str}" --quiet --eval "
    db.getCollectionNames().includes('${collection_name}')
  ")
  
  if [[ "$check_result" == "true" ]]; then
    say "Collection '${collection_name}' already exists."
    return 0
  fi
  
  say "Creating collection '${collection_name}' ..."
  ${mongo_cli} "${conn_str}" --quiet --eval "
    db.createCollection('${collection_name}')
  " >/dev/null
  
  say "Collection '${collection_name}' created successfully."
}

create_indexes() {
  local conn_str=$(build_connection_string)
  local mongo_cli=$(get_mongo_cli)
  
  say "Creating indexes for 'documents' collection ..."
  
  ${mongo_cli} "${conn_str}" --quiet --eval "
    // Create index on user_id for faster user-based queries
    db.documents.createIndex({ user_id: 1 });
    
    // Create compound unique index on (user_id, url) to prevent duplicate URLs per user
    db.documents.createIndex({ user_id: 1, url: 1 }, { unique: true });
    
    print('Indexes created successfully');
  " >/dev/null
  
  say "Indexes created successfully."
}

ensure_database() {
  local conn_str=$(build_connection_string)
  local mongo_cli=$(get_mongo_cli)
  
  say "Ensuring database '${MONGO_DB}' exists ..."
  
  # Check if database exists (will be created automatically when first collection is created)
  local db_exists=$(${mongo_cli} "mongodb://${MONGO_HOST}:${MONGO_PORT}/admin" --quiet --eval "
    db.adminCommand('listDatabases').databases.map(d => d.name).includes('${MONGO_DB}')
  " 2>/dev/null || echo "false")
  
  if [[ "$db_exists" == "true" ]]; then
    say "Database '${MONGO_DB}' already exists."
  else
    say "Database '${MONGO_DB}' will be created with first collection."
  fi
}

main() {
  # Ensure mongosh is installed
  ensure_mongosh
  
  local mongo_cli=$(get_mongo_cli)
  say "Using MongoDB CLI: ${mongo_cli}"
  say "MongoDB Host: ${MONGO_HOST}:${MONGO_PORT}"
  say "Database: ${MONGO_DB}"
  
  ensure_database
  
  # Create each collection
  for collection in "${COLLECTIONS[@]}"; do
    ensure_collection "$collection"
  done
  
  # Create indexes
  create_indexes
  
  say "Done. Database '${MONGO_DB}' is ready with collections: ${COLLECTIONS[*]}"
  say "Try: ${mongo_cli} mongodb://${MONGO_HOST}:${MONGO_PORT}/${MONGO_DB} --eval 'db.getCollectionNames()'"
}

main "$@"

