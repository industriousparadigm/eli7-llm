#!/bin/bash
# One-command fix for the Pi - just copy and paste this entire script!

echo "🔧 Fixing Soft Terminal to auto-launch GUI"
echo "==========================================="

cd ~/soft-terminal-llm

# Fix 1: Update browser launcher to check BOTH ports
echo "Fixing browser launcher..."
cat > launch-browser.sh << 'EOF'
#!/bin/bash
echo "🚀 Launching Soft Terminal..."

# Set display for GUI
export DISPLAY=:0

# Kill old browser
pkill -f chromium 2>/dev/null || true

# Check which port is active
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo "✓ Found app on port 3000 (Docker)"
    URL="http://localhost:3000"
elif curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "✓ Found app on port 5173 (Direct)"  
    URL="http://localhost:5173"
else
    echo "❌ App not running! Starting it..."
    sudo systemctl start soft-terminal || docker-compose up -d
    sleep 5
    URL="http://localhost:3000"
fi

# Launch browser in kiosk mode
chromium-browser --kiosk --noerrdialogs --disable-infobars $URL &
echo "✅ Browser launched!"
EOF
chmod +x launch-browser.sh

# Fix 2: Enable auto-login to desktop (not console!)
echo ""
echo "Setting up auto-login to desktop..."
sudo raspi-config nonint do_boot_behaviour B4

# Fix 3: Create autostart for browser
echo "Creating autostart entry..."
mkdir -p ~/.config/autostart
cat > ~/.config/autostart/soft-terminal.desktop << 'EOF'
[Desktop Entry]
Type=Application
Name=Soft Terminal
Exec=/bin/bash /home/diogo/soft-terminal-llm/launch-browser.sh
Hidden=false
X-GNOME-Autostart-enabled=true
X-GNOME-Autostart-delay=20
EOF

# Fix 4: Ensure services are enabled
echo "Enabling services..."
sudo systemctl enable soft-terminal 2>/dev/null || true
sudo systemctl start soft-terminal 2>/dev/null || docker-compose up -d

echo ""
echo "✅ ALL FIXED!"
echo "============="
echo ""
echo "Test now with: ./launch-browser.sh"
echo "Or reboot to test auto-start: sudo reboot"
echo ""
echo "After reboot, the app will:"
echo "1. Auto-login to desktop"
echo "2. Wait 20 seconds"
echo "3. Launch browser full-screen"
echo "No manual steps needed for the 7-year-old!"