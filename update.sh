#!/bin/bash
# ------------------------------------------------------------------------------
# Docker LLM Stack Update and Patch Script
# Automates git pull, docker image pull, recreation, and cleanup.
# ------------------------------------------------------------------------------

# Color codes for premium CLI output
BOLD='\033[1m'
CYAN='\033[96m'
GREEN='\033[92m'
WARNING='\033[93m'
FAIL='\033[91m'
ENDC='\033[0m'

echo -e "${CYAN}${BOLD}🔄 Starting LLM Stack Update Process...${ENDC}\n"

# 1. Check Git status and pull latest repository changes
if [ -d .git ]; then
    echo -e "${BOLD}[1/4] Checking repository updates via Git...${ENDC}"
    # Fetch and pull main branch
    git fetch origin main
    git pull origin main
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Repository updated successfully.${ENDC}\n"
    else
        echo -e "${WARNING}⚠️  Warning: Git pull failed. Continuing with container updates...${ENDC}\n"
    fi
else
    echo -e "${WARNING}⚠️  No git repository found in current directory. Skipping repository update...${ENDC}\n"
fi

# 2. Pull latest Docker container images
echo -e "${BOLD}[2/4] Pulling latest Docker images...${ENDC}"
docker compose pull
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Docker images pulled successfully.${ENDC}\n"
else
    echo -e "${WARNING}⚠️  Warning: Failed to pull some images. Recreating containers with cached images...${ENDC}\n"
fi

# 3. Recreate and restart containers with updates
echo -e "${BOLD}[3/4] Recreating containers with new images and configs...${ENDC}"
docker compose up -d --remove-orphans
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Stack restarted and running in the background.${ENDC}\n"
else
    echo -e "${FAIL}❌ Error: Failed to recreate docker containers.${ENDC}"
    exit 1
fi

# 4. Clean up old dangling Docker images (to conserve disk space)
echo -e "${BOLD}[4/4] Pruning old, unused Docker images to save space...${ENDC}"
docker image prune -f
echo -e "${GREEN}✅ Cleanup completed.${ENDC}\n"

echo -e "${GREEN}${BOLD}🎉 LLM Stack updated successfully and is now running!${ENDC}"
echo -e "Access points:"
echo -e "📱  Open WebUI:       http://localhost:8080"
echo -e "🤖  OpenClaw Gateway: http://localhost:18789"
echo -e "🦙  Ollama API:       http://localhost:11434"
echo -e "============================================================\n"
