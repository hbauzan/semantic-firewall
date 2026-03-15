#!/bin/bash
while true; do
  clear
  echo "======================================"
  echo " PHASE-LOCK SEMANTIC FIREWALL COMMANDER"
  echo "======================================"
  echo " [S] Start Server"
  echo " [U] Start UI"
  echo " [T] Run Tests"
  echo " [O] Ollama Menu (llama3.1)"
  echo " [Q] Quit"
  echo "======================================"
  read -p " Select an option: " choice
  case $choice in
    [Ss]* ) ./run_server.sh; read -p "Press Enter to continue..." ;;
    [Uu]* ) ./run_ui.sh; read -p "Press Enter to continue..." ;;
    [Tt]* ) ./run_tests.sh; read -p "Press Enter to continue..." ;;
    [Oo]* ) echo "Starting Ollama serve..."; (ollama serve >/dev/null 2>&1 &); sleep 2; ollama run llama3.1; read -p "Press Enter to continue..." ;;
    [Qq]* ) exit ;;
    * ) echo "Please answer S, U, T, O, or Q."; read -p "Press Enter..." ;;
  esac
done
