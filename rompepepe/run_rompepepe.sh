#!/bin/bash
# rompepepe — Autonomous Semantic Stress-Testing & Boundary Exploration Engine
# Interactive Control Panel

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

ensure_env() {
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}[!] .env not found. Creating from .env.example...${NC}"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo -e "${GREEN}[+] .env created successfully.${NC}"
        else
            echo -e "${RED}[!] .env.example not found.${NC}"
            return 1
        fi
    fi
}

run_python_script() {
    cd "$PROJECT_ROOT"
    PYTHONPATH="$PROJECT_ROOT" uv run --directory backend python -m rompepepe.main "$@"
    cd "$SCRIPT_DIR"
}

ensure_env

while true; do
    clear
    echo -e "${CYAN}========================================================================${NC}"
    echo -e "${BOLD}${CYAN}   Rompé Pepe! Rompé nomá!!! — Semantic Robustness & Boundary Exploration Engine${NC}"
    echo -e "${CYAN}========================================================================${NC}"
    echo -e "${YELLOW} Target API:${NC} $(grep FIREWALL_API_BASE_URL .env 2>/dev/null | cut -d= -f2 || echo 'http://localhost:8000')"
    echo -e "${YELLOW} Explorer:${NC}   ${BOLD}${GREEN}$(grep EXPLORER_PROVIDER .env 2>/dev/null | cut -d= -f2 || echo 'google')${NC} (${CYAN}$(grep EXPLORER_MODEL .env 2>/dev/null | cut -d= -f2 || echo 'gemini-1.5-flash')${NC})"
    echo -e "${CYAN}========================================================================${NC}"
    echo -e " ${GREEN}[1]${NC} Run Systematic Matrix Search (Grid Search)"
    echo -e " ${GREEN}[2]${NC} Run Closed-Loop Adaptive Exploratory Fuzzing"
    echo -e " ${GREEN}[3]${NC} ${BOLD}${YELLOW}Select / Configure Explorer Model${NC} (Gemini, Claude, GPT, Ollama)"
    echo -e " ${GREEN}[4]${NC} ${BOLD}${CYAN}Inspect & Sync Active LanceDB Corpus Dataset${NC}"
    echo -e " ${GREEN}[5]${NC} ${BOLD}${GREEN}Build Agent Handoff Pack${NC} (rompepepe_context.txt)"
    echo -e " ${GREEN}[6]${NC} View Past QA & Boundary Reports"
    echo -e " ${GREEN}[7]${NC} Resume Interrupted Session"
    echo -e " ${GREEN}[8]${NC} Edit .env Directly"
    echo -e " ${RED}[9]${NC} Quit"
    echo -e "${CYAN}========================================================================${NC}"
    
    # Check if there is an interrupted session to alert the user
    INTERRUPTED_SESSION=""
    if [ -d "vault/sessions" ]; then
        INTERRUPTED_SESSION=$(grep -l '"status": "interrupted"' vault/sessions/*.json 2>/dev/null | head -n 1 || true)
    fi

    if [ -n "$INTERRUPTED_SESSION" ]; then
        SESS_ID=$(basename "$INTERRUPTED_SESSION" .json)
        echo -e "${YELLOW} [!] Interrupted session detected: ${BOLD}${SESS_ID}${NC}"
        echo -e "${YELLOW}     Press '7' to resume where it left off.${NC}"
        echo -e "${CYAN}========================================================================${NC}"
    fi

    read -p " Select an option [1-9]: " choice
    case $choice in
        1)
            echo -e "\n${CYAN}Select Intensity Tier:${NC}"
            echo -e " [1] 🟢 Light (Smoke / Fast, ~10 steps)"
            echo -e " [2] 🟡 Normal (Standard, ~36 steps)"
            echo -e " [3] 🔴 Heavy (Exhaustive, ~100+ steps)"
            read -p " Select tier [1-3, default 2]: " tier_choice
            case $tier_choice in
                1) TIER="light" ;;
                3) TIER="heavy" ;;
                *) TIER="normal" ;;
            esac
            echo -e "\n${GREEN}[+] Launching Systematic Matrix Search (Strategy A, Tier: ${TIER})...${NC}"
            run_python_script --strategy grid --tier "$TIER"
            read -p "Press Enter to return to menu..."
            ;;
        2)
            echo -e "\n${CYAN}Select Intensity Tier:${NC}"
            echo -e " [1] 🟢 Light (Smoke / Fast, 15 iterations)"
            echo -e " [2] 🟡 Normal (Standard, 50 iterations)"
            echo -e " [3] 🔴 Heavy (Exhaustive / Continuous, 250 iterations)"
            read -p " Select tier [1-3, default 2]: " tier_choice
            case $tier_choice in
                1) TIER="light"; ITERS=15 ;;
                3) TIER="heavy"; ITERS=250 ;;
                *) TIER="normal"; ITERS=50 ;;
            esac
            echo -e "\n${GREEN}[+] Launching Adaptive Exploratory Fuzzing (Strategy B, Tier: ${TIER}, ${ITERS} iterations)...${NC}"
            run_python_script --strategy fuzz --tier "$TIER" --iterations "$ITERS"
            read -p "Press Enter to return to menu..."
            ;;
        3)
            run_python_script --select-model
            read -p "Press Enter to return to menu..."
            ;;
        4)
            run_python_script --sync-corpus
            read -p "Press Enter to return to menu..."
            ;;
        5)
            echo -e "\n${GREEN}[+] Building Agent Handoff Pack...${NC}"
            run_python_script --build-pack
            read -p "Press Enter to return to menu..."
            ;;
        6)
            run_python_script --view-reports
            read -p "Press Enter to return to menu..."
            ;;
        7)
            if [ -n "$INTERRUPTED_SESSION" ]; then
                SESS_ID=$(basename "$INTERRUPTED_SESSION" .json)
                read -p " Resume previous session [${SESS_ID}]? (y/n): " confirm
                if [[ "$confirm" =~ ^[Yy]$ ]]; then
                    run_python_script --resume "$SESS_ID"
                else
                    run_python_script --resume-latest
                fi
            else
                run_python_script --resume-latest
            fi
            read -p "Press Enter to return to menu..."
            ;;
        8)
            echo -e "\n${CYAN}Current .env configuration:${NC}"
            cat .env
            echo -e "\n${YELLOW}Opening .env in editor...${NC}"
            ${EDITOR:-nano} .env || vim .env || open .env
            read -p "Press Enter to return to menu..."
            ;;
        9)
            echo -e "\n${GREEN}Goodbye! Keep breaking boundaries.${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}[!] Invalid option. Please select 1-7.${NC}"
            sleep 1
            ;;
    esac
done
