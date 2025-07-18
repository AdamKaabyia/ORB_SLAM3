#!/usr/bin/env python3
"""
ORB-SLAM3 Unified CLI/UI
========================

Master command interface that integrates:
- Dataset acquisition (EuRoC scraping)
- Cross-platform container building (Docker/Podman)
- Comprehensive benchmarking and testing
- Interactive results visualization

Usage: python3 orbslam3_cli.py [command] [options]
"""

import os
import sys
import subprocess
import platform
import argparse
import json
from pathlib import Path

class ORBSlam3CLI:
    def __init__(self):
        self.platform = platform.system()
        self.workspace = Path.cwd()

    def print_banner(self):
        """Display the application banner"""
        print("="*60)
        print("ORB-SLAM3 Unified Development CLI")
        print("Complete pipeline: Dataset -> Build -> Test -> Analyze")
        print("="*60)
        print()

    def print_table(self, headers, rows, title=None):
        """Simple table printing"""
        if title:
            print(f"\n{title}")
            print("-" * len(title))

        # Calculate column widths
        all_rows = [headers] + rows
        col_widths = [max(len(str(row[i])) for row in all_rows) for i in range(len(headers))]

        # Print header
        header_row = " | ".join(str(headers[i]).ljust(col_widths[i]) for i in range(len(headers)))
        print(header_row)
        print("-" * len(header_row))

        # Print rows
        for row in rows:
            print(" | ".join(str(row[i]).ljust(col_widths[i]) for i in range(len(row))))
        print()

    def check_dependencies(self):
        """Check if required scripts and dependencies exist"""
        required_files = [
            'euroc_dataset_scraper.py',
            'orbslam3_runner.py',
            'orbslam3_benchmark_ui.py',
            'results_dashboard.py',
            'cross-platform-dev.py'
        ]

        missing = []
        for file in required_files:
            if not (self.workspace / file).exists():
                missing.append(file)

        if missing:
            print(f"ERROR: Missing required files: {', '.join(missing)}")
            return False

        return True

    def detect_container_runtime(self):
        """Detect available container runtime (Podman/Docker)"""
        runtimes = ['podman', 'docker']

        for runtime in runtimes:
            try:
                result = subprocess.run([runtime, '--version'],
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    return runtime
            except FileNotFoundError:
                continue

        return None

    def run_command(self, cmd, description=None, show_output=True):
        """Execute a command with optional progress indication"""
        if description:
            print(f"[INFO] {description}...")

        if show_output:
            result = subprocess.run(cmd, shell=True)
        else:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)

        return result

    def get_user_choice(self, prompt, choices, default=None):
        """Get user input with validation"""
        choice_str = "/".join(choices)
        if default:
            prompt_text = f"{prompt} [{choice_str}] (default: {default}): "
        else:
            prompt_text = f"{prompt} [{choice_str}]: "

        while True:
            choice = input(prompt_text).strip()
            if not choice and default:
                return default
            if choice in choices:
                return choice
            print(f"Invalid choice. Please select from: {choice_str}")

    def confirm(self, prompt):
        """Simple yes/no confirmation"""
        response = input(f"{prompt} [y/N]: ").strip().lower()
        return response in ['y', 'yes']

    def scrape_datasets(self):
        """Download EuRoC datasets"""
        print("\n[DATASET ACQUISITION]")
        print("Available EuRoC sequences:")

        datasets = [
            ("1", "machine_hall", "MH_01_easy through MH_05_difficult"),
            ("2", "vicon_room1", "V1_01_easy through V1_03_difficult"),
            ("3", "vicon_room2", "V2_01_easy through V2_03_medium"),
            ("all", "all datasets", "Download all sequences")
        ]

        self.print_table(["Option", "Dataset", "Description"],
                        [(opt, name, desc) for opt, name, desc in datasets])

        choice = self.get_user_choice("Select datasets", ["1", "2", "3", "all"], "all")

        if choice == "all":
            # Download all datasets by calling scraper multiple times
            datasets_to_download = ["machine_hall", "vicon_room1", "vicon_room2"]
            success = True
            for dataset in datasets_to_download:
                print(f"Downloading {dataset} sequences...")
                result = self.run_command(f"python3 euroc_dataset_scraper.py --location {dataset}",
                                        f"Downloading {dataset}")
                if result.returncode != 0:
                    success = False
            if success:
                print("[SUCCESS] All dataset acquisitions completed!")
            else:
                print("[ERROR] Some dataset acquisitions failed!")
        else:
            dataset_map = {"1": "machine_hall", "2": "vicon_room1", "3": "vicon_room2"}
            cmd = f"python3 euroc_dataset_scraper.py --location {dataset_map[choice]}"

            result = self.run_command(cmd, "Downloading datasets")
            if result.returncode == 0:
                print("[SUCCESS] Dataset acquisition completed!")
            else:
                print("[ERROR] Dataset acquisition failed!")

    def build_containers(self):
        """Build Docker/Podman containers"""
        print("\n[CONTAINER BUILDING]")

        runtime = self.detect_container_runtime()
        if not runtime:
            print("[ERROR] No container runtime found. Please install Docker or Podman.")
            return False

        print(f"Using container runtime: {runtime}")

        build_options = [
            ("1", "baseline", "Build upstream baseline ORB-SLAM3"),
            ("2", "optimized", "Build with our performance optimizations"),
            ("3", "both", "Build both baseline and optimized versions")
        ]

        self.print_table(["Option", "Type", "Description"],
                        [(opt, btype, desc) for opt, btype, desc in build_options])

        choice = self.get_user_choice("Select build option", ["1", "2", "3"], "3")

        option_map = {"1": "baseline", "2": "optimized", "3": "both"}
        build_type = option_map[choice]

        build_success = True

        if build_type in ["baseline", "both"]:
            result = self.run_command("python3 cross-platform-dev.py build-baseline",
                                    "Building baseline container")
            if result.returncode != 0:
                print("[ERROR] Baseline container build failed!")
                build_success = False

        if build_type in ["optimized", "both"]:
            result = self.run_command("python3 cross-platform-dev.py build-optimized",
                                    "Building optimized container")
            if result.returncode != 0:
                print("[ERROR] Optimized container build failed!")
                build_success = False

        if build_success:
            print("[SUCCESS] Container building completed!")
        else:
            print("[FAILED] One or more container builds failed!")

        return build_success

    def run_benchmarks(self):
        """Execute comprehensive benchmarking"""
        print("\n[BENCHMARKING & TESTING]")

        benchmark_options = [
            ("1", "quick", "Quick benchmark (5 runs each)"),
            ("2", "standard", "Standard benchmark (25 runs each)"),
            ("3", "comprehensive", "Comprehensive benchmark (50 runs each)"),
            ("4", "interactive", "Interactive benchmark UI")
        ]

        self.print_table(["Option", "Type", "Description"],
                        [(opt, btype, desc) for opt, btype, desc in benchmark_options])

        choice = self.get_user_choice("Select benchmark option", ["1", "2", "3", "4"], "4")

        if choice == "4":
            # Interactive UI
            print("Launching interactive benchmark UI...")
            self.run_command("python3 orbslam3_benchmark_ui.py")
        else:
            # Automated benchmarking
            run_counts = {"1": 5, "2": 25, "3": 50}
            runs = run_counts[choice]

            cmd = f"python3 orbslam3_runner.py --runs {runs} --output-format json --export-plots"
            self.run_command(cmd, f"Running {runs}-iteration benchmark")

        print("[SUCCESS] Benchmarking completed!")

    def view_results(self):
        """Launch results visualization dashboard"""
        print("\n[RESULTS ANALYSIS]")

        # Check for existing results
        result_files = list(self.workspace.glob("*_results_*.json"))

        if not result_files:
            print("[WARNING] No benchmark results found. Run benchmarks first.")
            return

        print(f"Found {len(result_files)} result files")

        # Launch dashboard
        print("Launching results dashboard...")
        self.run_command("python3 results_dashboard.py")

    def development_environment(self):
        """Launch development container environment"""
        print("\n[DEVELOPMENT ENVIRONMENT]")

        runtime = self.detect_container_runtime()
        if not runtime:
            print("[ERROR] No container runtime found.")
            return

        env_options = [
            ("1", "dev", "Interactive development environment"),
            ("2", "build", "Build and compile ORB-SLAM3"),
            ("3", "test", "Run basic functionality tests")
        ]

        self.print_table(["Option", "Type", "Description"],
                        [(opt, etype, desc) for opt, etype, desc in env_options])

        choice = self.get_user_choice("Select environment option", ["1", "2", "3"], "1")

        option_map = {"1": "dev", "2": "build", "3": "test"}
        env_type = option_map[choice]

        if self.platform == "Windows":
            cmd = f"powershell .\\windows-dev.ps1 {env_type}"
        else:
            cmd = f"./container-dev.sh {env_type}"

        print(f"Launching {env_type} environment...")
        self.run_command(cmd)

    def show_status(self):
        """Display current system status and setup"""
        print("\n[SYSTEM STATUS]")

        status_data = []

        # Platform info
        status_data.append(["Platform", f"{self.platform} {platform.machine()}", platform.platform()])

        # Container runtime
        runtime = self.detect_container_runtime()
        if runtime:
            status_data.append(["Container Runtime", runtime, "Available"])
        else:
            status_data.append(["Container Runtime", "None", "Install Docker or Podman"])

        # Check for datasets - improved detection
        dataset_base = self.workspace / "datasets"
        euroc_dir = dataset_base / "EuRoC"

        total_sequences = 0
        dataset_info = "None"

        if euroc_dir.exists():
            # Count sequences across all locations
            for location_dir in euroc_dir.iterdir():
                if location_dir.is_dir():
                    # Count sequence directories (not zip files)
                    sequences = [d for d in location_dir.iterdir()
                               if d.is_dir() and (d / "mav0").exists()]
                    total_sequences += len(sequences)

            if total_sequences > 0:
                dataset_info = f"{total_sequences} sequences"
                status_data.append(["Datasets", dataset_info, str(euroc_dir)])
            else:
                status_data.append(["Datasets", "Downloaded but not extracted", "Run extraction"])
        else:
            status_data.append(["Datasets", "None", "Run 'scrape' to download"])

        # Check for results
        result_files = list(self.workspace.glob("*_results_*.json"))
        if result_files:
            status_data.append(["Results", f"{len(result_files)} files", "Available for analysis"])
        else:
            status_data.append(["Results", "None", "Run benchmarks to generate"])

        self.print_table(["Component", "Status", "Details"], status_data)

    def interactive_mode(self):
        """Interactive CLI mode with menu"""
        while True:
            self.print_banner()

            menu_options = [
                ("status", "Show system status"),
                ("scrape", "Download EuRoC datasets"),
                ("build", "Build containers (Docker/Podman)"),
                ("benchmark", "Run benchmarks and tests"),
                ("results", "View results dashboard"),
                ("dev", "Launch development environment"),
                ("quit", "Exit")
            ]

            self.print_table(["Command", "Description"], menu_options, "Available Commands")

            choice = self.get_user_choice("Select command",
                                        [opt[0] for opt in menu_options],
                                        "status")

            if choice == "quit":
                break
            elif choice == "status":
                self.show_status()
            elif choice == "scrape":
                self.scrape_datasets()
            elif choice == "build":
                self.build_containers()
            elif choice == "benchmark":
                self.run_benchmarks()
            elif choice == "results":
                self.view_results()
            elif choice == "dev":
                self.development_environment()

            if choice != "status":
                input("\nPress Enter to continue...")

