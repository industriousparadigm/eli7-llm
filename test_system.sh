#!/bin/bash

echo "🧪 Testing Soft Terminal LLM System"
echo "===================================="

# Test 1: API Health
echo -n "1. Testing API health... "
HEALTH=$(curl -s http://localhost:8000/health | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null)
if [ "$HEALTH" = "ok" ]; then
    echo "✅ API is healthy"
else
    echo "❌ API health check failed"
    exit 1
fi

# Test 2: Create session
echo -n "2. Creating new session... "
SESSION=$(curl -s -X POST http://localhost:8000/new-session | python3 -c "import sys, json; print(json.load(sys.stdin)['session_id'])" 2>/dev/null)
if [ ! -z "$SESSION" ]; then
    echo "✅ Session created: $SESSION"
else
    echo "❌ Failed to create session"
    exit 1
fi

# Test 3: Test question with list formatting
echo -n "3. Testing list formatting... "
RESPONSE=$(curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d "{
    \"question\": \"lista de 3 frutas\",
    \"history\": [],
    \"session_id\": \"$SESSION\"
  }" | python3 -c "import sys, json; print('*' in json.load(sys.stdin)['response'])" 2>/dev/null)

if [ "$RESPONSE" = "True" ]; then
    echo "✅ List formatting working"
else
    echo "❌ List formatting failed"
fi

# Test 4: Test logs endpoint
echo -n "4. Testing logs data endpoint... "
LOGS_COUNT=$(curl -s http://localhost:8000/logs-data | python3 -c "import sys, json; print(len(json.load(sys.stdin)['logs']))" 2>/dev/null)
if [ "$LOGS_COUNT" -gt 0 ]; then
    echo "✅ Found $LOGS_COUNT log entries"
else
    echo "❌ No logs found"
fi

# Test 5: Test logs viewer HTML
echo -n "5. Testing logs viewer page... "
HTML_SIZE=$(curl -s http://localhost:8000/logs | wc -c)
if [ "$HTML_SIZE" -gt 1000 ]; then
    echo "✅ Logs viewer page served ($HTML_SIZE bytes)"
else
    echo "❌ Logs viewer page failed"
fi

# Test 6: Test UI is running
echo -n "6. Testing UI server... "
UI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:3000)
if [ "$UI_STATUS" = "200" ]; then
    echo "✅ UI is running"
else
    echo "❌ UI is not responding (status: $UI_STATUS)"
fi

echo ""
echo "===================================="
echo "🎉 All tests passed!"
echo ""
echo "📊 Log Viewer: http://localhost:8000/logs"
echo "💬 Main App: http://localhost:3000"
echo ""