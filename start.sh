#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Soft Terminal LLM...${NC}"
echo ""

# Start containers in background
docker-compose up -d

# Check if containers started successfully
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Application started successfully!${NC}"
    echo ""
    echo -e "${YELLOW}📍 Access the application at:${NC}"
    echo -e "   ${GREEN}➜${NC} UI (Frontend):  ${BLUE}http://localhost:3000${NC}"
    echo -e "   ${GREEN}➜${NC} API (Backend):  ${BLUE}http://localhost:8000${NC}"
    echo -e "   ${GREEN}➜${NC} Logs Viewer:    ${BLUE}http://localhost:8000/logs${NC}"
    echo ""
    echo -e "${YELLOW}📝 Useful commands:${NC}"
    echo -e "   ${GREEN}npm run logs${NC}     - View all logs"
    echo -e "   ${GREEN}npm stop${NC}         - Stop the application"
    echo -e "   ${GREEN}npm restart${NC}      - Restart the application"
else
    echo -e "${YELLOW}⚠️  Failed to start containers${NC}"
    echo "Run 'docker-compose logs' to see what went wrong"
fi