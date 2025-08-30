#!/bin/bash
# Quick deployment script with configurable IP

# Get IP from command line or use default
PI_IP="${1:-192.168.1.100}"
PI_USER="diogo"

echo "🚀 Quick Deploy to Pi at $PI_IP"
echo "================================"

# Test connection
if ! ping -c 1 -W 1 $PI_IP > /dev/null 2>&1; then
    echo "❌ Cannot reach Pi at $PI_IP"
    echo "Usage: $0 [PI_IP_ADDRESS]"
    echo "Example: $0 192.168.1.108"
    exit 1
fi

echo "✅ Pi is reachable at $PI_IP"
echo ""
echo "📦 Syncing files..."

# Sync only the critical files that need updating
rsync -avz --progress \
    launch-browser.sh \
    setup-pi-autostart.sh \
    manage.sh \
    check-health.sh \
    CLAUDE.md \
    systemd/ \
    $PI_USER@$PI_IP:/home/$PI_USER/soft-terminal-llm/

# Make scripts executable on Pi
ssh $PI_USER@$PI_IP "cd ~/soft-terminal-llm && chmod +x *.sh"

echo ""
echo "✅ Files deployed!"
echo ""
echo "Now on your Pi, run:"
echo "  cd ~/soft-terminal-llm"
echo "  ./setup-pi-autostart.sh"
echo ""
echo "Or to test immediately:"
echo "  ./launch-browser.sh"