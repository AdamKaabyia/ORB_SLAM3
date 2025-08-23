#!/usr/bin/env python3
"""
ORB-SLAM3 Version Comparator
Runs and compares: upstream (baseline container), optimized (container), and local (host build if available).

Usage examples:
  python3 compare_versions.py                            # Compare all EuRoC sequences once
  python3 compare_versions.py --runs 5                   # Repeat each version 5x per sequence
  python3 compare_versions.py --sequences MH_01_easy V1_01_easy

  # Compare specific git refs of upstream in separate containers (Alpine-based):
  ORBSLAM_REF=v1.0 python3 cross-platform-dev.py build-upstream
  podman tag localhost/orb-slam3:upstream localhost/orb-slam3:upstream-v1.0
  ORBSLAM_REF=some-branch python3 cross-platform-dev.py build-upstream
  podman tag localhost/orb-slam3:upstream localhost/orb-slam3:upstream-some-branch

  # Then compare those tags by overriding version list below (see --versions)

Outputs:
  - Prints a per-sequence timing summary (ms) for each version
  - Saves JSON summary to benchmark_results/compare_results_<timestamp>.json
"""

import argparse
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class VersionTiming:
    version: str
    success: bool
    runtime_ms: float
    exit_code: int
    log_path: Optional[str]


@dataclass
class SequenceComparison:
    location: str
    sequence: str
    dataset_path: str
    timings: List[VersionTiming]


def format_version_label(version_tag: str) -> str:
    """Return a human-friendly label for a version tag.

    We present the optimized container as "our local version" to distinguish it
    from upstream refs while avoiding confusion with the host-built 'local'.
    """
    if version_tag == "optimized":
        return "our local version"
    return version_tag


def load_dataset_sequences(dataset_config_path: Path, filter_sequences: Optional[List[str]]) -> List[Path]:
    if not dataset_config_path.exists():
        raise FileNotFoundError(
            f"Dataset config not found: {dataset_config_path}. Run: python3 euroc_dataset_scraper.py"
        )
    with open(dataset_config_path) as f:
        cfg = json.load(f)

    seq_paths: List[Path] = []
    for location, sequences in cfg.get("datasets", {}).items():
        for seq_name, seq_path in sequences.items():
            if (not filter_sequences) or (f"{location}/{seq_name}" in filter_sequences) or (seq_name in filter_sequences):
                seq_paths.append(Path(seq_path))
    return seq_paths


def run_container_version(container_tag: str, sequence_path: Path, stream: bool = True, save_logs: bool = True) -> VersionTiming:
    """Run ORB-SLAM3 inside a container via orbslam3_progress.py and time it.

    When stream=True, the child output is streamed live to our stdout (and optionally saved).
    """
    start = time.time()
    cmd = [
        "python3",
        "orbslam3_progress.py",
        container_tag,
        "/opt/orb-slam3/Vocabulary/ORBvoc.txt",
        "/opt/orb-slam3/Examples/Monocular/EuRoC.yaml",
        str(sequence_path),
    ]

    logs_dir = Path("benchmark_results")
    logs_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_tag = container_tag.replace(":", "_")
    log_path = logs_dir / f"compare_{safe_tag}_{sequence_path.name}_{ts}.log"

    try:
        if stream:
            # Stream output live and optionally tee to file
            log_fh = open(log_path, "w") if save_logs else None
            try:
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=os.environ.copy())
                for line in process.stdout:  # type: ignore[attr-defined]
                    print(line, end="")
                    if log_fh:
                        log_fh.write(line)
                process.wait()
                ret = process.returncode
            finally:
                if log_fh:
                    log_fh.flush()
                    log_fh.close()
            runtime_ms = (time.time() - start) * 1000.0
            return VersionTiming(container_tag, ret == 0, runtime_ms, ret, str(log_path) if save_logs else None)
        else:
            proc = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
            runtime_ms = (time.time() - start) * 1000.0
            if save_logs:
                with open(log_path, "w") as f:
                    f.write(proc.stdout or "")
                    if proc.stderr:
                        f.write("\n--- STDERR ---\n")
                        f.write(proc.stderr)
            return VersionTiming(container_tag, proc.returncode == 0, runtime_ms, proc.returncode, str(log_path) if save_logs else None)
    except Exception:
        runtime_ms = (time.time() - start) * 1000.0
        return VersionTiming(container_tag, False, runtime_ms, -1, str(log_path) if save_logs else None)


