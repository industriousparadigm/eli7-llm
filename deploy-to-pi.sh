#!/bin/bash
# Deploy Soft Terminal LLM to Raspberry Pi

set -e

# Configuration
PI_HOST="192.168.1.100"
PI_USER="diogo"
PI_DIR="/home/diogo/soft-terminal-llm"

echo "🚀 Deploying Soft Terminal LLM to Raspberry Pi"
echo "=============================================="
echo ""

# Check if Pi is reachable
echo "📡 Checking connection to Pi..."
if ! ping -c 1 $PI_HOST > /dev/null 2>&1; then
    echo "❌ Cannot reach Pi at $PI_HOST"
    echo "   Please check that your Pi is on and connected to the network"
    exit 1
fi
echo "✅ Pi is reachable"

# Sync files (excluding node_modules and other unnecessary files)
echo ""
echo "📦 Syncing files to Pi..."
rsync -avz --progress \
    --exclude 'node_modules' \
    --exclude '.git' \
    --exclude '.DS_Store' \
    --exclude '*.log' \
    --exclude '.env.local' \
    --exclude '.env.production' \
    --exclude 'dist' \
    --exclude '.vite' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'logs/*' \
    ./ $PI_USER@$PI_HOST:$PI_DIR/

# Copy production environment file (with secrets) as .env on Pi
if [ -f ".env.production" ]; then
    echo ""
    echo "🔐 Copying production environment..."
    scp .env.production $PI_USER@$PI_HOST:$PI_DIR/.env
else
    echo ""
    echo "⚠️  Warning: .env.production not found!"
    echo "   Create it from .env.example with your real API key"
fi

echo ""
echo "✅ Files synced successfully"

# Install npm packages on Pi (in case package.json changed)
echo ""
echo "📦 Installing npm packages on Pi..."
ssh $PI_USER@$PI_HOST "cd $PI_DIR/ui && npm install"

# Restart services on Pi
echo ""
echo "🔄 Restarting services on Pi..."
ssh $PI_USER@$PI_HOST << 'ENDSSH'
cd ~/soft-terminal-llm

# Stop existing services
echo "Stopping existing services..."
docker-compose down 2>/dev/null || true
pkill -f "npm run dev" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# Start API with Docker
echo "Starting API..."
docker-compose up -d api

# Wait for API to be ready
echo "Waiting for API to start..."
while ! curl -s http://localhost:8000/health > /dev/null 2>&1; do
    sleep 1
done

# Start UI
echo "Starting UI..."
cd ui
nohup npm run dev -- --host 0.0.0.0 > ~/ui.log 2>&1 &

echo "Services restarted!"
ENDSSH

echo ""
echo "✅ Deployment complete!"
echo ""
echo "📱 Access your app at:"
echo "   http://$PI_HOST:5173"
echo ""
echo "📺 To display on Pi screen, run on the Pi:"
echo "   ~/soft-terminal-llm/launch-browser.sh"
echo ""
echo "📝 View logs with:"
echo "   ssh $PI_USER@$PI_HOST 'tail -f ~/ui.log'"
echo "   ssh $PI_USER@$PI_HOST 'docker-compose -f ~/soft-terminal-llm/docker-compose.yml logs -f api'"
