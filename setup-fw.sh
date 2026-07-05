#!/bin/bash
# Three-Headed Semantic Firewall — Control Panel (bare-metal, uv + pnpm)

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

NON_INTERACTIVE_CHOICE=""

ensure_env() {
    if [ ! -f ".env" ]; then
        echo -e "${YELLOW}[!] .env not found. Creating from .env.example...${NC}"
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo -e "${GREEN}[+] .env created. Don't forget your towel!${NC}"
        else
            echo -e "${RED}[!] .env.example not found.${NC}"
            return 1
        fi
    fi
}

require_cmd() {
    local cmd="$1"
    local hint="$2"
    if ! command -v "$cmd" &>/dev/null; then
        echo -e "${RED}[!] Required command not found: ${cmd}${NC}"
        echo -e "${YELLOW}    ${hint}${NC}"
        return 1
    fi
}

require_dev_toolchain() {
    require_cmd uv "Install uv: https://docs.astral.sh/uv/" || return 1
    require_cmd pnpm "Install pnpm: https://pnpm.io/installation" || return 1
    require_cmd node "Install Node.js 20+: https://nodejs.org/" || return 1
}

print_header() {
    clear
    echo -e "${BLUE}====================================================${NC}"
    echo -e "${CYAN}  THREE-HEADED SEMANTIC FIREWALL — CONTROL PANEL${NC}"
    echo -e "${YELLOW}       Don't Panic — The Answer is 42${NC}"
    echo -e "${BLUE}====================================================${NC}"
}

show_startup_success_banner() {
    local fe_url="${1:-http://localhost:5173}"
    local be_url="http://127.0.0.1:8000/health"
    echo -e "\n${GREEN}=====================================================================${NC}"
    echo -e "${GREEN}  DON'T PANIC! The Answer is 42 & Your Firewall is Operational${NC}"
    echo -e "${GREEN}=====================================================================${NC}"
    echo -e "${CYAN}  Frontend Web GUI:${NC} ${YELLOW}${fe_url}${NC}"
    echo -e "${CYAN}  Backend API:     ${NC} ${YELLOW}${be_url}${NC}"
    echo -e "${BLUE}---------------------------------------------------------------------${NC}"
    echo -e "${YELLOW}  Copy & paste the GUI URL into your favorite web browser.${NC}"
    echo -e "${GREEN}=====================================================================${NC}"
}

path_size_human() {
    local target="$1"
    if [ -e "$target" ]; then
        du -sh "$target" 2>/dev/null | awk '{print $1}'
    else
        echo "—"
    fi
}

stop_port_processes() {
    local port="$1"
    local label="$2"
    local pattern="${3:-python|uvicorn|uv|node|vite}"

    if ! lsof -t -i :"$port" &>/dev/null; then
        echo -e "${YELLOW}[i] No process on port ${port}.${NC}"
        return 0
    fi

    local pids
    pids=$(lsof -t -i :"$port" 2>/dev/null || true)
    for pid in $pids; do
        local cmd_info
        cmd_info=$(ps -p "$pid" -o command= 2>/dev/null || true)
        if echo "$cmd_info" | grep -qiE "$pattern"; then
            echo -e "${YELLOW}[!] Stopping ${label} (PID ${pid}) on port ${port}...${NC}"
            kill "$pid" 2>/dev/null || true
            sleep 1
            if ps -p "$pid" &>/dev/null; then
                kill -9 "$pid" 2>/dev/null || true
            fi
            echo -e "${GREEN}[+] Stopped PID ${pid}.${NC}"
        else
            echo -e "${YELLOW}[i] Port ${port} PID ${pid} skipped (not ${label}): ${cmd_info}${NC}"
        fi
    done
}

stop_local_backend() { stop_port_processes 8000 "backend" "python|uvicorn|uv"; }
stop_local_frontend() { stop_port_processes 5173 "frontend" "node|vite"; }

start_backend_background() {
    stop_local_backend >/dev/null 2>&1 || true
    echo -e "${GREEN}[+] Starting FastAPI backend in background (Deep Thought is waking up)...${NC}"
    ( cd backend && nohup uv run python -m app.main > backend.log 2>&1 & )
    echo -e "${CYAN}[i] Logs: backend/backend.log${NC}"
}