def run_local_version(local_binary: Path, sequence_path: Path) -> VersionTiming:
    """Run host-built mono_euroc if available. Uses host paths for vocab/config/timestamps."""
    if not local_binary.exists():
        return VersionTiming("local", False, 0.0, -1, None)

    vocab = Path("./Vocabulary/ORBvoc.txt")
    config = Path("./Examples/Monocular/EuRoC.yaml")
    timestamps = sequence_path / "mav0/cam0/data.csv"

    if not vocab.exists() or not config.exists() or not timestamps.exists():
        return VersionTiming("local", False, 0.0, -1, None)

    start = time.time()
    cmd = [
        str(local_binary),
        str(vocab),
        str(config),
        str(sequence_path),
        str(timestamps),
        # Let the binary decide default output name in current directory
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(Path.cwd()))
        runtime_ms = (time.time() - start) * 1000.0
        success = proc.returncode == 0
        logs_dir = Path("benchmark_results")
        logs_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = logs_dir / f"compare_local_{sequence_path.name}_{ts}.log"
        with open(log_file, "w") as f:
            f.write(proc.stdout or "")
            if proc.stderr:
                f.write("\n--- STDERR ---\n")
                f.write(proc.stderr)
        return VersionTiming("local", success, runtime_ms, proc.returncode, str(log_file))
    except Exception:
        runtime_ms = (time.time() - start) * 1000.0
        return VersionTiming("local", False, runtime_ms, -1, None)


def print_summary(comparisons: List[SequenceComparison]):
    # Compute column widths
    headers = ["Sequence", "Version", "Runtime (ms)", "Success"]
    print("\nComparison Summary")
    print("-" * 80)
    print(" | ".join(headers))
    print("-" * 80)
    for comp in comparisons:
        for t in comp.timings:
            row = [
                f"{comp.location}/{comp.sequence}",
                t.version,
                f"{t.runtime_ms:.1f}",
                "yes" if t.success else "no",
            ]
            print(" | ".join(row))
    print("-" * 80)


