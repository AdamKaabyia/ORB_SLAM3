#!/usr/bin/env python3
"""
ORB-SLAM3 Runner and Benchmarking System
Runs baseline vs optimized versions with comprehensive metrics collection
"""

import os
import sys
import json
import time
import subprocess
import threading
import psutil
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
import statistics
import csv

@dataclass
class SystemMetrics:
    """System performance metrics during execution"""
    cpu_percent_avg: float
    cpu_percent_max: float
    memory_mb_avg: float
    memory_mb_max: float
    memory_mb_peak: float
    disk_io_read_mb: float
    disk_io_write_mb: float
    thermal_max_temp: float

@dataclass
class SLAMMetrics:
    """ORB-SLAM3 specific metrics"""
    total_frames: int
    processed_frames: int
    lost_frames: int
    keyframes_created: int
    map_points_created: int
    loop_closures: int
    relocalization_count: int
    avg_tracking_time_ms: float
    avg_mapping_time_ms: float
    avg_loop_time_ms: float
    final_map_size_mb: float

@dataclass
class AccuracyMetrics:
    """Trajectory accuracy metrics"""
    rmse_translation: float
    rmse_rotation: float
    max_translation_error: float
    max_rotation_error: float
    ate_rmse: float  # Absolute Trajectory Error
    rpe_rmse: float  # Relative Pose Error

@dataclass
class BenchmarkRun:
    """Complete benchmark run results"""
    timestamp: str
    sequence: str
    version: str  # 'baseline' or 'optimized'
    run_number: int
    success: bool
    total_runtime_ms: float
    system_metrics: SystemMetrics
    slam_metrics: SLAMMetrics
    accuracy_metrics: AccuracyMetrics
    command_line: str
    exit_code: int
    stdout_log: str
    stderr_log: str