wait_for_health() {
    local timeout="${1:-120}"
    local log_file="backend/backend.log"
    local elapsed=0
    local spin=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
    local spin_idx=0

    echo -e "\n${CYAN}Consulting Deep Thought... loading BGE-M3 across 1024 dimensions...${NC}"
    echo -e "${YELLOW}(don't forget your towel)${NC}\n"

    while [ "$elapsed" -lt $((timeout * 5)) ]; do
        if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
            echo -e "\n${GREEN}[+] Backend healthy. The Answer is 42.${NC}"
            return 0
        fi

        local stage_desc="Consulting Deep Thought... initializing Python runtime..."
        if [ -f "$log_file" ]; then
            local last_log
            last_log=$(tail -n 30 "$log_file" 2>/dev/null | grep -iE "embed|lance|model|uvicorn|started|loading|bge" | tail -n 1 || true)
            if [[ "$last_log" =~ [Ee]mbed ]]; then
                stage_desc="Loading BGE-M3 embedding matrix (1024 dimensions)..."
            elif [[ "$last_log" =~ [Ll]ance ]]; then
                stage_desc="Initializing LanceDB vector storage across the galaxy..."
            elif [[ "$last_log" =~ [Uu]vicorn|[Ss]tarted ]]; then
                stage_desc="Warming up hyperdrive engines for semantic firewall..."
            fi
        fi

        local secs=$((elapsed / 5))
        echo -ne "\r  ${CYAN}${spin[$spin_idx]}${NC} ${YELLOW}[${secs}s]${NC} ${GREEN}${stage_desc}${NC} \033[K"
        spin_idx=$(( (spin_idx + 1) % 10 ))
        sleep 0.2
        elapsed=$((elapsed + 1))
    done

    echo -e "\n${RED}[!] Health check timed out after ${timeout}s. See backend/backend.log${NC}"
    return 1
}

run_install() {
    ensure_env || return 1
    require_dev_toolchain || return 1
    echo -e "${CYAN}[i] Syncing backend dependencies (uv sync)...${NC}"
    (cd backend && uv sync)
    echo -e "${CYAN}[i] Installing frontend dependencies (pnpm install)...${NC}"
    (cd frontend && pnpm install)
    echo -e "\n${GREEN}[+] Install complete. Ready to cross the semantic galaxy. Don't forget your towel!${NC}"
}

warn_ollama() {
    if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        echo -e "${GREEN}[+] Ollama is reachable on :11434.${NC}"
    else
        echo -e "${YELLOW}[!] Ollama not detected on :11434. Chat will need a provider or \`ollama serve\`.${NC}"
    fi
}

run_dev_mode() {
    ensure_env || return 1
    require_dev_toolchain || return 1
    echo -e "\n${GREEN}Calculating the Answer to the Ultimate Question of Life, the Universe, and Everything... 42!${NC}"
    echo -e "${GREEN}Initializing Development Mode...${NC}\n"
    run_install || return 1
    warn_ollama
    stop_local_frontend >/dev/null 2>&1 || true
    start_backend_background
    if ! wait_for_health 120; then return 1; fi
    show_startup_success_banner "http://localhost:5173"
    echo -e "\n${CYAN}[i] Starting Vite frontend in foreground (Ctrl+C stops UI only).${NC}\n"
    ./run_ui.sh
}

run_ollama_check() {
    command -v ollama &>/dev/null || { echo -e "${RED}[!] ollama CLI not installed.${NC}"; return 1; }
    if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        echo -e "${YELLOW}[i] Starting ollama serve in background...${NC}"
        (ollama serve >/dev/null 2>&1 &)
        sleep 2
    fi
    if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        echo -e "${GREEN}[+] Ollama is online.${NC}"
        if ollama list 2>/dev/null | grep -q "llama3.1"; then
            echo -e "${GREEN}[+] llama3.1 is available.${NC}"
        else
            echo -e "${YELLOW}[i] Pulling llama3.1...${NC}"
            ollama pull llama3.1
        fi
    else
        echo -e "${RED}[!] Could not reach Ollama on :11434.${NC}"
        return 1
    fi
}

