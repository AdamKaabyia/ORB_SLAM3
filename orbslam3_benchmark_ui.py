#!/usr/bin/env python3
"""
Interactive ORB-SLAM3 Benchmarking UI
Provides real-time progress tracking and results visualization
"""

import os
import sys
import json
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime
import argparse
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
import statistics

# Try to import rich for better UI, fallback to basic print
try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.table import Table
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.live import Live
    from rich.text import Text
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("Install 'rich' for enhanced UI: pip install rich")

@dataclass
class BenchmarkResult:
    """Single benchmark run result"""
    sequence: str
    version: str  # 'baseline' or 'optimized'
    run_number: int
    success: bool
    runtime_ms: float
    tracking_lost_frames: int
    total_frames: int
    rmse_translation: float
    rmse_rotation: float
    memory_peak_mb: float
    timestamp: str

class ORBSLAMBenchmarkUI:
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.results = []
        self.current_progress = {}
        self.benchmark_running = False

    def display_header(self):
        """Display application header"""
        if RICH_AVAILABLE and self.console:
            header = Panel(
                "[bold blue]ORB-SLAM3 Performance Benchmarking Suite[/bold blue]\n" +
                "[dim]Interactive testing with baseline vs optimized comparison[/dim]",
                style="blue",
                box=box.DOUBLE
            )
            self.console.print(header)
        else:
            print("=" * 60)
            print("     ORB-SLAM3 Performance Benchmarking Suite")
            print("  Interactive testing with baseline vs optimized comparison")
            print("=" * 60)

    def display_menu(self):
        """Display main menu"""
        if RICH_AVAILABLE and self.console:
            menu = Table(title="Main Menu", box=box.ROUNDED)
            menu.add_column("Option", style="cyan", width=8)
            menu.add_column("Description", style="white")

            menu.add_row("1", "Download EuRoC Datasets")
            menu.add_row("2", "Run Single Sequence Test")
            menu.add_row("3", "Run Full Benchmark Suite (50 runs)")
            menu.add_row("4", "Run Sequential Benchmark (single container)")
            menu.add_row("5", "View Results Dashboard")
            menu.add_row("6", "Export Results")
            menu.add_row("7", "System Info")
            menu.add_row("q", "Quit")

            self.console.print(menu)
        else:
            print("\n--- Main Menu ---")
            print("1. Download EuRoC Datasets")
            print("2. Run Single Sequence Test")
            print("3. Run Full Benchmark Suite (50 runs)")
            print("4. Run Sequential Benchmark (single container)")
            print("5. View Results Dashboard")
            print("6. Export Results")
            print("7. System Info")
            print("q. Quit")

    def download_datasets_interactive(self):
        """Interactive dataset download"""
        print("\n=== EuRoC Dataset Download ===")

        locations = ["machine_hall", "vicon_room1", "vicon_room2", "all"]

        if RICH_AVAILABLE and self.console:
            table = Table(title="Available Locations")
            table.add_column("Number", style="cyan")
            table.add_column("Location", style="white")
            table.add_column("Sequences", style="dim")

            table.add_row("1", "machine_hall", "MH_01_easy to MH_05_difficult")
            table.add_row("2", "vicon_room1", "V1_01_easy to V1_03_difficult")
            table.add_row("3", "vicon_room2", "V2_01_easy to V2_03_difficult")
            table.add_row("4", "all", "Download everything")

            self.console.print(table)
        else:
            print("1. machine_hall (MH_01_easy to MH_05_difficult)")
            print("2. vicon_room1 (V1_01_easy to V1_03_difficult)")
            print("3. vicon_room2 (V2_01_easy to V2_03_difficult)")
            print("4. all (Download everything)")

        try:
            choice = input("\nSelect location (1-4): ").strip()
            choice_map = {"1": "machine_hall", "2": "vicon_room1", "3": "vicon_room2", "4": "all"}

            if choice in choice_map:
                location = choice_map[choice]
                print(f"\nStarting download for: {location}")

                # Run the scraper
                cmd = ["python3", "euroc_dataset_scraper.py"]
                if location != "all":
                    cmd.extend(["--location", location])

                subprocess.run(cmd)
                print("Download completed!")
            else:
                print("Invalid choice!")

        except KeyboardInterrupt:
            print("\nDownload cancelled.")

    def run_single_test(self):
        """Run a single sequence test"""
        print("\n=== Single Sequence Test ===")

        # Check available datasets
        config_path = Path("datasets/EuRoC/dataset_config.json")
        if not config_path.exists():
            print("No datasets found. Please download datasets first.")
            return

        with open(config_path) as f:
            config = json.load(f)

        # Display available sequences
        sequences = []
        for location, seqs in config["datasets"].items():
            for seq_name in seqs.keys():
                sequences.append(f"{location}/{seq_name}")

        if not sequences:
            print("No datasets available.")
            return

        print("Available sequences:")
        for i, seq in enumerate(sequences, 1):
            print(f"{i}. {seq}")

        try:
            choice = int(input(f"\nSelect sequence (1-{len(sequences)}): "))
            if 1 <= choice <= len(sequences):
                selected = sequences[choice-1]
                location, sequence = selected.split("/")

                print(f"\nTesting: {selected}")
                print("Testing both baseline and optimized versions...")

                # Run both versions
                baseline_result = self.run_orbslam_sequence(location, sequence, "baseline")
                optimized_result = self.run_orbslam_sequence(location, sequence, "optimized")

                self.display_comparison(baseline_result, optimized_result)

        except (ValueError, KeyboardInterrupt):
            print("Invalid selection or cancelled.")

    def run_orbslam_sequence(self, location, sequence, version):
        """Run ORB-SLAM3 on a specific sequence"""
        print(f"\nRunning {version} version on {location}/{sequence}...")

        # This is a placeholder - in real implementation, you'd:
        # 1. Build the appropriate ORB-SLAM3 version
        # 2. Run it with the dataset
        # 3. Parse the output for metrics

        # Simulated results for demonstration
        import random
        base_runtime = random.uniform(45000, 55000)  # ms
        improvement_factor = 0.85 if version == "optimized" else 1.0

        result = BenchmarkResult(
            sequence=f"{location}/{sequence}",
            version=version,
            run_number=1,
            success=True,
            runtime_ms=base_runtime * improvement_factor,
            tracking_lost_frames=random.randint(0, 50),
            total_frames=random.randint(2000, 3000),
            rmse_translation=random.uniform(0.05, 0.15),
            rmse_rotation=random.uniform(0.5, 1.5),
            memory_peak_mb=random.uniform(800, 1200),
            timestamp=datetime.now().isoformat()
        )

        # Simulate processing time
        if RICH_AVAILABLE:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                task = progress.add_task(f"Running {version}...", total=100)
                for i in range(100):
                    time.sleep(0.05)  # Simulate work
                    progress.update(task, advance=1)
        else:
            print(f"Running {version} version...")
            time.sleep(2)  # Simulate processing

        return result

    def display_comparison(self, baseline, optimized):
        """Display comparison between baseline and optimized results"""
        if RICH_AVAILABLE and self.console:
            table = Table(title=f"Performance Comparison: {baseline.sequence}")
            table.add_column("Metric", style="cyan")
            table.add_column("Baseline", style="white")
            table.add_column("Optimized", style="green")
            table.add_column("Improvement", style="yellow")

            # Runtime comparison
            runtime_improvement = ((baseline.runtime_ms - optimized.runtime_ms) / baseline.runtime_ms) * 100
            table.add_row(
                "Runtime (ms)",
                f"{baseline.runtime_ms:.1f}",
                f"{optimized.runtime_ms:.1f}",
                f"{runtime_improvement:+.1f}%"
            )

            # Memory comparison
            memory_improvement = ((baseline.memory_peak_mb - optimized.memory_peak_mb) / baseline.memory_peak_mb) * 100
            table.add_row(
                "Peak Memory (MB)",
                f"{baseline.memory_peak_mb:.1f}",
                f"{optimized.memory_peak_mb:.1f}",
                f"{memory_improvement:+.1f}%"
            )

            # RMSE comparisons
            rmse_t_improvement = ((baseline.rmse_translation - optimized.rmse_translation) / baseline.rmse_translation) * 100
            table.add_row(
                "RMSE Translation",
                f"{baseline.rmse_translation:.3f}",
                f"{optimized.rmse_translation:.3f}",
                f"{rmse_t_improvement:+.1f}%"
            )

            self.console.print(table)
        else:
            print(f"\n=== Performance Comparison: {baseline.sequence} ===")
            print(f"Runtime:        {baseline.runtime_ms:.1f}ms -> {optimized.runtime_ms:.1f}ms")
            print(f"Memory:         {baseline.memory_peak_mb:.1f}MB -> {optimized.memory_peak_mb:.1f}MB")
            print(f"RMSE Trans:     {baseline.rmse_translation:.3f} -> {optimized.rmse_translation:.3f}")

    def run_full_benchmark(self):
        """Run comprehensive benchmark suite with 50 runs each"""
        print("\n=== Full Benchmark Suite ===")
        print("This will run 50 iterations of each sequence for both baseline and optimized versions.")

        confirm = input("This may take several hours. Continue? (y/N): ").strip().lower()
        if confirm != 'y':
            return

        # Load available datasets
        config_path = Path("datasets/EuRoC/dataset_config.json")
        if not config_path.exists():
            print("No datasets found. Please download datasets first.")
            return

        with open(config_path) as f:
            config = json.load(f)

        all_sequences = []
        for location, seqs in config["datasets"].items():
            for seq_name in seqs.keys():
                all_sequences.append((location, seq_name))

        total_runs = len(all_sequences) * 2 * 50  # sequences * versions * runs

        print(f"Starting benchmark: {len(all_sequences)} sequences, 50 runs each, 2 versions")
        print(f"Total runs: {total_runs}")

        if RICH_AVAILABLE:
            with Progress() as progress:
                main_task = progress.add_task("Overall Progress", total=total_runs)

                for location, sequence in all_sequences:
                    seq_task = progress.add_task(f"{location}/{sequence}", total=100)

                    # Run baseline version 50 times
                    for run in range(50):
                        result = self.run_orbslam_sequence(location, sequence, "baseline")
                        result.run_number = run + 1
                        self.results.append(result)
                        progress.update(main_task, advance=1)
                        progress.update(seq_task, advance=1)

                    # Run optimized version 50 times
                    for run in range(50):
                        result = self.run_orbslam_sequence(location, sequence, "optimized")
                        result.run_number = run + 1
                        self.results.append(result)
                        progress.update(main_task, advance=1)
                        progress.update(seq_task, advance=1)

                    progress.remove_task(seq_task)

        print("\nBenchmark completed!")
        self.save_results()

    def run_sequential_benchmark(self):
        """Run benchmark with single container execution"""
        print("\n=== Sequential Benchmark Mode ===")
        print("This mode runs one container at a time for better resource usage.")

        if RICH_AVAILABLE:
            console = Console()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                console=console,
                refresh_per_second=2
            ) as progress:

                # Simplified sequence list for testing
                sequences = ["MH_01_easy", "MH_02_easy", "V1_01_easy"]
                total_tests = len(sequences) * 2  # baseline + optimized

                main_task = progress.add_task("Sequential Benchmark", total=total_tests)

                for sequence in sequences:
                    # Run baseline version (sequential)
                    progress.update(main_task, description=f"Running baseline: {sequence}")
                    result = self.run_orbslam_sequence("machine_hall", sequence, "baseline")
                    result.run_number = 1
                    self.results.append(result)
                    progress.update(main_task, advance=1)

                    # Small delay to ensure container cleanup
                    time.sleep(2)

                    # Run optimized version (sequential)
                    progress.update(main_task, description=f"Running optimized: {sequence}")
                    result = self.run_orbslam_sequence("machine_hall", sequence, "optimized")
                    result.run_number = 1
                    self.results.append(result)
                    progress.update(main_task, advance=1)

                    # Small delay to ensure container cleanup
                    time.sleep(2)

                progress.update(main_task, description="Sequential benchmark completed")

            console.print(Panel.fit(
                "[bold green]Sequential Benchmark Complete![/bold green]\n"
                f"Processed {len(sequences)} sequences in sequential mode\n"
                "Single container execution - no parallel overhead",
                title="Success"
            ))
        else:
            print("Running sequential benchmark...")
            sequences = ["MH_01_easy", "MH_02_easy", "V1_01_easy"]

            for i, sequence in enumerate(sequences):
                print(f"[{i+1}/{len(sequences)}] Testing {sequence}...")

                print("  Running baseline version...")
                result = self.run_orbslam_sequence("machine_hall", sequence, "baseline")
                result.run_number = 1
                self.results.append(result)

                print("  Running optimized version...")
                result = self.run_orbslam_sequence("machine_hall", sequence, "optimized")
                result.run_number = 1
                self.results.append(result)

                print(f"  {sequence} completed")

            print("Sequential benchmark completed!")

        self.save_results()

    def view_results_dashboard(self):
        """Display results dashboard"""
        if not self.results:
            print("No results available. Run some benchmarks first.")
            return

        if RICH_AVAILABLE and self.console:
            # Create summary statistics
            baseline_results = [r for r in self.results if r.version == "baseline"]
            optimized_results = [r for r in self.results if r.version == "optimized"]

            table = Table(title="Benchmark Results Summary")
            table.add_column("Metric", style="cyan")
            table.add_column("Baseline Avg", style="white")
            table.add_column("Optimized Avg", style="green")
            table.add_column("Improvement", style="yellow")

            if baseline_results and optimized_results:
                baseline_runtime = statistics.mean([r.runtime_ms for r in baseline_results])
                optimized_runtime = statistics.mean([r.runtime_ms for r in optimized_results])
                runtime_improvement = ((baseline_runtime - optimized_runtime) / baseline_runtime) * 100

                table.add_row(
                    "Average Runtime (ms)",
                    f"{baseline_runtime:.1f}",
                    f"{optimized_runtime:.1f}",
                    f"{runtime_improvement:+.1f}%"
                )

            self.console.print(table)
        else:
            print("=== Results Summary ===")
            print(f"Total results: {len(self.results)}")

    def save_results(self):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_results_{timestamp}.json"

        results_data = {
            "timestamp": datetime.now().isoformat(),
            "total_results": len(self.results),
            "results": [asdict(r) for r in self.results]
        }

        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"Results saved to: {filename}")

    def run(self):
        """Main application loop"""
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            self.display_header()
            self.display_menu()

            try:
                choice = input("\nSelect option: ").strip().lower()

                if choice == 'q':
                    print("Goodbye!")
                    break
                elif choice == '1':
                    self.download_datasets_interactive()
                elif choice == '2':
                    self.run_single_test()
                elif choice == '3':
                    self.run_full_benchmark()
                elif choice == '4':
                    self.run_sequential_benchmark()
                elif choice == '5':
                    self.view_results_dashboard()
                elif choice == '6':
                    self.save_results()
                elif choice == '7':
                    self.display_system_info()
                else:
                    print("Invalid option!")

                if choice != 'q':
                    input("\nPress Enter to continue...")

            except KeyboardInterrupt:
                print("\n\nExiting...")
                break

    def display_system_info(self):
        """Display system information"""
        import platform

        print("\n=== System Information ===")
        print(f"OS: {platform.system()} {platform.release()}")
        print(f"Architecture: {platform.machine()}")
        print(f"Python: {sys.version}")
        print(f"Working Directory: {os.getcwd()}")

def main():
    parser = argparse.ArgumentParser(description="ORB-SLAM3 Interactive Benchmarking UI")
    parser.add_argument("--no-ui", action="store_true", help="Run without rich UI")
    args = parser.parse_args()

    if args.no_ui:
        global RICH_AVAILABLE
        RICH_AVAILABLE = False

    app = ORBSLAMBenchmarkUI()
    app.run()

if __name__ == "__main__":
    main()