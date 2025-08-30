#!/bin/bash
# Improved deployment script with better error handling and optimization

set -e

# Configuration
PI_HOST="${PI_HOST:-192.168.1.100}"
PI_USER="${PI_USER:-diogo}"
PI_DIR="/home/${PI_USER}/soft-terminal-llm"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() { echo -e "${BLUE}ℹ ${NC} $1"; }
log_success() { echo -e "${GREEN}✓${NC} $1"; }
log_warning() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✗${NC} $1"; }

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check for .env.production
    if [[ ! -f ".env.production" ]]; then
        log_error ".env.production not found!"
        echo "Please create it with your ANTHROPIC_API_KEY:"
        echo "  echo 'ANTHROPIC_API_KEY=your_key_here' > .env.production"
        exit 1
    fi
    
    # Check Pi connectivity
    if ! ping -c 1 -W 2 $PI_HOST > /dev/null 2>&1; then
        log_error "Cannot reach Pi at $PI_HOST"
        exit 1
    fi
    
    log_success "Prerequisites checked"
}

# Build Docker images for ARM64
build_images() {
    log_info "Building Docker images for ARM64..."
    
    # Check if buildx is available
    if ! docker buildx version > /dev/null 2>&1; then
        log_warning "Docker buildx not found, skipping cross-platform build"
        return
    fi
    
    # Build API image
    docker buildx build \
        --platform linux/arm64 \
        --tag soft-terminal-api:arm64 \
        --load \
        ./api
    
    # Build UI image  
    docker buildx build \
        --platform linux/arm64 \
        --tag soft-terminal-ui:arm64 \
        --load \
        ./ui
    
    log_success "Images built for ARM64"
}

# Sync files to Pi
sync_files() {
    log_info "Syncing files to Pi..."
    
    # Create directory on Pi if it doesn't exist
    ssh $PI_USER@$PI_HOST "mkdir -p $PI_DIR"
    
    # Sync with better exclusions
    rsync -avz --progress \
        --exclude 'node_modules' \
        --exclude '.git' \
        --exclude '.DS_Store' \
        --exclude '*.log' \
        --exclude '.env.local' \
        --exclude 'dist' \
        --exclude '.vite' \
        --exclude '__pycache__' \
        --exclude '*.pyc' \
        --exclude 'logs/*.jsonl' \
        --exclude '.pytest_cache' \
        --exclude 'venv' \
        --exclude '.idea' \
        --exclude '.vscode' \
        ./ $PI_USER@$PI_HOST:$PI_DIR/
    
    # Copy production env
    scp .env.production $PI_USER@$PI_HOST:$PI_DIR/.env
    
    log_success "Files synced"
}

# Setup Pi environment
setup_pi() {
    log_info "Setting up Pi environment..."
    
    ssh $PI_USER@$PI_HOST << 'ENDSSH'
    cd ~/soft-terminal-llm
    
    # Ensure Docker is installed
    if ! command -v docker &> /dev/null; then
        echo "Installing Docker..."
        curl -sSL https://get.docker.com | sh
        sudo usermod -aG docker $USER
    fi
    
    # Install Node.js if needed
    if ! command -v node &> /dev/null; then
        echo "Installing Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    
    # Install UI dependencies
    cd ui && npm ci --production && cd ..
    
    # Make scripts executable
    chmod +x launch-browser.sh
    chmod +x setup-pi-autostart.sh
    
    # Setup systemd service
    if [[ -f systemd/soft-terminal.service ]]; then
        sudo cp systemd/soft-terminal.service /etc/systemd/system/
        sudo systemctl daemon-reload
        sudo systemctl enable soft-terminal.service
    fi
ENDSSH
    
    log_success "Pi environment ready"
}

# Deploy application
deploy_app() {
    log_info "Deploying application..."
    
    ssh $PI_USER@$PI_HOST << 'ENDSSH'
    cd ~/soft-terminal-llm
    
    # Stop existing services
    docker-compose down 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    
    # Use production docker-compose if available
    if [[ -f docker-compose.prod.yml ]]; then
        docker-compose -f docker-compose.prod.yml up -d
    else
        docker-compose up -d
    fi
    
    # Wait for services
    echo -n "Waiting for services to start"
    for i in {1..30}; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            echo " ✓"
            break
        fi
        echo -n "."
        sleep 1
    done
ENDSSH
    
    log_success "Application deployed"
}

# Main execution
main() {
    echo "🚀 Enhanced Deployment to Raspberry Pi"
    echo "======================================"
    echo ""
    
    check_prerequisites
    
    # Optional: Build ARM images
    read -p "Build Docker images for ARM64? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        build_images
    fi
    
    sync_files
    setup_pi
    deploy_app
    
    echo ""
    log_success "Deployment complete! 🎉"
    echo ""
    echo "📱 Access points:"
    echo "   Web UI:     http://$PI_HOST:5173"
    echo "   API:        http://$PI_HOST:8000"
    echo "   Logs:       http://$PI_HOST:8000/logs"
    echo ""
    echo "📺 For kiosk mode on Pi:"
    echo "   ssh $PI_USER@$PI_HOST"
    echo "   ~/soft-terminal-llm/launch-browser.sh"
    echo ""
}

# Run main function
main "$@"