run_diagnostics() {
    if ! curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo -e "${RED}[!] Backend is not running. Start dev mode first (option 2).${NC}"
        return 1
    fi
    echo -e "${CYAN}[i] System Heartbeat — consulting Deep Thought...${NC}\n"
    local health
    health=$(curl -sf http://127.0.0.1:8000/health 2>/dev/null || echo "{}")
    echo -e "${GREEN}Health:${NC} $health"
    if curl -sf http://127.0.0.1:8000/galaxy/stats >/dev/null 2>&1; then
        local stats
        stats=$(curl -sf http://127.0.0.1:8000/galaxy/stats 2>/dev/null || echo "{}")
        echo -e "${GREEN}Stats:${NC} $stats"
    fi
    if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        echo -e "${GREEN}Ollama:${NC} online"
    else
        echo -e "${YELLOW}Ollama:${NC} offline"
    fi
}

run_load_tests() {
    require_cmd uv "Install uv first." || return 1
    if ! curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
        echo -e "${RED}[!] Backend must be running for load tests.${NC}"
        return 1
    fi
    (cd backend && uv run python tests/load_test_suite.py)
}

run_calibration_menu() {
    require_cmd uv "Install uv first." || return 1
    echo -e "${CYAN}--- Calibration Harness (evaluate) ---${NC}"
    echo -e "  1. automotive_v1.json"
    echo -e "  2. medical_v1.json"
    echo -e "  3. gol_2020_v1.json"
    echo -e "  4. Custom path"
    read -r -p "Select dataset [1-4] [1]: " ds_choice
    ds_choice=${ds_choice:-1}
    local dataset=""
    case "$ds_choice" in
        1) dataset="calibration/datasets/automotive_v1.json" ;;
        2) dataset="calibration/datasets/medical_v1.json" ;;
        3) dataset="calibration/datasets/gol_2020_v1.json" ;;
        4) read -r -p "Dataset path (relative to backend/): " dataset ;;
        *) echo -e "${RED}[!] Invalid choice.${NC}"; return 1 ;;
    esac
    (cd backend && uv run python tests/calibration_suite.py evaluate --dataset "$dataset")
}

run_logs_menu() {
    echo -e "${CYAN}--- View Logs ---${NC}"
    echo -e "  1. Backend (backend/backend.log)"
    echo -e "  2. Hint: frontend logs appear in the terminal running Vite"
    read -r -p "Select [1-2] [1]: " logs_choice
    logs_choice=${logs_choice:-1}
    case "$logs_choice" in
        1)
            if [ -f "backend/backend.log" ]; then
                echo -e "${CYAN}[i] tail -f backend/backend.log (Ctrl+C to exit)${NC}\n"
                tail -f "backend/backend.log"
            else
                echo -e "${RED}[!] No backend/backend.log yet.${NC}"
            fi ;;
        2) echo -e "${YELLOW}[i] Run ./run_ui.sh or option 4 to see Vite output in that terminal.${NC}" ;;
        *) echo -e "${RED}[!] Invalid option.${NC}" ;;
    esac
}

run_stop_services() {
    echo -e "${YELLOW}[i] Stopping services (data preserved)...${NC}"
    stop_local_backend
    stop_local_frontend
    echo -e "${GREEN}[+] Stop complete.${NC}"
}

prompt_yn() {
    local label="$1"
    local default="${2:-N}"
    local prompt="[y/N]"
    [ "$default" = "Y" ] && prompt="[Y/n]"
    echo -n -e "  ${label} ${prompt}: "
    read -r ans
    ans=${ans:-$default}
    [[ "$ans" =~ ^[Yy]$ ]]
}

