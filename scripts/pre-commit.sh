#!/usr/bin/env bash
# Pre-commit hook script
# Runs code quality checks and tests before allowing a commit.
# Commands mirror those in README.md (Code Quality and Running Tests sections).

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

FAILED=0
REPO_ROOT="$(git rev-parse --show-toplevel)"
DOCKER_COMPOSE_FILE="$REPO_ROOT/docker/docker-compose.yml"

# ---------------------------------------------------------------------------
# Detect whether to run commands inside Docker or locally
# ---------------------------------------------------------------------------
use_docker=false
if command -v docker-compose &>/dev/null || docker compose version &>/dev/null 2>&1; then
    # Resolve docker-compose binary (v1 vs v2)
    if command -v docker-compose &>/dev/null; then
        DC="docker-compose -f $DOCKER_COMPOSE_FILE"
    else
        DC="docker compose -f $DOCKER_COMPOSE_FILE"
    fi

    # Check if the web service container is actually running
    if $DC ps web 2>/dev/null | grep -qE "Up|running"; then
        use_docker=true
    fi
fi

run_cmd() {
    local label="$1"
    shift
    echo -e "\n${YELLOW}>>> $label${NC}"
    if "$@"; then
        echo -e "${GREEN}✓ $label passed${NC}"
    else
        echo -e "${RED}✗ $label failed${NC}"
        FAILED=1
    fi
}

# ---------------------------------------------------------------------------
# Helper: run a command either inside the Docker web container or locally
# ---------------------------------------------------------------------------
exec_check() {
    local label="$1"
    shift  # remaining args are the command (without "docker-compose exec web" prefix)
    if [ "$use_docker" = true ]; then
        run_cmd "$label" $DC exec -T web "$@"
    else
        run_cmd "$label" "$@"
    fi
}

# ---------------------------------------------------------------------------
echo -e "\n=========================================="
echo -e "  Pre-commit checks"
if [ "$use_docker" = true ]; then
    echo -e "  Mode: Docker (docker-compose web container)"
else
    echo -e "  Mode: Local (tools must be on PATH)"
fi
echo -e "==========================================\n"

# ---------------------------------------------------------------------------
# Code Quality checks (README.md § Code Quality)
# Use --check / --check-only flags so the hook never silently modifies files.
# ---------------------------------------------------------------------------

# Black – formatting check
exec_check "Black (formatting)" black --check .

# isort – import-sorting check
exec_check "isort (import sorting)" isort --check-only .

# flake8 – linting
exec_check "flake8 (linting)" flake8 .

# ---------------------------------------------------------------------------
# Tests (README.md § Running Tests)
# ---------------------------------------------------------------------------

exec_check "pytest" pytest

# ---------------------------------------------------------------------------
echo -e "\n=========================================="
if [ "$FAILED" -ne 0 ]; then
    echo -e "${RED}Pre-commit checks FAILED. Fix the issues above and try again.${NC}"
    echo -e "==========================================\n"
    exit 1
else
    echo -e "${GREEN}All pre-commit checks passed.${NC}"
    echo -e "==========================================\n"
    exit 0
fi
