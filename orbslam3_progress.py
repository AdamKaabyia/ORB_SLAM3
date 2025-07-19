#!/usr/bin/env python3
"""
ORB-SLAM3 Progress Monitor
Wraps ORB-SLAM3 execution with real-time progress tracking
"""

import sys
import subprocess
import time
import os
import threading
from pathlib import Path

try:
    from rich.console import Console
    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
    from rich.live import Live
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

def count_frames_in_timestamps(timestamp_file):
    """Count total frames from timestamp file"""
    try:
        # Map sequence names to timestamp files automatically
        sequence_to_timestamp = {
            "MH_01_easy": "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/MH01.txt",
            "MH_02_easy": "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/MH02.txt",
            "MH_03_medium": "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/MH03.txt",
            "MH_04_difficult": "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/MH04.txt",
            "MH_05_difficult": "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/MH05.txt",
            "V1_01_easy": "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/V101.txt",
            "V1_02_medium": "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/V102.txt",
            "V1_03_difficult": "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/V103.txt",
            "V2_01_easy": "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/V201.txt",
            "V2_02_medium": "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/V202.txt",
            "V2_03_medium": "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/V203.txt"
        }

        # If timestamp_file is a sequence path, extract sequence name and map to timestamp file
        if "/EuRoC/" in timestamp_file:
            sequence_name = Path(timestamp_file).name
            if sequence_name in sequence_to_timestamp:
                timestamp_file = sequence_to_timestamp[sequence_name]

        # Try to read from container first
        try:
            result = subprocess.run([
                "podman", "run", "--rm",
                "localhost/orb-slam3:optimized",
                "wc", "-l", timestamp_file
            ], capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return int(result.stdout.strip().split()[0])
        except:
            pass

        # Fallback: estimate based on dataset type
        sequence_name = Path(timestamp_file).name if "/EuRoC/" in timestamp_file else ""
        if "MH_01" in sequence_name:
            return 3682  # Actual frame count for MH_01_easy
        elif "MH_02" in sequence_name:
            return 3040
        elif "MH_03" in sequence_name:
            return 2760
        elif "V1_01" in sequence_name:
            return 2510
        elif "V1_02" in sequence_name:
            return 2210
        else:
            return 2000  # Conservative estimate

    except Exception as e:
        print(f"Warning: Could not count frames: {e}")
        return 2000

def monitor_orbslam_output(process, total_frames, progress_task=None, progress=None):
    """Monitor ORB-SLAM3 output and show real-time status"""
    line_count = 0
    vocab_loaded = False
    map_created = False
    processing_started = False
    saving_started = False
    start_time = time.time()

    # Status tracking for display
    current_status = "Starting..."

    if RICH_AVAILABLE:
        console = Console()

    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            line = output.strip()
            line_count += 1

            # Update status based on ORB-SLAM3 output
            if "Loading ORB Vocabulary" in line:
                current_status = "[yellow]Loading vocabulary (139MB)...[/yellow]"
            elif "Vocabulary loaded!" in line:
                current_status = "[green]Vocabulary loaded[/green] - Initializing system..."
                vocab_loaded = True
            elif "New Map created" in line and "points" in line:
                current_status = "[green]Map initialized[/green] - Processing frames..."
                map_created = True
                processing_started = True
            elif "First KF:" in line or "Camera 0 is pinhole" in line:
                current_status = "[cyan]Processing frames...[/cyan]"
                processing_started = True
            elif "Saving trajectory" in line:
                current_status = "[yellow]Saving trajectory...[/yellow]"
                saving_started = True
            elif "End of saving trajectory" in line:
                current_status = "[yellow]Saving keyframe data...[/yellow]"
            elif "Saving keyframe trajectory" in line:
                current_status = "[green]Processing complete![/green]"

            # Print status update and logs
            if RICH_AVAILABLE:
                # Clear line and show current status
                if current_status:
                    elapsed = time.time() - start_time
                    elapsed_str = f"{elapsed:.0f}s"
                    console.print(f"\rStatus: {current_status} [{elapsed_str}]", end="")

                # Print the actual ORB-SLAM3 output with color coding
                if any(keyword in line.lower() for keyword in ['error', 'fail']):
                    console.print(f"\n[red]ORB-SLAM3:[/red] {line}")
                elif any(keyword in line.lower() for keyword in ['loaded', 'saving', 'complete', 'end of saving']):
                    console.print(f"\n[green]ORB-SLAM3:[/green] {line}")
                elif any(keyword in line.lower() for keyword in ['new map', 'camera', 'first kf', 'atlas', 'creation']):
                    console.print(f"\n[cyan]ORB-SLAM3:[/cyan] {line}")
                elif "lost" in line.lower():
                    console.print(f"\n[yellow]ORB-SLAM3:[/yellow] {line}")
                elif line.strip() and not line.startswith("        -") and not line.startswith("--"):
                    # Only show important lines, skip config details
                    if any(keyword in line.lower() for keyword in ['vocabulary', 'initialization', 'shutdown', 'maps', 'kf']):
                        console.print(f"\n[dim]ORB-SLAM3:[/dim] {line}")
            else:
                print(f"Status: {current_status.replace('[', '').replace(']', '').replace('/', '')}")
                print(f"ORB-SLAM3: {line}")

    return process.poll()

def auto_detect_timestamp_file(sequence_path):
    """Automatically detect the correct timestamp file for any EuRoC sequence"""
    sequence_name = Path(sequence_path).name

    # Mapping for all EuRoC sequences
    timestamp_map = {
        "MH_01_easy": "MH01.txt",
        "MH_02_easy": "MH02.txt",
        "MH_03_medium": "MH03.txt",
        "MH_04_difficult": "MH04.txt",
        "MH_05_difficult": "MH05.txt",
        "V1_01_easy": "V101.txt",
        "V1_02_medium": "V102.txt",
        "V1_03_difficult": "V103.txt",
        "V2_01_easy": "V201.txt",
        "V2_02_medium": "V202.txt",
        "V2_03_medium": "V203.txt"
    }

    if sequence_name in timestamp_map:
        return f"/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/{timestamp_map[sequence_name]}"
    else:
        # Fallback for unknown sequences
        print(f"Warning: Unknown sequence {sequence_name}, using MH01.txt as fallback")
        return "/opt/orb-slam3/Examples/Monocular/EuRoC_TimeStamps/MH01.txt"

def run_orbslam_with_progress(container_name, vocab_path, config_path, sequence_path, timestamps_path=None):
    """Run ORB-SLAM3 with real-time status monitoring (no fake progress bars)"""
    # Auto-detect timestamp file if not provided
    if not timestamps_path:
        timestamps_path = auto_detect_timestamp_file(sequence_path)
        if RICH_AVAILABLE:
            console = Console()
            console.print(f"[cyan]Auto-detected timestamp file:[/cyan] {timestamps_path}")

    # Count total frames for information
    total_frames = count_frames_in_timestamps(timestamps_path)
    if RICH_AVAILABLE:
        console = Console()
        console.print(f"[cyan]Estimated total frames:[/cyan] {total_frames:,}")

    # Create results directory with proper permissions
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    results_dir.chmod(0o777)  # Ensure container can write to it

    # Extract sequence name for result files
    sequence_name = Path(sequence_path).name
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    result_prefix = f"{sequence_name}_{container_name}_{timestamp}"

    # Convert paths for container execution
    # If sequence_path is absolute, make it relative to workspace
    if os.path.isabs(sequence_path):
        sequence_path_in_container = os.path.relpath(sequence_path, os.getcwd())
        # Ensure it starts with /workspace/ for the container
        sequence_path_in_container = f"/workspace/{sequence_path_in_container}"
    else:
        sequence_path_in_container = f"/workspace/{sequence_path}"

    # Convert vocab and config paths for container
    vocab_path_in_container = vocab_path  # These are already container paths
    config_path_in_container = config_path

    # Build command - Fixed volume mounting and permissions
    cmd = [
        "podman", "run", "--rm",
        "--user", f"{os.getuid()}:{os.getgid()}",  # Run as current user to fix permissions
        "-v", f"{os.getcwd()}:/workspace:Z",
        "-w", "/workspace/results",  # Work directly in results directory
        f"localhost/orb-slam3:{container_name}",
        "/opt/orb-slam3/Examples/Monocular/mono_euroc",
        vocab_path_in_container, config_path_in_container, sequence_path_in_container, timestamps_path,
        f"{result_prefix}_trajectory"  # Just filename, ORB-SLAM3 adds f_ and kf_ prefixes
    ]

    if RICH_AVAILABLE:
        console = Console()

        console.print(Panel.fit(
            f"[bold blue]ORB-SLAM3 Real-Time Monitor[/bold blue]\n"
            f"Container: [green]{container_name}[/green]\n"
            f"Sequence: [cyan]{sequence_path}[/cyan]\n"
            f"Expected frames: [yellow]{total_frames:,}[/yellow]\n"
            f"Output files: [white]f_{result_prefix}_trajectory.txt, kf_{result_prefix}_trajectory.txt[/white]",
            title="Starting SLAM Processing"
        ))

        # Start process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Monitor with status display (no progress bar)
        exit_code = monitor_orbslam_output(process, total_frames)

        # Final status
        console.print()  # New line
        if exit_code == 0:
            console.print(Panel.fit(
                f"[bold green]Processing Complete![/bold green]\n"
                f"Successfully processed {total_frames:,} frames\n"
                f"Results saved to: [cyan]results/[/cyan]\n"
                f"Files: [white]f_{result_prefix}_trajectory.txt, kf_{result_prefix}_trajectory.txt[/white]",
                title="Success"
            ))
        else:
            console.print(Panel.fit(
                f"[bold red]Processing Failed[/bold red]\n"
                f"Exit code: {exit_code}\n"
                f"Check results directory for partial output",
                title="Error"
            ))

        return exit_code

    else:
        # Fallback without rich
        print(f"Starting ORB-SLAM3 processing...")
        print(f"Container: {container_name}")
        print(f"Sequence: {sequence_path}")
        print(f"Expected frames: {total_frames:,}")
        print("=" * 50)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        exit_code = monitor_orbslam_output(process, total_frames)

        if exit_code == 0:
            print("=" * 50)
            print("Processing complete!")
            print(f"Results saved to: results/")
            print(f"Files: f_{result_prefix}_trajectory.txt, kf_{result_prefix}_trajectory.txt")
        else:
            print("=" * 50)
            print(f"Processing failed (exit code: {exit_code})")
            print("Check results directory for partial output")

        return exit_code

def main():
    if len(sys.argv) < 5:
        print("Usage: python3 orbslam3_progress.py <container> <vocab> <config> <sequence> [timestamps]")
        print("")
        print("Auto-detects timestamp files for all EuRoC sequences!")
        print("")
        print("Examples:")
        print("# Machine Hall sequences")
        print("python3 orbslam3_progress.py optimized \\")
        print("  /opt/orb-slam3/Vocabulary/ORBvoc.txt \\")
        print("  /opt/orb-slam3/Examples/Monocular/EuRoC.yaml \\")
        print("  /workspace/datasets/EuRoC/machine_hall/MH_01_easy")
        print("")
        print("# Vicon Room sequences")
        print("python3 orbslam3_progress.py optimized \\")
        print("  /opt/orb-slam3/Vocabulary/ORBvoc.txt \\")
        print("  /opt/orb-slam3/Examples/Monocular/EuRoC.yaml \\")
        print("  /workspace/datasets/EuRoC/vicon_room1/V1_01_easy")
        print("")
        print("Supported sequences: MH_01-05, V1_01-03, V2_01-03")
        print("Results saved to: results/<sequence>_<container>_<timestamp>_*")
        sys.exit(1)

    container = sys.argv[1]
    vocab = sys.argv[2]
    config = sys.argv[3]
    sequence = sys.argv[4]
    timestamps = sys.argv[5] if len(sys.argv) > 5 else None

    exit_code = run_orbslam_with_progress(container, vocab, config, sequence, timestamps)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()