run_custom_cleanup() {
    print_header
    echo -e "\n${CYAN}=== Heart of Gold Maintenance Bay ===${NC}"
    echo -e "${YELLOW}Select what to wipe (leave blank = keep).${NC}\n"
    echo -e "${CYAN}Current footprint:${NC}"
    printf "  backend.log      %s\n" "$(path_size_human backend/backend.log)"
    printf "  backend/data/    %s\n" "$(path_size_human backend/data)"
    printf "  lancedb_data/    %s\n" "$(path_size_human backend/lancedb_data)"
    printf "  node_modules/    %s\n" "$(path_size_human frontend/node_modules)"
    printf "  backend/.venv/   %s\n" "$(path_size_human backend/.venv)"
    echo ""
    local wipe_backend=false wipe_frontend=false wipe_log=false wipe_session=false
    local wipe_lance=false wipe_auto_ds=false wipe_artifacts=false wipe_pycache=false
    local wipe_node_modules=false wipe_venv=false destructive=false
    prompt_yn "A) Stop backend process (port 8000)" "N" && wipe_backend=true
    prompt_yn "B) Stop frontend process (port 5173)" "N" && wipe_frontend=true
    prompt_yn "C) Delete backend/backend.log" "Y" && wipe_log=true
    prompt_yn "D) Delete backend/data/ (profiles, chat, sniffer)" "N" && { wipe_session=true; destructive=true; }
    prompt_yn "E) Delete backend/lancedb_data/ (corpus vectors)" "N" && { wipe_lance=true; destructive=true; }
    prompt_yn "F) Delete auto calibration datasets (auto_*.json)" "N" && wipe_auto_ds=true
    prompt_yn "G) Delete test artifacts (metrics CSV/MD, context.txt)" "Y" && wipe_artifacts=true
    prompt_yn "H) Delete Python caches (__pycache__, .pytest_cache)" "Y" && wipe_pycache=true
    prompt_yn "I) Delete frontend/node_modules/" "N" && { wipe_node_modules=true; destructive=true; }
    prompt_yn "J) Delete backend/.venv/" "N" && { wipe_venv=true; destructive=true; }
    echo ""
    echo -e "${CYAN}--- Demolition summary ---${NC}"
    $wipe_backend && echo -e "  ${RED}*${NC} Stop backend"
    $wipe_frontend && echo -e "  ${RED}*${NC} Stop frontend"
    $wipe_log && echo -e "  ${RED}*${NC} backend/backend.log"
    $wipe_session && echo -e "  ${RED}*${NC} backend/data/"
    $wipe_lance && echo -e "  ${RED}*${NC} backend/lancedb_data/"
    $wipe_auto_ds && echo -e "  ${RED}*${NC} calibration/datasets/auto_*.json"
    $wipe_artifacts && echo -e "  ${RED}*${NC} test artifacts"
    $wipe_pycache && echo -e "  ${RED}*${NC} Python caches"
    $wipe_node_modules && echo -e "  ${RED}*${NC} frontend/node_modules/"
    $wipe_venv && echo -e "  ${RED}*${NC} backend/.venv/"
    if ! $wipe_backend && ! $wipe_frontend && ! $wipe_log && ! $wipe_session && \
       ! $wipe_lance && ! $wipe_auto_ds && ! $wipe_artifacts && ! $wipe_pycache && \
       ! $wipe_node_modules && ! $wipe_venv; then
        echo -e "${YELLOW}[i] Nothing selected. The dolphins approve your caution.${NC}"
        return 0
    fi
    if $destructive; then
        echo ""
        echo -e "${RED}[!] Destructive targets selected.${NC}"
        read -r -p "Type YES to authorize Vogon demolition: " confirm
        if [ "$confirm" != "YES" ]; then
            echo -e "${YELLOW}[i] Demolition cancelled.${NC}"
            return 0
        fi
    fi
    $wipe_backend && stop_local_backend
    $wipe_frontend && stop_local_frontend
    $wipe_log && rm -f backend/backend.log && echo -e "${GREEN}[+] Removed backend.log${NC}"
    $wipe_session && rm -rf backend/data && echo -e "${GREEN}[+] Removed backend/data/${NC}"
    $wipe_lance && rm -rf backend/lancedb_data && echo -e "${GREEN}[+] Removed lancedb_data/${NC}"
    if $wipe_auto_ds; then
        rm -f backend/calibration/datasets/auto_*.json 2>/dev/null || true
        echo -e "${GREEN}[+] Removed auto_*.json datasets${NC}"
    fi
    if $wipe_artifacts; then
        rm -f backend/tests/metrics_report.csv backend/tests/db_scaling_metrics.md context.txt 2>/dev/null || true
        echo -e "${GREEN}[+] Removed test artifacts${NC}"
    fi
    if $wipe_pycache; then
        find backend -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
        find backend -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true
        echo -e "${GREEN}[+] Removed Python caches${NC}"
    fi
    $wipe_node_modules && rm -rf frontend/node_modules && echo -e "${GREEN}[+] Removed node_modules/${NC}"
    $wipe_venv && rm -rf backend/.venv && echo -e "${GREEN}[+] Removed .venv/${NC}"
    echo -e "\n${GREEN}Demolition complete. O frettled gruntbuggly!${NC}"
}

inspect_stale_instances() {
    print_header
    echo -e "\n${CYAN}=== Instance Inspector ===${NC}"
    echo -e "${YELLOW}Scanning bare-metal processes (Docker not used in this project).${NC}\n"
    local bare_found=false
    local ports=(8000 5173 11434)
    local labels=("Backend (FastAPI)" "Frontend (Vite)" "Ollama")
    for i in "${!ports[@]}"; do
        local port=${ports[$i]}
        local pids
        pids=$(lsof -t -i :"$port" 2>/dev/null || true)
        if [ -n "$pids" ]; then
            bare_found=true
            for pid in $pids; do
                local cmd elapsed
                cmd=$(ps -p "$pid" -o command= 2>/dev/null | head -c 90 || true)
                elapsed=$(ps -p "$pid" -o etime= 2>/dev/null | xargs || true)
                printf "  ${GREEN}PORT %-5s${NC} PID ${YELLOW}%-8s${NC} uptime: %-10s  %s\n" "$port" "$pid" "$elapsed" "$cmd"
            done
        fi
    done
    if ! $bare_found; then
        echo -e "${YELLOW}[i] No processes on ports 8000 / 5173 / 11434.${NC}"
    fi
    echo ""
    echo -e "${CYAN}Actions:${NC}"
    echo -e "  1. Kill backend (8000)"
    echo -e "  2. Kill frontend (5173)"
    echo -e "  3. Kill by PID"
    echo -e "  0. Back"
    read -r -p "Select [0-3] [0]: " action
    action=${action:-0}
    case "$action" in
        1) stop_local_backend ;;
        2) stop_local_frontend ;;
        3)
            read -r -p "PID to kill: " kill_pid
            [ -n "$kill_pid" ] && { kill "$kill_pid" 2>/dev/null || kill -9 "$kill_pid" 2>/dev/null || true; echo -e "${GREEN}[+] Sent signal to PID ${kill_pid}.${NC}"; }
            ;;
        0) ;;
        *) echo -e "${RED}[!] Invalid option.${NC}" ;;
    esac
}

