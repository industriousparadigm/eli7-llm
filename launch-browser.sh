#!/bin/bash
# Launch Soft Terminal in kiosk mode on Raspberry Pi
# FIXED: Checks BOTH ports (3000 for Docker, 5173 for direct)

echo "🚀 Launching Soft Terminal Browser"
echo "==================================="

# Check if running via SSH and set display
if [ -n "$SSH_CONNECTION" ]; then
    echo "Running via SSH - setting DISPLAY=:0"
    export DISPLAY=:0
fi

# Check if display is available
if ! xset q &>/dev/null; then
    echo "❌ No display available!"
    echo "   This must be run on the Pi's desktop."
    echo "   If using SSH, try: DISPLAY=:0 $0"
    exit 1
fi

# Kill any existing chromium instances
pkill -f chromium 2>/dev/null || true

# Wait for the application to be ready
# Check BOTH ports since we might be in Docker (3000) or direct (5173)
echo -n "Waiting for application"
URL=""
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        URL="http://localhost:3000"
        echo " ✓ (Docker on port 3000)"
        break
    elif curl -s http://localhost:5173 > /dev/null 2>&1; then
        URL="http://localhost:5173"
        echo " ✓ (Direct on port 5173)"
        break
    fi
    echo -n "."
    sleep 1
done

if [ -z "$URL" ]; then
    echo ""
    echo "❌ Application not responding!"
    echo "   Try: docker ps (check containers)"
    echo "   Or:  ./manage.sh start"
    exit 1
fi

# Disable screen blanking
xset s off 2>/dev/null || true
xset -dpms 2>/dev/null || true
xset s noblank 2>/dev/null || true

# Launch Chromium in kiosk mode
echo "Opening browser at $URL"
chromium-browser \
    --kiosk \
    --noerrdialogs \
    --disable-infobars \
    --disable-session-crashed-bubble \
    --check-for-update-interval=604800 \
    --disable-features=TranslateUI \
    --disable-component-update \
    --autoplay-policy=no-user-gesture-required \
    --start-fullscreen \
    $URL &

BROWSER_PID=$!
echo "✅ Browser launched!"
echo "Press Ctrl+C to exit"

# Trap Ctrl+C
trap "kill $BROWSER_PID 2>/dev/null; exit" INT

# Keep running
wait $BROWSER_PID