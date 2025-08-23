#!/usr/bin/env python3
"""
ORB-SLAM3 Results Dashboard
Interactive visualization of benchmark results comparing baseline vs optimized performance
"""

import json
import sys
import statistics
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import argparse
from datetime import datetime

# Try to import rich for enhanced UI
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.layout import Layout
    from rich.live import Live
    from rich.text import Text
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.columns import Columns
    from rich import box
    from rich.align import Align
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Try to import matplotlib for plotting
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    from datetime import datetime
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

@dataclass
class ComparisonStats:
    """Statistical comparison between baseline and optimized"""
    metric_name: str
    baseline_mean: float
    baseline_std: float
    optimized_mean: float
    optimized_std: float
    improvement_percent: float
    statistical_significance: float
    sample_size: int

class ResultsDashboard:
    """Interactive dashboard for benchmark results"""

    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.results_data = None
        self.baseline_results = []
        self.optimized_results = []

    def load_results(self, results_file: Path) -> bool:
        """Load benchmark results from JSON file"""
        try:
            with open(results_file) as f:
                self.results_data = json.load(f)

            # Separate baseline and optimized results
            self.baseline_results = [
                r for r in self.results_data["results"]
                if r["version"] == "baseline" and r["success"]
            ]
            self.optimized_results = [
                r for r in self.results_data["results"]
                if r["version"] == "optimized" and r["success"]
            ]

            return True

        except Exception as e:
            print(f"Error loading results: {e}")
            return False

    def calculate_comparison_stats(self, metric_path: str) -> ComparisonStats:
        """Calculate statistical comparison for a metric"""
        def get_metric_value(result, path):
            """Extract nested metric value using dot notation"""
            value = result
            for key in path.split('.'):
                value = value[key]
            return float(value)

        baseline_values = [get_metric_value(r, metric_path) for r in self.baseline_results]
        optimized_values = [get_metric_value(r, metric_path) for r in self.optimized_results]

        baseline_mean = statistics.mean(baseline_values)
        baseline_std = statistics.stdev(baseline_values) if len(baseline_values) > 1 else 0
        optimized_mean = statistics.mean(optimized_values)
        optimized_std = statistics.stdev(optimized_values) if len(optimized_values) > 1 else 0

        # Calculate improvement percentage
        if baseline_mean != 0:
            improvement = ((baseline_mean - optimized_mean) / baseline_mean) * 100
        else:
            improvement = 0

        # Simple t-test significance (would use scipy.stats in real implementation)
        significance = 0.95  # Placeholder

        return ComparisonStats(
            metric_name=metric_path,
            baseline_mean=baseline_mean,
            baseline_std=baseline_std,
            optimized_mean=optimized_mean,
            optimized_std=optimized_std,
            improvement_percent=improvement,
            statistical_significance=significance,
            sample_size=min(len(baseline_values), len(optimized_values))
        )

    def display_header(self):
        """Display dashboard header"""
        if RICH_AVAILABLE:
            title = "[bold blue]ORB-SLAM3 Performance Dashboard[/bold blue]"
            if self.results_data:
                subtitle = f"[dim]Results from {self.results_data['metadata']['timestamp']}[/dim]"
                total_runs = self.results_data['metadata']['total_runs']
                successful_runs = self.results_data['metadata']['successful_runs']
                subtitle += f"\n[dim]{successful_runs}/{total_runs} successful runs[/dim]"
                try:
                    labels = self.results_data.get("metadata", {}).get("labels", {})
                    if labels:
                        subtitle += f"\n[dim]Baseline: {labels.get('baseline','Baseline')}[/dim]"
                        subtitle += f"\n[dim]Improved: {labels.get('optimized','Optimized')}[/dim]"
                except Exception:
                    pass
            else:
                subtitle = "[dim]No results loaded[/dim]"

            header = Panel(f"{title}\n{subtitle}", style="blue", box=box.DOUBLE)
            self.console.print(header)
        else:
            print("=" * 60)
            print("           ORB-SLAM3 Performance Dashboard")
            if self.results_data:
                print(f"         Results from {self.results_data['metadata']['timestamp']}")
                total_runs = self.results_data['metadata']['total_runs']
                successful_runs = self.results_data['metadata']['successful_runs']
                print(f"         {successful_runs}/{total_runs} successful runs")
            print("=" * 60)

    def display_summary_table(self):
        """Display summary comparison table"""
        if not self.results_data:
            print("No results loaded")
            return

        # Key metrics to compare
        metrics = [
            ("Runtime", "total_runtime_ms", "ms", True),
            ("Memory Peak", "system_metrics.memory_mb_peak", "MB", True),
            ("CPU Average", "system_metrics.cpu_percent_avg", "%", True),
            ("Frames Processed", "slam_metrics.processed_frames", "", False),
            ("Frames Lost", "slam_metrics.lost_frames", "", True),
            ("Keyframes Created", "slam_metrics.keyframes_created", "", False),
            ("RMSE Translation", "accuracy_metrics.rmse_translation", "", True),
            ("RMSE Rotation", "accuracy_metrics.rmse_rotation", "°", True)
        ]

        # Dynamic labels (if provided in metadata)
        baseline_label = "Baseline"
        optimized_label = "Optimized"
        try:
            if "metadata" in self.results_data and "labels" in self.results_data["metadata"]:
                labels = self.results_data["metadata"]["labels"]
                baseline_label = labels.get("baseline", baseline_label)
                optimized_label = labels.get("optimized", optimized_label)
        except Exception:
            pass

        if RICH_AVAILABLE:
            table = Table(title="Performance Comparison Summary", box=box.ROUNDED, expand=True)
            table.add_column("Metric", style="cyan", width=22, no_wrap=True)
            table.add_column(baseline_label, style="white", justify="right", no_wrap=True, overflow="fold")
            table.add_column(optimized_label, style="green", justify="right", no_wrap=True, overflow="fold")
            table.add_column("Improvement", style="yellow", justify="right", no_wrap=True)
            table.add_column("Significance", style="blue", justify="center", no_wrap=True)

            for name, path, unit, lower_is_better in metrics:
                try:
                    stats = self.calculate_comparison_stats(path)

                    # Format values
                    baseline_str = f"{stats.baseline_mean:.1f}"
                    optimized_str = f"{stats.optimized_mean:.1f}"

                    if unit:
                        baseline_str += f" {unit}"
                        optimized_str += f" {unit}"

                    # Color code improvement
                    improvement = stats.improvement_percent
                    if lower_is_better:
                        improvement_color = "green" if improvement > 0 else "red"
                    else:
                        improvement_color = "green" if improvement < 0 else "red"
                        improvement = -improvement  # Flip sign for "higher is better" metrics

                    improvement_str = f"[{improvement_color}]{improvement:+.1f}%[/{improvement_color}]"

                    # Significance indicator
                    sig_indicator = "*" if stats.statistical_significance > 0.95 else "~"

                    table.add_row(
                        name,
                        baseline_str,
                        optimized_str,
                        improvement_str,
                        sig_indicator
                    )

                except Exception as e:
                    table.add_row(name, "N/A", "N/A", "N/A", "!")

            self.console.print(table)
        else:
            print("\n=== Performance Comparison Summary ===")
            print(f"{'Metric':<20} {baseline_label:<12} {optimized_label:<12} {'Improvement':<12}")
            print("-" * 60)

            for name, path, unit, lower_is_better in metrics:
                try:
                    stats = self.calculate_comparison_stats(path)
                    improvement = stats.improvement_percent
                    if not lower_is_better:
                        improvement = -improvement

                    print(f"{name:<15} {stats.baseline_mean:<12.1f} {stats.optimized_mean:<12.1f} {improvement:+.1f}%")
                except:
                    print(f"{name:<15} {'N/A':<12} {'N/A':<12} {'N/A':<12}")

    def export_html(self, output_file: Path):
        """Export dashboard views to a simple self-contained HTML file"""
        if not self.results_data:
            print("No results loaded")
            return

        # Dynamic labels
        baseline_label = "Baseline"
        optimized_label = "Optimized"
        try:
            labels = self.results_data.get("metadata", {}).get("labels", {})
            baseline_label = labels.get("baseline", baseline_label)
            optimized_label = labels.get("optimized", optimized_label)
        except Exception:
            pass

        # Summary metrics (same as console)
        metrics = [
            ("Runtime", "total_runtime_ms", "ms", True),
            ("Memory Peak", "system_metrics.memory_mb_peak", "MB", True),
            ("CPU Average", "system_metrics.cpu_percent_avg", "%", True),
            ("Frames Processed", "slam_metrics.processed_frames", "", False),
            ("Frames Lost", "slam_metrics.lost_frames", "", True),
            ("Keyframes Created", "slam_metrics.keyframes_created", "", False),
            ("RMSE Translation", "accuracy_metrics.rmse_translation", "", True),
            ("RMSE Rotation", "accuracy_metrics.rmse_rotation", "°", True),
        ]

        def html_escape(s: str) -> str:
            return (s.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;"))

        # Header
        meta = self.results_data.get("metadata", {})
        title = "ORB-SLAM3 Performance Dashboard"
        subtitle = f"Results from {html_escape(meta.get('timestamp',''))}"
        success = f"{meta.get('successful_runs',0)}/{meta.get('total_runs',0)} successful runs"

        # Build summary table rows
        summary_rows = []
        for name, path, unit, lower_is_better in metrics:
            try:
                stats = self.calculate_comparison_stats(path)
                base = f"{stats.baseline_mean:.1f}{(' ' + unit) if unit else ''}"
                opt = f"{stats.optimized_mean:.1f}{(' ' + unit) if unit else ''}"
                improvement = stats.improvement_percent
                if not lower_is_better:
                    improvement = -improvement
                imp_str = f"{improvement:+.1f}%"
                summary_rows.append((name, base, opt, imp_str))
            except Exception:
                summary_rows.append((name, "N/A", "N/A", "N/A"))

        # Per-sequence averages
        sequences = {}
        for result in self.baseline_results + self.optimized_results:
            seq_name = result["sequence"]
            if seq_name not in sequences:
                sequences[seq_name] = {"baseline": [], "optimized": []}
            sequences[seq_name][result["version"]].append(result)

        seq_rows = []
        for seq_name, seq_results in sorted(sequences.items()):
            baseline_runtimes = [r["total_runtime_ms"] for r in seq_results["baseline"]]
            optimized_runtimes = [r["total_runtime_ms"] for r in seq_results["optimized"]]
            if baseline_runtimes and optimized_runtimes:
                baseline_avg = statistics.mean(baseline_runtimes)
                optimized_avg = statistics.mean(optimized_runtimes)
                improvement = ((baseline_avg - optimized_avg) / baseline_avg) * 100 if baseline_avg else 0.0
                seq_rows.append(
                    (seq_name, f"{baseline_avg:.1f}", f"{optimized_avg:.1f}", f"{improvement:+.1f}%", f"{len(baseline_runtimes)}/{len(optimized_runtimes)}")
                )

        html = [
            "<!doctype html>",
            "<meta charset='utf-8'>",
            f"<title>{html_escape(title)}</title>",
            "<style>body{font-family:system-ui,Arial,sans-serif;margin:24px} table{border-collapse:collapse;width:100%;margin:16px 0} th,td{border:1px solid #ddd;padding:8px} th{background:#f5f5f5;text-align:left} caption{font-weight:bold;margin-bottom:8px} .meta{color:#555;margin-bottom:16px}</style>",
            f"<h1>{html_escape(title)}</h1>",
            f"<div class='meta'>{html_escape(subtitle)}<br>\n{html_escape(success)}<br>\nBaseline: {html_escape(baseline_label)} &nbsp;|&nbsp; Improved: {html_escape(optimized_label)}</div>",
            "<table>",
            f"<caption>Performance Comparison Summary</caption>",
            "<thead><tr>",
            "<th>Metric</th>",
            f"<th>{html_escape(baseline_label)}</th>",
            f"<th>{html_escape(optimized_label)}</th>",
            "<th>Improvement</th>",
            "</tr></thead>",
            "<tbody>",
        ]
        for name, base, opt, imp in summary_rows:
            html.append(f"<tr><td>{html_escape(name)}</td><td style='text-align:right'>{html_escape(base)}</td><td style='text-align:right'>{html_escape(opt)}</td><td style='text-align:right'>{html_escape(imp)}</td></tr>")
        html += ["</tbody></table>"]

        # Per-sequence table
        html += [
            "<table>",
            f"<caption>Per-Sequence Performance</caption>",
            "<thead><tr>",
            "<th>Sequence</th>",
            f"<th>{html_escape(baseline_label)} Avg (ms)</th>",
            f"<th>{html_escape(optimized_label)} Avg (ms)</th>",
            "<th>Improvement</th>",
            "<th>Runs</th>",
            "</tr></thead>",
            "<tbody>",
        ]
        for seq_name, b, o, imp, runs in seq_rows:
            html.append(f"<tr><td>{html_escape(seq_name)}</td><td style='text-align:right'>{b}</td><td style='text-align:right'>{o}</td><td style='text-align:right'>{imp}</td><td style='text-align:center'>{runs}</td></tr>")
        html += ["</tbody></table>"]

        output_file = Path(output_file)
        output_file.write_text("\n".join(html))
        print(f"HTML dashboard exported to: {output_file}")

    def display_sequence_breakdown(self):
        """Display per-sequence performance breakdown"""
        if not self.results_data:
            return

        # Dynamic labels (if provided)
        baseline_label = "Baseline"
        optimized_label = "Optimized"
        try:
            if "metadata" in self.results_data and "labels" in self.results_data["metadata"]:
                labels = self.results_data["metadata"]["labels"]
                baseline_label = labels.get("baseline", baseline_label)
                optimized_label = labels.get("optimized", optimized_label)
        except Exception:
            pass

        # Group results by sequence
        sequences = {}
        for result in self.baseline_results + self.optimized_results:
            seq_name = result["sequence"]
            if seq_name not in sequences:
                sequences[seq_name] = {"baseline": [], "optimized": []}
            sequences[seq_name][result["version"]].append(result)

        if RICH_AVAILABLE:
            table = Table(title="Per-Sequence Performance", box=box.ROUNDED, expand=True)
            table.add_column("Sequence", style="cyan", no_wrap=True, overflow="fold")
            table.add_column(f"{baseline_label} Avg (ms)", style="white", justify="right", no_wrap=True, overflow="fold")
            table.add_column(f"{optimized_label} Avg (ms)", style="green", justify="right", no_wrap=True, overflow="fold")
            table.add_column("Improvement", style="yellow", justify="right", no_wrap=True)
            table.add_column("Runs", style="blue", justify="center", no_wrap=True)

            for seq_name, seq_results in sorted(sequences.items()):
                baseline_runtimes = [r["total_runtime_ms"] for r in seq_results["baseline"]]
                optimized_runtimes = [r["total_runtime_ms"] for r in seq_results["optimized"]]

                if baseline_runtimes and optimized_runtimes:
                    baseline_avg = statistics.mean(baseline_runtimes)
                    optimized_avg = statistics.mean(optimized_runtimes)
                    improvement = ((baseline_avg - optimized_avg) / baseline_avg) * 100

                    improvement_color = "green" if improvement > 0 else "red"
                    improvement_str = f"[{improvement_color}]{improvement:+.1f}%[/{improvement_color}]"

                    run_count = f"{len(baseline_runtimes)}/{len(optimized_runtimes)}"

                    table.add_row(
                        seq_name,
                        f"{baseline_avg:.1f}",
                        f"{optimized_avg:.1f}",
                        improvement_str,
                        run_count
                    )

            self.console.print(table)
        else:
            print("\n=== Per-Sequence Performance ===")
            print(f"{'Sequence':<25} {baseline_label:<12} {optimized_label:<12} {'Improvement':<12}")
            print("-" * 70)

            for seq_name, seq_results in sorted(sequences.items()):
                baseline_runtimes = [r["total_runtime_ms"] for r in seq_results["baseline"]]
                optimized_runtimes = [r["total_runtime_ms"] for r in seq_results["optimized"]]

                if baseline_runtimes and optimized_runtimes:
                    baseline_avg = statistics.mean(baseline_runtimes)
                    optimized_avg = statistics.mean(optimized_runtimes)
                    improvement = ((baseline_avg - optimized_avg) / baseline_avg) * 100

                    print(f"{seq_name:<25} {baseline_avg:<12.1f} {optimized_avg:<12.1f} {improvement:+.1f}%")

    def display_system_metrics(self):
        """Display system performance metrics"""
        if not self.results_data:
            return

        system_info = self.results_data["metadata"]["system_info"]

        if RICH_AVAILABLE:
            # System info panel
            system_text = f"""
[bold]Hardware Configuration:[/bold]
  CPU Cores: {system_info['cpu_count']}
  Memory: {system_info['memory_gb']:.1f} GB
  Platform: {system_info['platform']}

[bold]Test Configuration:[/bold]
  Total Runs: {self.results_data['metadata']['total_runs']}
  Successful: {self.results_data['metadata']['successful_runs']}
  Sequences: {self.results_data['metadata']['sequences_tested']}
"""

            panel = Panel(system_text.strip(), title="System Information", style="blue")
            self.console.print(panel)
        else:
            print("\n=== System Information ===")
            print(f"CPU Cores: {system_info['cpu_count']}")
            print(f"Memory: {system_info['memory_gb']:.1f} GB")
            print(f"Platform: {system_info['platform']}")
            print(f"Total Runs: {self.results_data['metadata']['total_runs']}")
            print(f"Successful: {self.results_data['metadata']['successful_runs']}")

    def generate_plots(self, output_dir: Path = None):
        """Generate performance plots"""
        if not MATPLOTLIB_AVAILABLE:
            print("Matplotlib not available for plotting")
            return

        if not self.results_data:
            print("No results loaded")
            return

        if output_dir is None:
            output_dir = Path("plots")
        output_dir.mkdir(exist_ok=True)

        # Runtime comparison plot
        self._plot_runtime_comparison(output_dir)

        # Memory usage plot
        self._plot_memory_comparison(output_dir)

        # Accuracy comparison plot
        self._plot_accuracy_comparison(output_dir)

        print(f"Plots saved to: {output_dir}")

    def _plot_runtime_comparison(self, output_dir: Path):
        """Generate runtime comparison plot"""
        baseline_runtimes = [r["total_runtime_ms"] for r in self.baseline_results]
        optimized_runtimes = [r["total_runtime_ms"] for r in self.optimized_results]

        plt.figure(figsize=(12, 6))

        # Box plot comparison
        plt.subplot(1, 2, 1)
        plt.boxplot([baseline_runtimes, optimized_runtimes],
                   labels=['Baseline', 'Optimized'])
        plt.title('Runtime Distribution Comparison')
        plt.ylabel('Runtime (ms)')
        plt.grid(True, alpha=0.3)

        # Histogram overlay
        plt.subplot(1, 2, 2)
        plt.hist(baseline_runtimes, alpha=0.7, label='Baseline', bins=20)
        plt.hist(optimized_runtimes, alpha=0.7, label='Optimized', bins=20)
        plt.title('Runtime Distribution')
        plt.xlabel('Runtime (ms)')
        plt.ylabel('Frequency')
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir / 'runtime_comparison.png', dpi=150)
        plt.close()

    def _plot_memory_comparison(self, output_dir: Path):
        """Generate memory usage comparison plot"""
        baseline_memory = [r["system_metrics"]["memory_mb_peak"] for r in self.baseline_results]
        optimized_memory = [r["system_metrics"]["memory_mb_peak"] for r in self.optimized_results]

        plt.figure(figsize=(10, 6))

        plt.boxplot([baseline_memory, optimized_memory],
                   labels=['Baseline', 'Optimized'])
        plt.title('Peak Memory Usage Comparison')
        plt.ylabel('Peak Memory (MB)')
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir / 'memory_comparison.png', dpi=150)
        plt.close()

    def _plot_accuracy_comparison(self, output_dir: Path):
        """Generate accuracy comparison plot"""
        baseline_rmse = [r["accuracy_metrics"]["rmse_translation"] for r in self.baseline_results]
        optimized_rmse = [r["accuracy_metrics"]["rmse_translation"] for r in self.optimized_results]

        plt.figure(figsize=(10, 6))

        plt.scatter(range(len(baseline_rmse)), baseline_rmse,
                   alpha=0.6, label='Baseline', s=30)
        plt.scatter(range(len(optimized_rmse)), optimized_rmse,
                   alpha=0.6, label='Optimized', s=30)

        plt.title('Translation RMSE Comparison')
        plt.xlabel('Run Number')
        plt.ylabel('RMSE Translation')
        plt.legend()
        plt.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(output_dir / 'accuracy_comparison.png', dpi=150)
        plt.close()

    def interactive_menu(self):
        """Interactive menu for dashboard"""
        while True:
            if RICH_AVAILABLE:
                self.console.clear()
            else:
                print("\n" * 50)  # Clear screen

            self.display_header()

            if RICH_AVAILABLE:
                menu = Table(box=box.ROUNDED)
                menu.add_column("Option", style="cyan", width=8)
                menu.add_column("Description", style="white")

                menu.add_row("1", "Load Results File")
                menu.add_row("2", "Summary Comparison")
                menu.add_row("3", "Sequence Breakdown")
                menu.add_row("4", "System Information")
                menu.add_row("5", "Generate Plots")
                menu.add_row("6", "Export Report")
                menu.add_row("q", "Quit")

                self.console.print(menu)
            else:
                print("\n--- Dashboard Menu ---")
                print("1. Load Results File")
                print("2. Summary Comparison")
                print("3. Sequence Breakdown")
                print("4. System Information")
                print("5. Generate Plots")
                print("6. Export Report")
                print("q. Quit")

            try:
                choice = input("\nSelect option: ").strip().lower()

                if choice == 'q':
                    break
                elif choice == '1':
                    self.load_results_interactive()
                elif choice == '2':
                    self.display_summary_table()
                elif choice == '3':
                    self.display_sequence_breakdown()
                elif choice == '4':
                    self.display_system_metrics()
                elif choice == '5':
                    self.generate_plots()
                elif choice == '6':
                    self.export_report()
                else:
                    print("Invalid option!")

                if choice != 'q':
                    input("\nPress Enter to continue...")

            except KeyboardInterrupt:
                break

    def load_results_interactive(self):
        """Interactive results loading"""
        results_dir = Path("benchmark_results")

        if not results_dir.exists():
            print("No benchmark results directory found")
            return

        json_files = list(results_dir.glob("*.json"))

        if not json_files:
            print("No result files found")
            return

        print("\nAvailable result files:")
        for i, file_path in enumerate(json_files, 1):
            print(f"{i}. {file_path.name}")

        try:
            choice = int(input(f"\nSelect file (1-{len(json_files)}): "))
            if 1 <= choice <= len(json_files):
                selected_file = json_files[choice - 1]
                if self.load_results(selected_file):
                    print(f"* Loaded results from {selected_file.name}")
                else:
                    print("! Failed to load results")
        except ValueError:
            print("Invalid selection")

    def export_report(self):
        """Export comprehensive report"""
        if not self.results_data:
            print("No results loaded")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = Path(f"performance_report_{timestamp}.md")

        with open(report_file, 'w') as f:
            f.write("# ORB-SLAM3 Performance Report\n\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n\n")

            # System info
            system_info = self.results_data["metadata"]["system_info"]
            f.write("## System Configuration\n\n")
            f.write(f"- CPU Cores: {system_info['cpu_count']}\n")
            f.write(f"- Memory: {system_info['memory_gb']:.1f} GB\n")
            f.write(f"- Platform: {system_info['platform']}\n\n")

            # Test summary
            f.write("## Test Summary\n\n")
            f.write(f"- Total Runs: {self.results_data['metadata']['total_runs']}\n")
            f.write(f"- Successful Runs: {self.results_data['metadata']['successful_runs']}\n")
            f.write(f"- Sequences Tested: {self.results_data['metadata']['sequences_tested']}\n\n")

            # Performance comparison
            f.write("## Performance Comparison\n\n")
            f.write("| Metric | Baseline | Optimized | Improvement |\n")
            f.write("|--------|----------|-----------|-------------|\n")

            metrics = [
                ("Runtime", "total_runtime_ms", "ms"),
                ("Memory Peak", "system_metrics.memory_mb_peak", "MB"),
                ("RMSE Translation", "accuracy_metrics.rmse_translation", "")
            ]

            for name, path, unit in metrics:
                try:
                    stats = self.calculate_comparison_stats(path)
                    f.write(f"| {name} | {stats.baseline_mean:.1f} {unit} | "
                           f"{stats.optimized_mean:.1f} {unit} | {stats.improvement_percent:+.1f}% |\n")
                except:
                    f.write(f"| {name} | N/A | N/A | N/A |\n")

            f.write("\n")

        print(f"Report exported to: {report_file}")

def main():
    parser = argparse.ArgumentParser(description="ORB-SLAM3 Results Dashboard")
    parser.add_argument("--results-file", type=Path, help="Results JSON file to load")
    parser.add_argument("--export-plots", action="store_true", help="Generate and export plots")
    parser.add_argument("--export-report", action="store_true", help="Export markdown report")
    parser.add_argument("--export-html", type=Path, help="Export dashboard as HTML to this file")
    parser.add_argument("--no-interactive", action="store_true", help="Non-interactive mode")

    args = parser.parse_args()

    dashboard = ResultsDashboard()

    # Load results if specified
    if args.results_file:
        if not dashboard.load_results(args.results_file):
            return 1

    # Export plots if requested
    if args.export_plots:
        dashboard.generate_plots()

    # Export report if requested
    if args.export_report:
        dashboard.export_report()

    # Export HTML if requested
    if args.export_html:
        dashboard.export_html(args.export_html)

    # Interactive mode
    if not args.no_interactive:
        dashboard.interactive_menu()
    else:
        # Non-interactive: show summary
        dashboard.display_header()
        dashboard.display_summary_table()
        dashboard.display_sequence_breakdown()

    return 0

if __name__ == "__main__":
    sys.exit(main())