def main():
    parser = argparse.ArgumentParser(description="Compare ORB-SLAM3 versions (containers and optional local)")
    parser.add_argument("--sequences", nargs="+", help="Subset of sequences (e.g., MH_01_easy V1_01_easy)")
    parser.add_argument("--runs", type=int, default=1, help="Runs per version per sequence")
    parser.add_argument("--dataset-config", default="datasets/EuRoC/dataset_config.json",
                        help="Dataset configuration file")
    parser.add_argument("--include-local", action="store_true", help="Also try a local host build if available")
    parser.add_argument("--versions", nargs="+", default=["upstream", "optimized"],
                        help="Container versions/tags to compare (e.g., upstream optimized upstream-v1.0 upstream-some-branch)")
    parser.add_argument("--no-stream", action="store_true", help="Disable live log streaming (capture to file only)")
    parser.add_argument("--no-save-logs", action="store_true", help="Do not save per-run logs to benchmark_results/")
    parser.add_argument("--export-dashboard", metavar="OUT_JSON", help="Also export a dashboard-compatible JSON from trajectory files")
    parser.add_argument("--auto-dashboard", action="store_true", help="After export, show dashboard summary (non-interactive)")
    args = parser.parse_args()

    dataset_config_path = Path(args.dataset_config)
    all_seq_paths = load_dataset_sequences(dataset_config_path, args.sequences)
    if not all_seq_paths:
        print("No sequences selected/found. Aborting.")
        return 1

    # Resolve local binary path
    local_binary = Path("./build/Examples/Monocular/mono_euroc")

    comparisons: List[SequenceComparison] = []
    for seq_path in all_seq_paths:
        location = seq_path.parent.name
        sequence = seq_path.name
        timings: List[VersionTiming] = []

        # Run specified container versions (tags)
        for version in args.versions:
            print(f"\n=== Running {version} on {location}/{sequence} (runs={args.runs}) ===")
            # Repeat N times and take mean
            run_timings: List[VersionTiming] = []
            for _ in range(args.runs):
                run_timings.append(run_container_version(version, seq_path, stream=(not args.no_stream), save_logs=(not args.no_save_logs)))
            # Aggregate
            successes = [t for t in run_timings if t.success]
            avg_ms = sum(t.runtime_ms for t in run_timings) / max(len(run_timings), 1)
            display_label = format_version_label(version)
            timings.append(VersionTiming(display_label, bool(successes), avg_ms, run_timings[-1].exit_code, run_timings[-1].log_path))

        # Optional local comparison
        if args.include_local:
            run_timings_local: List[VersionTiming] = []
            for _ in range(args.runs):
                run_timings_local.append(run_local_version(local_binary, seq_path))
            successes_local = [t for t in run_timings_local if t.success]
            avg_ms_local = sum(t.runtime_ms for t in run_timings_local) / max(len(run_timings_local), 1)
            timings.append(VersionTiming("local", bool(successes_local), avg_ms_local,
                                         run_timings_local[-1].exit_code, run_timings_local[-1].log_path))

        comparisons.append(SequenceComparison(location, sequence, str(seq_path), timings))

    # Print a simple table summary
    print_summary(comparisons)

    # Save JSON
    out_dir = Path("benchmark_results")
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Create informative filename: include sequence (or 'all') and version tags (up to 3)
    def slug(s: str) -> str:
        return re.sub(r"[^A-Za-z0-9._-]+", "-", s)

    if len(comparisons) == 1:
        seq_label = f"{comparisons[0].location}_{comparisons[0].sequence}"
    else:
        seq_label = "all"

    versions_label = "__vs__".join([slug(v) for v in (args.versions or ["unknown"])])
    out_filename = f"compare_results_{slug(seq_label)}_{versions_label}_{ts}.json"
    out_path = out_dir / out_filename
    with open(out_path, "w") as f:
        json.dump({"comparisons": [asdict(c) for c in comparisons]}, f, indent=2)
    print(f"Saved comparison results to: {out_path}")

    # Optionally export a dashboard-compatible JSON using trajectory conversion
    if args.export_dashboard:
        try:
            # Use the converter to scan results/ and produce OUT_JSON
            cmd = [
                "python3", "trajectory_to_benchmark.py",
                "--output", args.export_dashboard
            ]
            print(f"Exporting dashboard JSON via trajectory conversion -> {args.export_dashboard}")
            subprocess.run(cmd, check=False)

            # Inject display labels so the dashboard can show real version names
            try:
                dashboard_path = Path(args.export_dashboard)
                with open(dashboard_path, "r") as jf:
                    data = json.load(jf)
                labels = data.get("metadata", {}).get("labels", {})
                if not labels:
                    # Prefer provided order for display
                    baseline_label_raw = args.versions[0] if args.versions else "baseline"
                    optimized_label_raw = (
                        (args.versions[1] if len(args.versions) > 1 else "optimized")
                    )
                    # Suffix to clarify roles in the dashboard
                    baseline_label = f"{baseline_label_raw} (baseline)"
                    optimized_label = f"{optimized_label_raw} (improved)"
                    data.setdefault("metadata", {})["labels"] = {
                        "baseline": baseline_label,
                        "optimized": optimized_label,
                    }
                    data["metadata"]["improvement_reference"] = baseline_label_raw
                    with open(dashboard_path, "w") as jf:
                        json.dump(data, jf, indent=2)
            except Exception as e:
                print(f"Warning: could not inject display labels: {e}")
        except Exception as e:
            print(f"Warning: dashboard export failed: {e}")

        # Optionally open dashboard summary automatically
        if args.auto_dashboard:
            try:
                dash_cmd = [
                    "python3", "results_dashboard.py",
                    "--results-file", args.export_dashboard,
                    "--no-interactive"
                ]
                subprocess.run(dash_cmd, check=False)
            except Exception as e:
                print(f"Warning: auto-dashboard failed: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