def main():
    parser = argparse.ArgumentParser(
        description="ORB-SLAM3 Unified CLI - Complete development pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 orbslam3_cli.py                    # Interactive mode
  python3 orbslam3_cli.py status             # Show system status
  python3 orbslam3_cli.py scrape             # Download datasets
  python3 orbslam3_cli.py build              # Build containers
  python3 orbslam3_cli.py benchmark          # Run benchmarks
  python3 orbslam3_cli.py results            # View results
  python3 orbslam3_cli.py dev                # Development environment
        """
    )

    parser.add_argument('command', nargs='?',
                       choices=['status', 'scrape', 'build', 'benchmark', 'results', 'dev'],
                       help='Command to execute (default: interactive mode)')

    args = parser.parse_args()

    cli = ORBSlam3CLI()

    if not cli.check_dependencies():
        print("[ERROR] Missing required dependencies. Please ensure all scripts are present.")
        sys.exit(1)

    if args.command:
        # Direct command mode
        cli.print_banner()

        if args.command == 'status':
            cli.show_status()
        elif args.command == 'scrape':
            cli.scrape_datasets()
        elif args.command == 'build':
            cli.build_containers()
        elif args.command == 'benchmark':
            cli.run_benchmarks()
        elif args.command == 'results':
            cli.view_results()
        elif args.command == 'dev':
            cli.development_environment()
    else:
        # Interactive mode
        cli.interactive_mode()

if __name__ == "__main__":
    main()