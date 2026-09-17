"""Main CLI entry point for rompepepe autonomous stress testing tool.
"""
import argparse
import asyncio
import logging
from pathlib import Path
import sys

from rompepepe.client.explorer_client import ExplorerClient
from rompepepe.client.firewall_client import FirewallClient
from rompepepe.config import get_config, update_env_file
from rompepepe.engines.adaptive_fuzzing import AdaptiveFuzzingEngine
from rompepepe.engines.grid_search import GridSearchEngine
from rompepepe.reports.generator import ReportGenerator
from rompepepe.state.models import SessionState
from rompepepe.state.session_manager import SessionManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rompepepe")


def format_progress(session: SessionState, elapsed_sec: float):
    total = session.total_steps
    curr = session.current_step

    passed = sum(1 for r in session.results if r.passed)
    stability = (passed / curr * 100.0) if curr > 0 else 100.0

    avg_step_time = elapsed_sec / curr if curr > 0 else 0.05
    remaining_sec = avg_step_time * (total - curr)
    eta_min = int(remaining_sec // 60)
    eta_sec = int(remaining_sec % 60)

    # ANSI Progress line
    sys.stdout.write(
        f"\r\033[K[\033[1;36m{curr}/{total}\033[0m tests - "
        f"\033[1;32m{stability:.1f}%\033[0m operational stability - "
        f"ETA: \033[1;33m{eta_min:02d}m {eta_sec:02d}s\033[0m] "
        f"Last prompt: '{session.results[-1].prompt[:30]}...'"
    )
    sys.stdout.flush()


async def select_model_menu(fw_client: FirewallClient | None = None):
    cfg = get_config()
    print("\n=======================================================")
    print("   SELECT EXPLORER LLM PROVIDER, MODEL & RATE LIMIT")
    print("=======================================================")
    print(f" Current Active: \033[1;32m{cfg.explorer_provider}\033[0m (\033[1;36m{cfg.explorer_model}\033[0m)")
    print(f" Current RPM Limit: \033[1;33m{cfg.explorer_rpm_limit} RPM\033[0m (Requests Per Minute)")
    print("=======================================================")
    print(" [1] Google Gemini — gemini-3.1-flash-lite (Firewall .env Default)")
    print(" [2] Google Gemini — gemini-2.0-flash")
    print(" [3] Google Gemini — gemini-1.5-flash")
    print(" [4] Anthropic — claude-3-5-sonnet-latest")
    print(" [5] OpenAI — gpt-4o")
    print(" [6] Ollama — llama3.1 (Local)")
    print(" [7] Auto-Sync from Target Firewall & .env")
    print(" [8] Custom Provider, Model String & RPM Limit")
    print("=======================================================")

    choice = input(" Select option [1-8]: ").strip()
    provider = cfg.explorer_provider
    model = cfg.explorer_model
    rpm_limit = str(cfg.explorer_rpm_limit)

    if choice == "1":
        provider, model = "google", "gemini-3.1-flash-lite"
    elif choice == "2":
        provider, model = "google", "gemini-2.0-flash"
    elif choice == "3":
        provider, model = "google", "gemini-1.5-flash"
    elif choice == "4":
        provider, model = "anthropic", "claude-3-5-sonnet-latest"
    elif choice == "5":
        provider, model = "openai", "gpt-4o"
    elif choice == "6":
        provider, model = "ollama", "llama3.1"
    elif choice == "7":
        from rompepepe.config import load_env_file
        root_env = load_env_file(Path(__file__).parent.parent / ".env")
        provider = root_env.get("UPSTREAM_PROVIDER", "google").lower()
        if fw_client:
            try:
                fw_cfg = await fw_client.get_config()
                provider = fw_cfg.get("upstream_provider", provider)
            except Exception:
                pass
        
        if provider == "google":
            model = root_env.get("GEMINI_MODEL_ID", "gemini-3.1-flash-lite")
        elif provider == "ollama":
            model = root_env.get("OLLAMA_MODEL", "llama3.1")
        elif provider == "openai":
            model = root_env.get("OPENAI_MODEL", "gpt-4o")
        elif provider == "anthropic":
            model = root_env.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
        
        print(f"[+] Auto-synced from Firewall .env & backend: provider={provider}, model={model}")
    elif choice == "8":
        provider = input(" Enter provider (google/anthropic/openai/ollama): ").strip().lower() or "google"
        model = input(" Enter model ID: ").strip() or "gemini-3.1-flash-lite"
        custom_rpm = input(f" Enter RPM limit [default: {cfg.explorer_rpm_limit}]: ").strip()
        if custom_rpm.isdigit():
            rpm_limit = custom_rpm

    update_env_file({"EXPLORER_PROVIDER": provider, "EXPLORER_MODEL": model, "EXPLORER_RPM_LIMIT": rpm_limit})
    print(f"\n[+] Configuration updated in rompepepe/.env:")
    print(f"    EXPLORER_PROVIDER  = {provider}")
    print(f"    EXPLORER_MODEL     = {model}")
    print(f"    EXPLORER_RPM_LIMIT = {rpm_limit}")


async def run_grid_search(
    fw_client: FirewallClient,
    session_mgr: SessionManager,
    report_gen: ReportGenerator,
    tier: str = "normal",
    session_id: str | None = None,
    non_interactive: bool = False,
):
    engine = GridSearchEngine(fw_client, session_mgr)
    grid = None
    dataset_size = 15

    if not session_id:
        from rompepepe.engines.grid_search import generate_config_grid
        grid = generate_config_grid(tier=tier)
        preflight = await engine.estimate_preflight(grid, dataset_size)

        print(f"\n=======================================================")
        print(f" Strategy A: Systematic Matrix Search (Grid Search, Tier: {tier.upper()})")
        print(f"=======================================================")
        print(f" Grid Cells: {preflight['total_grid_cells']}")
        print(f" Seed Dataset Size: {preflight['dataset_size']} queries")
        print(f" Total Tests: {preflight['total_tests']}")
        print(f" Measured API Latency: {preflight['avg_latency_sec']*1000:.1f} ms")
        print(f" Estimated Duration: {preflight['formatted_eta']}")
        print(f"=======================================================")

        if not non_interactive:
            confirm = input(" Proceed with execution? [Y/n]: ").strip().lower()
            if confirm not in ("", "y", "yes"):
                print("[!] Execution cancelled by user.")
                return

    print("\n[+] Starting Systematic Matrix Search...")
    session_mgr.setup_signal_handler()
    session = await engine.run(
        grid=grid,
        tier=tier,
        session_id=session_id,
        progress_callback=format_progress,
    )
    print("\n")

    report_path = report_gen.generate_report(session, fw_client.base_url)
    print(f"\n[+] Grid Search Complete! Session ID: {session.session_id}")
    print(f"[+] QA Report saved to: {report_path}")


async def run_adaptive_fuzzing(
    fw_client: FirewallClient,
    exp_client: ExplorerClient,
    session_mgr: SessionManager,
    report_gen: ReportGenerator,
    iterations: int = 40,
    tier: str = "normal",
    session_id: str | None = None,
    non_interactive: bool = False,
):
    # Adjust default iteration depth if tier is explicitly specified
    if tier == "light" and iterations == 40:
        iterations = 15
    elif tier == "heavy" and iterations == 40:
        iterations = 250

    engine = AdaptiveFuzzingEngine(fw_client, exp_client, session_mgr)

    if not session_id:
        preflight = await engine.estimate_preflight(iterations)

        print(f"\n=======================================================")
        print(f" Strategy B: Closed-Loop Adaptive Exploration (Tier: {tier.upper()})")
        print(f"=======================================================")
        print(f" Explorer Model: {exp_client.provider} ({exp_client.model})")
        print(f" Planned Iterations: {preflight['iterations']}")
        print(f" Estimated Step Latency: {preflight['total_per_step_sec']:.2f} s")
        print(f" Estimated Duration: {preflight['formatted_eta']}")
        print(f"=======================================================")

        if not non_interactive:
            confirm = input(" Proceed with execution? [Y/n]: ").strip().lower()
            if confirm not in ("", "y", "yes"):
                print("[!] Execution cancelled by user.")
                return

    print("\n[+] Starting Closed-Loop Adaptive Exploration...")
    session_mgr.setup_signal_handler()
    session = await engine.run(
        iterations=iterations,
        session_id=session_id,
        progress_callback=format_progress,
    )
    print("\n")

    report_path = report_gen.generate_report(session, fw_client.base_url)
    print(f"\n[+] Adaptive Fuzzing Complete! Session ID: {session.session_id}")
    print(f"[+] Boundary Transition Points Located: {len(session.boundary_traces)}")
    print(f"[+] QA Report saved to: {report_path}")


def view_reports(vault_path: Path):
    reports_dir = vault_path / "reports"
    reports = sorted(reports_dir.glob("*.md"), reverse=True)
    if not reports:
        print("\n[!] No QA reports found in vault.")
        return

    print(f"\n=======================================================")
    print(f" Past QA Reports ({len(reports)} found)")
    print(f"=======================================================")
    for idx, r in enumerate(reports[:10], start=1):
        print(f" [{idx}] {r.name}")
    print(f"=======================================================")

    choice = input("\nSelect report number to view preview (or Enter to go back): ").strip()
    if choice.isdigit():
        n = int(choice)
        if 1 <= n <= len(reports):
            selected = reports[n - 1]
            print(f"\n--- Previewing {selected.name} ---")
            with open(selected, "r", encoding="utf-8") as f:
                lines = f.readlines()
                print("".join(lines[:35]))
                if len(lines) > 35:
                    print("\n... [truncated] ...")


async def inspect_lancedb_corpus_menu(fw_client: FirewallClient):
    print("\n=======================================================")
    print("   ACTIVE LANCEDB CORPUS PACK INSPECTOR & SYNC")
    print("=======================================================")
    try:
        packs = await fw_client.get_packs()
        if not packs:
            print("[!] No active corpus packs currently loaded in LanceDB via API.")
        else:
            print(f"[+] Located {len(packs)} active corpus pack(s) in LanceDB:")
            for p in packs:
                if isinstance(p, dict):
                    print(f"    - {p.get('filename')} ({p.get('num_vectors', 'N/A')} vectors)")
        
        from rompepepe.test_dataset import build_adapted_corpus
        queries = await build_adapted_corpus(fw_client)
        print(f"\n[+] Domain-adapted dataset constructed ({len(queries)} total queries).")
        print("    Sample queries:")
        for q in queries[:5]:
            print(f"    * '{q}'")
    except Exception as e:
        print(f"[!] Error inspecting LanceDB corpus: {e}")


async def main_async():
    parser = argparse.ArgumentParser(description="rompepepe — Autonomous Stress Testing Engine")
    parser.add_argument("--strategy", choices=["grid", "fuzz"], help="Strategy to run")
    parser.add_argument("--tier", choices=["light", "normal", "heavy"], default="normal", help="Execution intensity tier (light, normal, heavy)")
    parser.add_argument("--resume", type=str, help="Resume session ID")
    parser.add_argument("--resume-latest", action="store_true", help="Resume latest interrupted session")
    parser.add_argument("--iterations", type=int, default=40, help="Iterations for adaptive fuzzing")
    parser.add_argument("--explorer-provider", type=str, help="Override explorer provider (google, anthropic, openai, ollama)")
    parser.add_argument("--explorer-model", type=str, help="Override explorer model ID")
    parser.add_argument("--rpm-limit", type=int, help="Override explorer RPM rate limit (default: 15)")
    parser.add_argument("--select-model", action="store_true", help="Open model selector menu")
    parser.add_argument("--sync-corpus", action="store_true", help="Inspect and adapt dataset to active LanceDB corpus")
    parser.add_argument("--build-pack", "--pack", action="store_true", help="Build agent handoff pack (rompepepe_context.txt)")
    parser.add_argument("--non-interactive", action="store_true", help="Skip preflight confirmation prompt")
    parser.add_argument("--view-reports", action="store_true", help="View past QA reports")

    args = parser.parse_args()

    if args.build_pack:
        from rompepepe.packager import build_rompepepe_pack
        out_path = build_rompepepe_pack()
        print(f"[+] Handoff Pack created at: {out_path}")
        return

    if args.explorer_provider or args.explorer_model or args.rpm_limit:
        updates = {}
        if args.explorer_provider:
            updates["EXPLORER_PROVIDER"] = args.explorer_provider
        if args.explorer_model:
            updates["EXPLORER_MODEL"] = args.explorer_model
        if args.rpm_limit:
            updates["EXPLORER_RPM_LIMIT"] = str(args.rpm_limit)
        update_env_file(updates)

    config = get_config()

    fw_client = FirewallClient(
        base_url=config.firewall_api_base_url,
        api_key=config.firewall_x_api_key,
    )

    if args.select_model:
        await select_model_menu(fw_client)
        return

    if args.sync_corpus:
        await inspect_lancedb_corpus_menu(fw_client)
        return

    exp_client = ExplorerClient(
        provider=config.explorer_provider,
        api_key=config.explorer_api_key,
        model=config.explorer_model,
        rpm_limit=config.explorer_rpm_limit,
    )
    session_mgr = SessionManager(config.vault_storage_path)
    report_gen = ReportGenerator(config.vault_storage_path / "reports")

    if args.view_reports:
        view_reports(config.vault_storage_path)
        return

    session_id_to_resume = args.resume
    if args.resume_latest:
        latest = session_mgr.get_latest_interrupted_session()
        if latest:
            session_id_to_resume = latest.session_id
            print(f"[+] Found interrupted session to resume: {session_id_to_resume}")
        else:
            print("[!] No interrupted session found to resume.")
            return

    if session_id_to_resume:
        session = session_mgr.load_session(session_id_to_resume)
        print(f"[+] Resuming session `{session_id_to_resume}` (Strategy: {session.strategy})")
        if session.strategy == "grid_search":
            await run_grid_search(fw_client, session_mgr, report_gen, tier=args.tier, session_id=session_id_to_resume, non_interactive=args.non_interactive)
        else:
            await run_adaptive_fuzzing(fw_client, exp_client, session_mgr, report_gen, iterations=session.total_steps, tier=args.tier, session_id=session_id_to_resume, non_interactive=args.non_interactive)
        return

    if args.strategy == "grid":
        await run_grid_search(fw_client, session_mgr, report_gen, tier=args.tier, non_interactive=args.non_interactive)
    elif args.strategy == "fuzz":
        await run_adaptive_fuzzing(fw_client, exp_client, session_mgr, report_gen, iterations=args.iterations, tier=args.tier, non_interactive=args.non_interactive)
    else:
        print("\n==============================================")
        print("  Rompé Pepe! Rompé nomá!!! — Autonomous Stress Engine CLI")
        print("==============================================")
        print(" [1] Strategy A: Systematic Matrix Search (Grid Search)")
        print(" [2] Strategy B: Closed-Loop Adaptive Exploration (Fuzzing)")
        print(" [3] Select / Configure Explorer Model")
        print(" [4] Inspect Active LanceDB Corpus & Adapted Queries")
        print(" [5] Build Agent Handoff Pack (rompepepe_context.txt)")
        print(" [6] View Past QA Reports")
        print(" [7] Resume Interrupted Session")
        print(" [8] Quit")
        print("==============================================")
        choice = input(" Select option [1-8]: ").strip()
        
        if choice == "1":
            await run_grid_search(fw_client, session_mgr, report_gen)
        elif choice == "2":
            await run_adaptive_fuzzing(fw_client, exp_client, session_mgr, report_gen)
        elif choice == "3":
            await select_model_menu(fw_client)
        elif choice == "4":
            await inspect_lancedb_corpus_menu(fw_client)
        elif choice == "5":
            from rompepepe.packager import build_rompepepe_pack
            out_p = build_rompepepe_pack()
            print(f"[+] Agent Handoff Pack created: {out_p}")
        elif choice == "6":
            view_reports(config.vault_storage_path)
        elif choice == "7":
            latest = session_mgr.get_latest_interrupted_session()
            if latest:
                print(f"[+] Found interrupted session: {latest.session_id}")
                await run_adaptive_fuzzing(fw_client, exp_client, session_mgr, report_gen, session_id=latest.session_id) if latest.strategy == "adaptive_fuzzing" else await run_grid_search(fw_client, session_mgr, report_gen, session_id=latest.session_id)
            else:
                print("[!] No interrupted session found.")


def main():
    try:
        asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n[!] Exited by user.")


if __name__ == "__main__":
    main()
