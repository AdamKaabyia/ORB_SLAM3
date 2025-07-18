#!/usr/bin/env python3
"""
Ground Truth Comparison for ORB-SLAM3
Compare both upstream and optimized versions against ground truth data
"""

import sys
import os
import subprocess
from pathlib import Path
import time

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Import our progress monitoring
import orbslam3_progress

class GroundTruthEvaluator:
    def __init__(self):
        self.console = Console() if RICH_AVAILABLE else None
        self.ground_truth_dir = Path("evaluation/Ground_truth/EuRoC_left_cam")

        # Mapping from sequence names to ground truth files
        self.gt_mapping = {
            "MH_01_easy": "MH01_GT.txt",
            "MH_02_easy": "MH02_GT.txt",
            "MH_03_medium": "MH03_GT.txt",
            "MH_04_difficult": "MH04_GT.txt",
            "MH_05_difficult": "MH05_GT.txt",
            "V1_01_easy": "V101_GT.txt",
            "V1_02_medium": "V102_GT.txt",
            "V1_03_difficult": "V103_GT.txt",
            "V2_01_easy": "V201_GT.txt",
            "V2_02_medium": "V202_GT.txt",
            "V2_03_medium": "V203_GT.txt"
        }

    def get_ground_truth_file(self, sequence_path):
        """Get the ground truth file for a given sequence"""
        sequence_name = Path(sequence_path).name
        if sequence_name in self.gt_mapping:
            gt_file = self.ground_truth_dir / self.gt_mapping[sequence_name]
            if gt_file.exists():
                return gt_file
        return None

    def convert_trajectory_format(self, orbslam_trajectory, output_file):
        """Convert ORB-SLAM3 trajectory format to evaluation format"""
        try:
            with open(orbslam_trajectory, 'r') as f_in, open(output_file, 'w') as f_out:
                for line in f_in:
                    if line.strip():
                        parts = line.strip().split()
                        if len(parts) >= 8:
                            # ORB-SLAM3 format: timestamp x y z qx qy qz qw
                            # Evaluation format: timestamp x y z qx qy qz qw
                            timestamp = parts[0]
                            x, y, z = parts[1], parts[2], parts[3]
                            qx, qy, qz, qw = parts[4], parts[5], parts[6], parts[7]
                            f_out.write(f"{timestamp} {x} {y} {z} {qx} {qy} {qz} {qw}\n")
            return True
        except Exception as e:
            if self.console:
                self.console.print(f"[red]Error converting trajectory: {e}[/red]")
            return False

    def evaluate_against_ground_truth(self, trajectory_file, ground_truth_file):
        """Evaluate trajectory against ground truth using ATE"""
        try:
            # Convert trajectory to evaluation format
            temp_traj = trajectory_file.parent / f"temp_{trajectory_file.name}"
            if not self.convert_trajectory_format(trajectory_file, temp_traj):
                return None

            # Run ATE evaluation
            result = subprocess.run([
                "python3", "evaluation/evaluate_ate_scale.py",
                str(ground_truth_file),
                str(temp_traj),
                "--verbose2"
            ], capture_output=True, text=True, cwd=".")

            # Clean up temp file
            if temp_traj.exists():
                temp_traj.unlink()

            if result.returncode == 0:
                # Parse output
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if "absolute_translational_error.rmse" in line:
                        rmse = float(line.split()[-2])  # Extract RMSE value
                        return {
                            "ate_rmse": rmse,
                            "success": True,
                            "raw_output": result.stdout
                        }

            return {
                "ate_rmse": float('inf'),
                "success": False,
                "error": result.stderr
            }

        except Exception as e:
            return {
                "ate_rmse": float('inf'),
                "success": False,
                "error": str(e)
            }

    def run_comparison(self, sequence_path, vocab_path, config_path):
        """Run both versions and compare against ground truth"""
        sequence_name = Path(sequence_path).name

        if self.console:
            self.console.print(Panel.fit(
                f"[bold blue]Ground Truth Comparison[/bold blue]\n"
                f"Sequence: [cyan]{sequence_path}[/cyan]\n"
                f"Evaluating: [yellow]upstream vs optimized vs ground truth[/yellow]",
                title="Starting Evaluation"
            ))

        # Check if ground truth exists
        gt_file = self.get_ground_truth_file(sequence_path)
        if not gt_file:
            if self.console:
                self.console.print(f"[red]No ground truth available for {sequence_name}[/red]")
            return None

        results = {}

        # Test both versions
        for version in ["upstream", "optimized"]:
            if self.console:
                self.console.print(f"\n[cyan]Running {version} version...[/cyan]")

            # Run ORB-SLAM3 with our progress monitoring
            exit_code = orbslam3_progress.run_orbslam_with_progress(
                version, vocab_path, config_path, sequence_path
            )

            if exit_code != 0:
                if self.console:
                    self.console.print(f"[red]{version} version failed[/red]")
                results[version] = {"success": False, "error": "ORB-SLAM3 execution failed"}
                continue

            # Find the generated trajectory file
            results_dir = Path("results")
            trajectory_files = list(results_dir.glob(f"f_{sequence_name}_{version}_*_trajectory.txt"))

            if not trajectory_files:
                if self.console:
                    self.console.print(f"[red]No trajectory file found for {version}[/red]")
                results[version] = {"success": False, "error": "No trajectory file generated"}
                continue

            trajectory_file = trajectory_files[-1]  # Get most recent

            # Evaluate against ground truth
            if self.console:
                self.console.print(f"[yellow]Evaluating {version} against ground truth...[/yellow]")

            evaluation = self.evaluate_against_ground_truth(trajectory_file, gt_file)
            results[version] = evaluation

        return results

    def display_results(self, results, sequence_name):
        """Display comparison results"""
        if not results:
            return

        if self.console:
            # Create comparison table
            table = Table(title=f"Ground Truth Accuracy Comparison: {sequence_name}")
            table.add_column("Version", style="cyan", no_wrap=True)
            table.add_column("ATE RMSE (m)", style="magenta", justify="right")
            table.add_column("Status", style="green")
            table.add_column("Relative to GT", style="yellow", justify="right")

            ground_truth_rmse = 0.0  # Perfect reference

            for version in ["upstream", "optimized"]:
                if version in results:
                    result = results[version]
                    if result["success"]:
                        rmse = result["ate_rmse"]
                        error_vs_gt = f"{rmse:.3f}m"
                        status = "✓ Success"
                        table.add_row(version.title(), f"{rmse:.3f}", status, error_vs_gt)
                    else:
                        table.add_row(version.title(), "∞", "✗ Failed", "N/A")

            self.console.print(table)

            # Show which version is more accurate
            if "upstream" in results and "optimized" in results:
                if results["upstream"]["success"] and results["optimized"]["success"]:
                    upstream_rmse = results["upstream"]["ate_rmse"]
                    optimized_rmse = results["optimized"]["ate_rmse"]

                    if upstream_rmse < optimized_rmse:
                        winner = "upstream"
                        improvement = ((optimized_rmse - upstream_rmse) / upstream_rmse) * 100
                        self.console.print(f"\n[green]Upstream version is {improvement:.1f}% more accurate[/green]")
                    elif optimized_rmse < upstream_rmse:
                        winner = "optimized"
                        improvement = ((upstream_rmse - optimized_rmse) / optimized_rmse) * 100
                        self.console.print(f"\n[green]Optimized version is {improvement:.1f}% more accurate[/green]")
                    else:
                        self.console.print(f"\n[yellow]Both versions have similar accuracy[/yellow]")

        else:
            # Fallback text output
            print(f"\nGround Truth Comparison: {sequence_name}")
            print("=" * 50)
            for version in ["upstream", "optimized"]:
                if version in results and results[version]["success"]:
                    rmse = results[version]["ate_rmse"]
                    print(f"{version.title()}: {rmse:.3f}m ATE RMSE")
                else:
                    print(f"{version.title()}: Failed")

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 ground_truth_comparison.py <vocab> <config> <sequence>")
        print("")
        print("Example:")
        print("python3 ground_truth_comparison.py \\")
        print("  /opt/orb-slam3/Vocabulary/ORBvoc.txt \\")
        print("  /opt/orb-slam3/Examples/Monocular/EuRoC.yaml \\")
        print("  /workspace/datasets/EuRoC/machine_hall/MH_01_easy")
        sys.exit(1)

    vocab_path = sys.argv[1]
    config_path = sys.argv[2]
    sequence_path = sys.argv[3]

    evaluator = GroundTruthEvaluator()
    results = evaluator.run_comparison(sequence_path, vocab_path, config_path)

    if results:
        sequence_name = Path(sequence_path).name
        evaluator.display_results(results, sequence_name)
    else:
        print("Evaluation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()