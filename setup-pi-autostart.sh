#!/bin/bash
# Setup automatic startup on Raspberry Pi boot WITH VISIBLE GUI
# IMPORTANT: This will make the app VISIBLE on screen for the 7-year-old user!

set -e

echo "🚀 Setting up Soft Terminal LLM with VISIBLE GUI on Boot"
echo "========================================================"
echo "The app will be VISIBLE on screen - perfect for kids!"
echo ""

# Check if running on Pi (optional check, can be skipped)
if [[ -f /proc/device-tree/model ]]; then
    grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null || true
fi

# Install dependencies if needed
echo "📦 Checking system dependencies..."
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -sSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo "✅ Docker installed"
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose
    echo "✅ Docker Compose installed"
fi

# Setup systemd service
echo ""
echo "⚙️  Installing systemd service..."
sudo cp systemd/soft-terminal.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable soft-terminal.service
echo "✅ Service installed and enabled"

# ALWAYS setup auto-login and kiosk mode for the 7-year-old user!
echo ""
echo "📺 Setting up auto-login and kiosk mode..."

# Enable auto-login to desktop (not console)
sudo raspi-config nonint do_boot_behaviour B4
echo "✅ Auto-login to desktop enabled"

# Create autostart directories
mkdir -p ~/.config/autostart
mkdir -p ~/.config/lxsession/LXDE-pi

# Create autostart entry for kiosk mode
cat > ~/.config/autostart/soft-terminal.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Soft Terminal Browser
Comment=Educational AI for Kids
Exec=/home/diogo/soft-terminal-llm/launch-browser.sh
Terminal=false
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-delay=15
EOF

# Also create LXDE autostart (alternative method)
cat > ~/.config/lxsession/LXDE-pi/autostart << 'EOF'
@lxpanel --profile LXDE-pi
@pcmanfm --desktop --profile LXDE-pi
@xscreensaver -no-splash
@bash /home/diogo/soft-terminal-llm/launch-browser.sh
EOF

echo "✅ Auto-launch browser on boot configured"

# Create log rotation config
echo ""
echo "📝 Setting up log rotation..."
sudo tee /etc/logrotate.d/soft-terminal << EOF
/home/diogo/soft-terminal-llm/logs/*.jsonl {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 644 diogo diogo
}
EOF
echo "✅ Log rotation configured"

# Start the service
echo ""
echo "🎬 Starting Soft Terminal service..."
sudo systemctl start soft-terminal.service

# Check status
if sudo systemctl is-active --quiet soft-terminal.service; then
    echo "✅ Service is running!"
    echo ""
    echo "📊 Service status:"
    sudo systemctl status soft-terminal.service --no-pager
else
    echo "❌ Service failed to start. Check logs with:"
    echo "   sudo journalctl -u soft-terminal.service -n 50"
fi

echo ""
echo "✨ Setup complete!"
echo ""
echo "📝 Useful commands:"
echo "   sudo systemctl status soft-terminal    # Check service status"
echo "   sudo systemctl restart soft-terminal   # Restart service"
echo "   sudo journalctl -u soft-terminal -f    # View service logs"
echo "   ~/soft-terminal-llm/launch-browser.sh  # Launch browser manually"
echo ""
echo "The application will now start automatically on boot!"
echo ""
echo "🖥️  IMPORTANT: The browser will AUTO-LAUNCH on the screen!"
echo "   - No manual steps needed for the 7-year-old"
echo "   - Just turn on the Pi and wait ~30 seconds"
echo "   - The app will appear full-screen automatically"
echo ""
echo "🔄 Reboot now to test? (y/n)"
read -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Rebooting..."
    sudo reboot
fi