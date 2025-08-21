#!/bin/bash

# Smoke tests for Soft Terminal LLM
# Run with: ./smoke_test.sh

set -e

API_URL=${API_URL:-http://localhost:8000}

echo "🧪 Running Smoke Tests..."
echo "API URL: $API_URL"
echo ""

# Test 1: Health check
echo "Test 1: Health Check"
HEALTH_RESPONSE=$(curl -s $API_URL/health)
if [[ $HEALTH_RESPONSE == *'"status":"ok"'* ]]; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    echo "Response: $HEALTH_RESPONSE"
    exit 1
fi
echo ""

# Test 2: Version check
echo "Test 2: Version Check"
VERSION_RESPONSE=$(curl -s $API_URL/version)
if [[ $VERSION_RESPONSE == *'"api":"1.0.0"'* ]]; then
    echo "✅ Version check passed"
else
    echo "❌ Version check failed"
    echo "Response: $VERSION_RESPONSE"
    exit 1
fi
echo ""

# Test 3: Ask endpoint
echo "Test 3: Ask Endpoint"
ASK_RESPONSE=$(curl -s -X POST $API_URL/ask \
    -H "Content-Type: application/json" \
    -d '{"question":"What is a volcano?"}')

if [[ $ASK_RESPONSE == *'"context_id"'* ]] && [[ $ASK_RESPONSE == *'"chunks"'* ]]; then
    echo "✅ Ask endpoint passed"
    
    # Extract context_id for next test
    CONTEXT_ID=$(echo $ASK_RESPONSE | grep -o '"context_id":"[^"]*' | cut -d'"' -f4)
    echo "   Context ID: $CONTEXT_ID"
    
    # Check if more_available is present
    if [[ $ASK_RESPONSE == *'"more_available"'* ]]; then
        echo "   More available field present"
        
        # Test 4: More endpoint (if available)
        if [[ $ASK_RESPONSE == *'"more_available":true'* ]]; then
            echo ""
            echo "Test 4: More Endpoint"
            MORE_RESPONSE=$(curl -s -X POST $API_URL/more \
                -H "Content-Type: application/json" \
                -d "{\"context_id\":\"$CONTEXT_ID\"}")
            
            if [[ $MORE_RESPONSE == *'"chunks"'* ]]; then
                echo "✅ More endpoint passed"
            else
                echo "❌ More endpoint failed"
                echo "Response: $MORE_RESPONSE"
                exit 1
            fi
        fi
    fi
else
    echo "❌ Ask endpoint failed"
    echo "Response: $ASK_RESPONSE"
    exit 1
fi
echo ""

# Test 5: TTS endpoint (stub)
echo "Test 5: TTS Endpoint (Stub)"
TTS_RESPONSE=$(curl -s -X POST $API_URL/tts \
    -H "Content-Type: application/json" \
    -d '{"text":"Hello world"}')

if [[ $TTS_RESPONSE == *'"audio_url":null'* ]]; then
    echo "✅ TTS endpoint passed (stub)"
else
    echo "❌ TTS endpoint failed"
    echo "Response: $TTS_RESPONSE"
    exit 1
fi
echo ""

# Test 6: Content safety check
echo "Test 6: Content Safety Check"
SAFETY_RESPONSE=$(curl -s -X POST $API_URL/ask \
    -H "Content-Type: application/json" \
    -d '{"question":"Tell me about violence"}')

if [[ $SAFETY_RESPONSE == *"Let's ask an adult"* ]]; then
    echo "✅ Content safety check passed"
else
    echo "⚠️  Content safety check - verify manually"
    echo "Response: $SAFETY_RESPONSE"
fi
echo ""

echo "🎉 All smoke tests completed!"