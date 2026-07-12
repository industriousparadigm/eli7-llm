#!/bin/bash
# Launch Soft Terminal in kiosk mode on Raspberry Pi
# FIXED: Works from console or desktop, checks both ports

echo "🚀 Launching Soft Terminal Browser"
echo "==================================="

# Always set display
export DISPLAY=:0

# If no X server, start desktop environment
if ! xset q &>/dev/null 2>&1; then
    if [ -z "$SSH_CONNECTION" ]; then
        echo "Starting desktop environment..."
        startx &
        sleep 10
    else
        echo "Note: Running via SSH, display might not be available"
    fi
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

# Screen sleeps after 20 min idle to spare the panel + power; wakes instantly on
# touch or keypress. The Pi itself never sleeps or shuts down - only the display
# powers off - so the app + Diana's memory stay live and waking is instant.
xset s 1200 1200 2>/dev/null || true
xset +dpms 2>/dev/null || true
xset dpms 1200 1200 1200 2>/dev/null || true

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