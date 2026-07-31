"""Main CLI entry point for rompepepe autonomous stress testing tool.
"""
import argparse
import asyncio
import logging
from pathlib import Path
import sys

from rompepepe.client.explorer_client import ExplorerClient
from rompepepe.client.firewall_client import FirewallClient
from rompepepe.config import get_config
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
    pct = (curr / total * 100.0) if total > 0 else 0.0

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


async def run_grid_search(
    fw_client: FirewallClient,
    session_mgr: SessionManager,
    report_gen: ReportGenerator,
    session_id: str | None = None,
    non_interactive: bool = False,
):
    engine = GridSearchEngine(fw_client, session_mgr)
    grid = None  # default grid
    dataset_size = 15

    if not session_id:
        from rompepepe.engines.grid_search import generate_config_grid
        grid = generate_config_grid()
        preflight = await engine.estimate_preflight(grid, dataset_size)

        print(f"\n=======================================================")
        print(f" Strategy A: Systematic Matrix Permutation (Grid Search)")
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
    session_id: str | None = None,
    non_interactive: bool = False,
):
    engine = AdaptiveFuzzingEngine(fw_client, exp_client, session_mgr)

    if not session_id:
        preflight = await engine.estimate_preflight(iterations)

        print(f"\n=======================================================")
        print(f" Strategy B: Closed-Loop Adaptive Exploration (Fuzzing)")
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


async def main_async():
    parser = argparse.ArgumentParser(description="rompepepe — Autonomous Stress Testing Engine")
    parser.add_argument("--strategy", choices=["grid", "fuzz"], help="Strategy to run")
    parser.add_argument("--resume", type=str, help="Resume session ID")
    parser.add_argument("--resume-latest", action="store_true", help="Resume latest interrupted session")
    parser.add_argument("--iterations", type=int, default=40, help="Iterations for adaptive fuzzing")
    parser.add_argument("--non-interactive", action="store_true", help="Skip preflight confirmation prompt")
    parser.add_argument("--view-reports", action="store_true", help="View past QA reports")

    args = parser.parse_args()
    config = get_config()

    fw_client = FirewallClient(
        base_url=config.firewall_api_base_url,
        api_key=config.firewall_x_api_key,
    )
    exp_client = ExplorerClient(
        provider=config.explorer_provider,
        api_key=config.explorer_api_key,
        model=config.explorer_model,
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
            await run_grid_search(fw_client, session_mgr, report_gen, session_id=session_id_to_resume, non_interactive=args.non_interactive)
        else:
            await run_adaptive_fuzzing(fw_client, exp_client, session_mgr, report_gen, iterations=session.total_steps, session_id=session_id_to_resume, non_interactive=args.non_interactive)
        return

    if args.strategy == "grid":
        await run_grid_search(fw_client, session_mgr, report_gen, non_interactive=args.non_interactive)
    elif args.strategy == "fuzz":
        await run_adaptive_fuzzing(fw_client, exp_client, session_mgr, report_gen, iterations=args.iterations, non_interactive=args.non_interactive)
    else:
        # Interactive CLI fallback if launched directly without args
        print("\n==============================================")
        print("  ROMP E PE PE — Autonomous Stress Engine CLI")
        print("==============================================")
        print(" [1] Strategy A: Systematic Matrix Search (Grid Search)")
        print(" [2] Strategy B: Closed-Loop Adaptive Exploration (Fuzzing)")
        print(" [3] View Past QA Reports")
        print(" [4] Resume Interrupted Session")
        print(" [5] Quit")
        print("==============================================")
        choice = input(" Select option [1-5]: ").strip()
        
        if choice == "1":
            await run_grid_search(fw_client, session_mgr, report_gen)
        elif choice == "2":
            await run_adaptive_fuzzing(fw_client, exp_client, session_mgr, report_gen)
        elif choice == "3":
            view_reports(config.vault_storage_path)
        elif choice == "4":
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