run_handoff_pack() {
    read -r -p "Include roadmap/ in pack? [y/N]: " inc_roadmap
    if [[ "${inc_roadmap:-N}" =~ ^[Yy]$ ]]; then
        ./run_pack.sh --all
    else
        ./run_pack.sh
    fi
}

show_menu() {
    print_header
    echo -e "${CYAN}--- Environment ---${NC}"
    echo -e "  ${GREEN}1.${NC} First-time Install (uv sync + pnpm install)"
    echo -e "  ${GREEN}2.${NC} Start Development Mode (backend bg + frontend)"
    echo -e "  ${GREEN}3.${NC} Start Backend only (foreground)"
    echo -e "  ${GREEN}4.${NC} Start Frontend only (foreground)"
    echo -e "  ${GREEN}5.${NC} Ollama: check / pull llama3.1"
    echo -e "${CYAN}--- Diagnostics & Tests ---${NC}"
    echo -e "  ${GREEN}6.${NC} System Heartbeat (health, embedder, corpus, ollama)"
    echo -e "  ${GREEN}7.${NC} Run Backend Unit Tests (pytest)"
    echo -e "  ${GREEN}8.${NC} Run Load Test Suite"
    echo -e "  ${GREEN}9.${NC} Run Calibration Harness (evaluate)"
    echo -e "${CYAN}--- Maintenance ---${NC}"
    echo -e "  ${GREEN}10.${NC} View Logs"
    echo -e "  ${GREEN}11.${NC} Stop Services (keep data)"
    echo -e "  ${GREEN}12.${NC} Custom Cleanup — pick what to wipe"
    echo -e "  ${GREEN}13.${NC} Inspect & Kill Stale Instances"
    echo -e "${CYAN}--- Handoff ---${NC}"
    echo -e "  ${GREEN}14.${NC} Build Agent Handoff Pack"
    echo -e "  ${GREEN}0.${NC} Exit (So long, and thanks for all the fish!)"
    echo -e "${BLUE}====================================================${NC}"
    echo -n -e "Select an option [0-14] [1]: "
}

ensure_env || true

if [ -n "${1:-}" ]; then
    if [[ "$1" =~ ^[0-9]+$ ]]; then
        NON_INTERACTIVE_CHOICE="$1"
    else
        echo "Usage: $0 [option_number 0-14]"
        exit 1
    fi
fi

while true; do
    if [ -n "${NON_INTERACTIVE_CHOICE}" ]; then
        choice="${NON_INTERACTIVE_CHOICE}"
    else
        show_menu
        read -r choice
        choice=${choice:-1}
    fi
    case "$choice" in
        1) run_install || true ;;
        2) run_dev_mode || true ;;
        3) ensure_env || true; require_dev_toolchain || true; ./run_server.sh ;;
        4) require_cmd pnpm "Install pnpm first." || true; ./run_ui.sh ;;
        5) run_ollama_check || true ;;
        6) run_diagnostics || true ;;
        7) ./run_tests.sh ;;
        8) run_load_tests || true ;;
        9) run_calibration_menu || true ;;
        10) run_logs_menu || true ;;
        11) run_stop_services || true ;;
        12) run_custom_cleanup || true ;;
        13) inspect_stale_instances || true ;;
        14) run_handoff_pack || true ;;
        0) echo -e "\n${GREEN}🐬 So long, and thanks for all the fish! Goodbye!${NC}\n"; exit 0 ;;
        *) echo -e "${RED}[!] Invalid option. Select 0-14.${NC}" ;;
    esac
    if [ -n "${NON_INTERACTIVE_CHOICE}" ]; then exit 0; fi
    echo -e "\nPress Enter to return to main menu..."
    read -r
done