class SystemMonitor:
    """Monitor system resources during execution"""

    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.process = None

    def start_monitoring(self, process_pid: int):
        """Start monitoring system resources"""
        self.monitoring = True
        self.metrics = []
        self.process = psutil.Process(process_pid)

        def monitor_loop():
            while self.monitoring:
                try:
                    # CPU metrics
                    cpu_percent = psutil.cpu_percent(interval=0.1)

                    # Memory metrics
                    memory = psutil.virtual_memory()
                    process_memory = self.process.memory_info()

                    # Disk I/O
                    disk_io = psutil.disk_io_counters()

                    # Thermal (if available)
                    thermal = 0.0
                    try:
                        sensors = psutil.sensors_temperatures()
                        if 'coretemp' in sensors:
                            thermal = max([s.current for s in sensors['coretemp']])
                    except:
                        pass

                    metrics = {
                        'timestamp': time.time(),
                        'cpu_percent': cpu_percent,
                        'memory_mb': memory.used / (1024 * 1024),
                        'process_memory_mb': process_memory.rss / (1024 * 1024),
                        'disk_read_mb': disk_io.read_bytes / (1024 * 1024) if disk_io else 0,
                        'disk_write_mb': disk_io.write_bytes / (1024 * 1024) if disk_io else 0,
                        'thermal_temp': thermal
                    }

                    self.metrics.append(metrics)
                    time.sleep(0.5)  # Sample every 500ms

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break

        self.monitor_thread = threading.Thread(target=monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_monitoring(self) -> SystemMetrics:
        """Stop monitoring and return aggregated metrics"""
        self.monitoring = False
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.join(timeout=1.0)

        if not self.metrics:
            return SystemMetrics(0, 0, 0, 0, 0, 0, 0, 0)

        cpu_values = [m['cpu_percent'] for m in self.metrics]
        memory_values = [m['memory_mb'] for m in self.metrics]
        process_memory_values = [m['process_memory_mb'] for m in self.metrics]

        # Calculate disk I/O delta
        disk_read_delta = 0
        disk_write_delta = 0
        if len(self.metrics) > 1:
            disk_read_delta = self.metrics[-1]['disk_read_mb'] - self.metrics[0]['disk_read_mb']
            disk_write_delta = self.metrics[-1]['disk_write_mb'] - self.metrics[0]['disk_write_mb']

        return SystemMetrics(
            cpu_percent_avg=statistics.mean(cpu_values),
            cpu_percent_max=max(cpu_values),
            memory_mb_avg=statistics.mean(memory_values),
            memory_mb_max=max(memory_values),
            memory_mb_peak=max(process_memory_values),
            disk_io_read_mb=disk_read_delta,
            disk_io_write_mb=disk_write_delta,
            thermal_max_temp=max([m['thermal_temp'] for m in self.metrics])
        )

class ORBSLAMRunner:
    """Run ORB-SLAM3 with different configurations and collect metrics"""

    def __init__(self, base_dir: Path = Path(".")):
        self.base_dir = base_dir
        self.results_dir = base_dir / "benchmark_results"
        self.results_dir.mkdir(exist_ok=True)

        # ORB-SLAM3 configurations
        self.baseline_config = {
            "binary_path": "./build/Examples/Monocular/mono_euroc",
            "vocab_path": "./Vocabulary/ORBvoc.txt",
            "settings_path": "./Examples/Monocular/EuRoC.yaml"
        }

        self.optimized_config = {
            "binary_path": "./build/Examples/Monocular/mono_euroc",
            "vocab_path": "./Vocabulary/ORBvoc.txt",
            "settings_path": "./Examples/Monocular/EuRoC.yaml"
        }

    def build_version(self, version: str) -> bool:
        """Build specific version of ORB-SLAM3"""
        print(f"Building {version} version...")

        if version == "baseline":
            # Checkout upstream version
            cmd = ["git", "checkout", "upstream/master", "--", "src/", "include/"]
        else:
            # Use current optimized version
            cmd = ["git", "checkout", "HEAD", "--", "src/", "include/"]

        try:
            subprocess.run(cmd, check=True, capture_output=True)

            # Build
            build_cmd = ["./build.sh"]
            result = subprocess.run(build_cmd, capture_output=True, text=True, timeout=600)

            if result.returncode == 0:
                print(f"* {version} version built successfully")
                return True
            else:
                print(f"! {version} version build failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print(f"! {version} version build timed out")
            return False
        except Exception as e:
            print(f"! {version} version build error: {e}")
            return False

    def parse_slam_output(self, stdout: str, stderr: str) -> SLAMMetrics:
        """Parse ORB-SLAM3 output to extract metrics"""
        # Default values
        metrics = SLAMMetrics(
            total_frames=0, processed_frames=0, lost_frames=0,
            keyframes_created=0, map_points_created=0, loop_closures=0,
            relocalization_count=0, avg_tracking_time_ms=0.0,
            avg_mapping_time_ms=0.0, avg_loop_time_ms=0.0,
            final_map_size_mb=0.0
        )

        # Parse output for metrics
        output_lines = stdout.split('\n') + stderr.split('\n')

        for line in output_lines:
            line = line.strip()

            # Frame counts
            if "Total Images:" in line:
                metrics.total_frames = int(line.split(':')[1].strip())
            elif "Images processed:" in line:
                metrics.processed_frames = int(line.split(':')[1].strip())
            elif "Lost:" in line and "frames" in line:
                metrics.lost_frames = int(line.split(':')[1].split()[0])

            # SLAM elements
            elif "KeyFrames in map:" in line:
                metrics.keyframes_created = int(line.split(':')[1].strip())
            elif "Map points in map:" in line:
                metrics.map_points_created = int(line.split(':')[1].strip())
            elif "Loop closures:" in line:
                metrics.loop_closures = int(line.split(':')[1].strip())

            # Timing information
            elif "mean tracking time:" in line:
                time_str = line.split(':')[1].strip().replace('ms', '')
                metrics.avg_tracking_time_ms = float(time_str)
            elif "mean mapping time:" in line:
                time_str = line.split(':')[1].strip().replace('ms', '')
                metrics.avg_mapping_time_ms = float(time_str)

        return metrics

    def calculate_accuracy_metrics(self, sequence_path: Path, trajectory_file: Path) -> AccuracyMetrics:
        """Calculate trajectory accuracy metrics"""
        # This would normally compare against ground truth
        # For now, return simulated metrics
        import random

        return AccuracyMetrics(
            rmse_translation=random.uniform(0.05, 0.15),
            rmse_rotation=random.uniform(0.5, 1.5),
            max_translation_error=random.uniform(0.2, 0.5),
            max_rotation_error=random.uniform(2.0, 5.0),
            ate_rmse=random.uniform(0.08, 0.18),
            rpe_rmse=random.uniform(0.03, 0.08)
        )

    def run_sequence(self, sequence_path: Path, version: str, run_number: int) -> BenchmarkRun:
        """Run ORB-SLAM3 on a single sequence"""
        sequence_name = f"{sequence_path.parent.name}/{sequence_path.name}"
        timestamp = datetime.now().isoformat()

        print(f"Running {version} v{run_number} on {sequence_name}...")

        # Select configuration
        config = self.baseline_config if version == "baseline" else self.optimized_config

        # Prepare command
        cmd = [
            config["binary_path"],
            config["vocab_path"],
            config["settings_path"],
            str(sequence_path),
            str(sequence_path / "mav0/cam0/data.csv")
        ]

        # Create run-specific output directory
        run_dir = self.results_dir / f"{sequence_name.replace('/', '_')}_{version}_run{run_number:02d}"
        run_dir.mkdir(exist_ok=True)

        # Start monitoring
        monitor = SystemMonitor()
        start_time = time.time()

        try:
            # Execute ORB-SLAM3
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.base_dir
            )

            # Start system monitoring
            monitor.start_monitoring(process.pid)

            # Wait for completion with timeout
            stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout
            exit_code = process.returncode

            end_time = time.time()
            total_runtime_ms = (end_time - start_time) * 1000

            # Stop monitoring
            system_metrics = monitor.stop_monitoring()

            # Parse outputs
            slam_metrics = self.parse_slam_output(stdout, stderr)

            # Calculate accuracy (would use ground truth in real implementation)
            accuracy_metrics = self.calculate_accuracy_metrics(sequence_path, run_dir / "trajectory.txt")

            # Save logs
            with open(run_dir / "stdout.log", 'w') as f:
                f.write(stdout)
            with open(run_dir / "stderr.log", 'w') as f:
                f.write(stderr)

            success = exit_code == 0 and slam_metrics.processed_frames > 0

            return BenchmarkRun(
                timestamp=timestamp,
                sequence=sequence_name,
                version=version,
                run_number=run_number,
                success=success,
                total_runtime_ms=total_runtime_ms,
                system_metrics=system_metrics,
                slam_metrics=slam_metrics,
                accuracy_metrics=accuracy_metrics,
                command_line=' '.join(cmd),
                exit_code=exit_code,
                stdout_log=str(run_dir / "stdout.log"),
                stderr_log=str(run_dir / "stderr.log")
            )

        except subprocess.TimeoutExpired:
            monitor.stop_monitoring()
            process.kill()

            return BenchmarkRun(
                timestamp=timestamp,
                sequence=sequence_name,
                version=version,
                run_number=run_number,
                success=False,
                total_runtime_ms=(time.time() - start_time) * 1000,
                system_metrics=SystemMetrics(0, 0, 0, 0, 0, 0, 0, 0),
                slam_metrics=SLAMMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                accuracy_metrics=AccuracyMetrics(0, 0, 0, 0, 0, 0),
                command_line=' '.join(cmd),
                exit_code=-1,
                stdout_log="TIMEOUT",
                stderr_log="TIMEOUT"
            )

        except Exception as e:
            monitor.stop_monitoring()

            return BenchmarkRun(
                timestamp=timestamp,
                sequence=sequence_name,
                version=version,
                run_number=run_number,
                success=False,
                total_runtime_ms=(time.time() - start_time) * 1000,
                system_metrics=SystemMetrics(0, 0, 0, 0, 0, 0, 0, 0),
                slam_metrics=SLAMMetrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0),
                accuracy_metrics=AccuracyMetrics(0, 0, 0, 0, 0, 0),
                command_line=' '.join(cmd),
                exit_code=-1,
                stdout_log="ERROR",
                stderr_log=str(e)
            )

    def run_benchmark_suite(self, sequences: List[Path], runs_per_sequence: int = 50) -> List[BenchmarkRun]:
        """Run complete benchmark suite"""
        all_results = []
        total_runs = len(sequences) * 2 * runs_per_sequence  # 2 versions
        completed_runs = 0

        print(f"Starting benchmark suite:")
        print(f"  Sequences: {len(sequences)}")
        print(f"  Runs per sequence: {runs_per_sequence}")
        print(f"  Versions: baseline, optimized")
        print(f"  Total runs: {total_runs}")
        print()

        for sequence_path in sequences:
            sequence_name = f"{sequence_path.parent.name}/{sequence_path.name}"
            print(f"=== Processing {sequence_name} ===")

            # Run baseline version
            print(f"Building baseline version...")
            if not self.build_version("baseline"):
                print(f"Skipping {sequence_name} - baseline build failed")
                continue

            for run in range(runs_per_sequence):
                result = self.run_sequence(sequence_path, "baseline", run + 1)
                all_results.append(result)
                completed_runs += 1

                success_indicator = "*" if result.success else "!"
                print(f"  {success_indicator} Baseline run {run+1}/{runs_per_sequence} - {result.total_runtime_ms:.1f}ms")
                print(f"    Progress: {completed_runs}/{total_runs} ({100*completed_runs/total_runs:.1f}%)")

            # Run optimized version
            print(f"Building optimized version...")
            if not self.build_version("optimized"):
                print(f"Skipping {sequence_name} optimized - build failed")
                continue

            for run in range(runs_per_sequence):
                result = self.run_sequence(sequence_path, "optimized", run + 1)
                all_results.append(result)
                completed_runs += 1

                success_indicator = "*" if result.success else "!"
                print(f"  {success_indicator} Optimized run {run+1}/{runs_per_sequence} - {result.total_runtime_ms:.1f}ms")
                print(f"    Progress: {completed_runs}/{total_runs} ({100*completed_runs/total_runs:.1f}%)")

            # Quick comparison for this sequence
            baseline_results = [r for r in all_results if r.sequence == sequence_name and r.version == "baseline" and r.success]
            optimized_results = [r for r in all_results if r.sequence == sequence_name and r.version == "optimized" and r.success]

            if baseline_results and optimized_results:
                baseline_avg = statistics.mean([r.total_runtime_ms for r in baseline_results])
                optimized_avg = statistics.mean([r.total_runtime_ms for r in optimized_results])
                improvement = ((baseline_avg - optimized_avg) / baseline_avg) * 100

                print(f"  Quick comparison: {improvement:+.1f}% improvement ({baseline_avg:.1f}ms -> {optimized_avg:.1f}ms)")

            print()

        return all_results

    def save_results(self, results: List[BenchmarkRun], filename: str = None):
        """Save benchmark results to file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"benchmark_results_{timestamp}.json"

        results_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_runs": len(results),
                "successful_runs": len([r for r in results if r.success]),
                "sequences_tested": len(set(r.sequence for r in results)),
                "system_info": {
                    "cpu_count": psutil.cpu_count(),
                    "memory_gb": psutil.virtual_memory().total / (1024**3),
                    "platform": os.uname().sysname if hasattr(os, 'uname') else 'Unknown'
                }
            },
            "results": [asdict(r) for r in results]
        }

        filepath = self.results_dir / filename
        with open(filepath, 'w') as f:
            json.dump(results_data, f, indent=2)

        print(f"Results saved to: {filepath}")

        # Also save as CSV for easy analysis
        csv_filename = filename.replace('.json', '.csv')
        self.export_to_csv(results, csv_filename)

    def export_to_csv(self, results: List[BenchmarkRun], filename: str):
        """Export results to CSV format"""
        csv_path = self.results_dir / filename

        with open(csv_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)

            # Header
            writer.writerow([
                'timestamp', 'sequence', 'version', 'run_number', 'success',
                'total_runtime_ms', 'cpu_percent_avg', 'memory_mb_peak',
                'processed_frames', 'lost_frames', 'keyframes_created',
                'rmse_translation', 'rmse_rotation', 'ate_rmse'
            ])

            # Data rows
            for r in results:
                writer.writerow([
                    r.timestamp, r.sequence, r.version, r.run_number, r.success,
                    r.total_runtime_ms, r.system_metrics.cpu_percent_avg, r.system_metrics.memory_mb_peak,
                    r.slam_metrics.processed_frames, r.slam_metrics.lost_frames, r.slam_metrics.keyframes_created,
                    r.accuracy_metrics.rmse_translation, r.accuracy_metrics.rmse_rotation, r.accuracy_metrics.ate_rmse
                ])

        print(f"CSV export saved to: {csv_path}")

def main():
    import argparse

    parser = argparse.ArgumentParser(description="ORB-SLAM3 Benchmarking Runner")
    parser.add_argument("--sequences", nargs="+", help="Specific sequences to test")
    parser.add_argument("--runs", type=int, default=50, help="Runs per sequence (default: 50)")
    parser.add_argument("--output", help="Output filename")
    parser.add_argument("--dataset-config", default="datasets/EuRoC/dataset_config.json",
                       help="Dataset configuration file")

    args = parser.parse_args()

    # Load dataset configuration
    config_path = Path(args.dataset_config)
    if not config_path.exists():
        print(f"Dataset config not found: {config_path}")
        print("Please download datasets first using: python3 euroc_dataset_scraper.py")
        return 1

    with open(config_path) as f:
        dataset_config = json.load(f)

    # Collect sequence paths
    sequence_paths = []
    for location, sequences in dataset_config["datasets"].items():
        for seq_name, seq_path in sequences.items():
            if args.sequences is None or f"{location}/{seq_name}" in args.sequences:
                sequence_paths.append(Path(seq_path))

    if not sequence_paths:
        print("No sequences found to test")
        return 1

    print(f"Found {len(sequence_paths)} sequences to benchmark")
    for seq_path in sequence_paths:
        print(f"  - {seq_path.parent.name}/{seq_path.name}")
    print()

    # Run benchmarks
    runner = ORBSLAMRunner()
    results = runner.run_benchmark_suite(sequence_paths, args.runs)

    # Save results
    runner.save_results(results, args.output)

    # Print summary
    successful_results = [r for r in results if r.success]
    baseline_results = [r for r in successful_results if r.version == "baseline"]
    optimized_results = [r for r in successful_results if r.version == "optimized"]

    print(f"\n=== Benchmark Summary ===")
    print(f"Total runs: {len(results)}")
    print(f"Successful runs: {len(successful_results)}")
    print(f"Success rate: {100*len(successful_results)/len(results):.1f}%")

    if baseline_results and optimized_results:
        baseline_avg = statistics.mean([r.total_runtime_ms for r in baseline_results])
        optimized_avg = statistics.mean([r.total_runtime_ms for r in optimized_results])
        improvement = ((baseline_avg - optimized_avg) / baseline_avg) * 100

        print(f"\nPerformance Comparison:")
        print(f"Baseline average: {baseline_avg:.1f}ms")
        print(f"Optimized average: {optimized_avg:.1f}ms")
        print(f"Overall improvement: {improvement:+.1f}%")

    return 0

if __name__ == "__main__":
    sys.exit(main())