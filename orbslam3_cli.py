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
import time
import shutil
import glob
import sys
import subprocess
import platform
import argparse
import json
import re
from pathlib import Path

class ORBSlam3CLI:
    def __init__(self):
        self.platform = platform.system()
        self.workspace = Path.cwd()
        self.common_upstream_refs = ["v0.2-beta", "v0.3-beta", "v0.4-beta", "v1.0", "master"]

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

    def build_upstream_ref(self, ref: str, tag: str = None) -> bool:
        """Build upstream container for a given ref and tag it as upstream-<ref> (or provided tag)."""
        runtime = self.detect_container_runtime()
        if not runtime:
            print("[ERROR] No container runtime found. Please install Docker or Podman.")
            return False

        env = os.environ.copy()
        env["ORBSLAM_REF"] = ref
        print(f"[INFO] Building upstream ref: {ref}")
        result = subprocess.run("python3 cross-platform-dev.py build-upstream", shell=True, env=env)
        if result.returncode != 0:
            print(f"[ERROR] Failed to build upstream ref {ref}")
            return False

        version_tag = tag if tag else f"upstream-{ref}"
        tag_cmd = f"{runtime} tag localhost/orb-slam3:upstream localhost/orb-slam3:{version_tag}"
        tag_res = subprocess.run(tag_cmd, shell=True)
        if tag_res.returncode != 0:
            print(f"[ERROR] Failed to tag image as {version_tag}")
            return False
        print(f"[SUCCESS] Built and tagged: {version_tag}")
        return True

    def validate_git_ref(self, repo_url: str, ref: str) -> bool:
        """Validate that a given ref exists in the remote repo (heads or tags)."""
        try:
            # Try exact ref; if empty, try as heads/tags explicitly
            res = subprocess.run([
                "git", "ls-remote", "--heads", "--tags", repo_url, ref
            ], capture_output=True, text=True)
            return res.returncode == 0 and bool(res.stdout.strip())
        except Exception:
            return False

    def _sanitize_tag(self, value: str) -> str:
        """Sanitize a string to be a safe container tag component."""
        safe = re.sub(r"[^a-zA-Z0-9_.-]", "-", value)
        return safe.strip("-._") or "custom"

    def build_custom_upstream(self, repo_url: str, ref: str, tag: str = None) -> tuple:
        """Build using a custom upstream repo+ref. Returns (success, tag_name)."""
        runtime = self.detect_container_runtime()
        if not runtime:
            print("[ERROR] No container runtime found. Please install Docker or Podman.")
            return False, None

        if not self.validate_git_ref(repo_url, ref):
            print(f"[ERROR] Ref '{ref}' not found in repo {repo_url}")
            return False, None

        env = os.environ.copy()
        env["ORBSLAM_REPO"] = repo_url
        env["ORBSLAM_REF"] = ref
        print(f"[INFO] Building custom upstream: repo={repo_url}, ref={ref}")
        result = subprocess.run("python3 cross-platform-dev.py build-upstream", shell=True, env=env)
        if result.returncode != 0:
            print("[ERROR] Failed to build custom upstream")
            return False, None

        repo_base = os.path.splitext(os.path.basename(repo_url.rstrip("/")))[0]
        auto_tag = tag or f"upstream-{self._sanitize_tag(repo_base)}-{self._sanitize_tag(ref)}"
        tag_cmd = f"{runtime} tag localhost/orb-slam3:upstream localhost/orb-slam3:{auto_tag}"
        tag_res = subprocess.run(tag_cmd, shell=True)
        if tag_res.returncode != 0:
            print(f"[ERROR] Failed to tag image as {auto_tag}")
            return False, None
        print(f"[SUCCESS] Built and tagged: {auto_tag}")
        return True, auto_tag

    def compare_upstream_build_and_run(self):
        """Interactive: build two upstream refs and run comparison end-to-end."""
        print("\n[COMPARE UPSTREAM VERSIONS - BUILD & RUN]")
        print("Pick from common upstream refs or choose Other:")
        for i, r in enumerate(self.common_upstream_refs, start=1):
            print(f"  {i}. {r}")
        print(f"  {len(self.common_upstream_refs)+1}. Other (enter manually or repo@ref)")

        def pick_ref(label: str, default_idx: int) -> tuple:
            choice = input(f"Select {label} [{default_idx}] ").strip()
            if not choice:
                return ("ref", self.common_upstream_refs[default_idx-1])
            if choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(self.common_upstream_refs):
                    return ("ref", self.common_upstream_refs[idx-1])
                elif idx == len(self.common_upstream_refs)+1:
                    # Other
                    value = input("Enter upstream ref or repo@ref: ").strip()
                    if "@" in value and (value.startswith("http") or value.endswith(".git")):
                        repo, ref = value.split("@", 1)
                        return ("custom", (repo, ref))
                    return ("ref", value or "master")
            # Fallback: treat as ref text
            return ("ref", choice)

        kind_a, val_a = pick_ref("first ref", default_idx=4)  # default v1.0
        kind_b, val_b = pick_ref("second ref", default_idx=5) # default master

        # Optional options
        seq = input("Sequence (default MH_01_easy, or 'all'): ").strip() or "MH_01_easy"
        runs_str = input("Runs per version [1]: ").strip()
        runs = int(runs_str) if runs_str.isdigit() and int(runs_str) > 0 else 1
        export = input("Export dashboard JSON (filename or leave empty to skip): ").strip()

        # Build both refs (handle custom repo@ref case)
        if kind_a == "custom":
            ok_a, tag_a = self.build_custom_upstream(val_a[0], val_a[1])
            v_a = tag_a if ok_a else None
        else:
            ref_a = val_a
            ok_a = self.build_upstream_ref(ref_a)
            v_a = f"upstream-{ref_a}" if ok_a else None

        if kind_b == "custom":
            ok_b, tag_b = self.build_custom_upstream(val_b[0], val_b[1])
            v_b = tag_b if ok_b else None
        else:
            ref_b = val_b
            ok_b = self.build_upstream_ref(ref_b)
            v_b = f"upstream-{ref_b}" if ok_b else None
        if not (ok_a and ok_b):
            print("[ERROR] One or both upstream builds failed. Aborting compare.")
            return

        # Form versions list (already assigned above)

        # Build compare command
        cmd_parts = [
            "python3", "compare_versions.py",
            "--runs", str(runs),
            "--versions", v_a, v_b
        ]
        if seq.lower() != "all":
            cmd_parts += ["--sequences", seq]
        if export:
            cmd_parts += ["--export-dashboard", export]

        # Live streaming by default
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["RICH_FORCE_TERMINAL"] = "1"
        print("\n[INFO] Starting comparison...")
        print("Command:", " ".join(cmd_parts))
        subprocess.run(" ".join(cmd_parts), shell=True, env=env)

    def one_shot_compare(self):
        """Single interface: pick/enter versions (with validation), build if needed, compare, and show dashboard."""
        print("\n[ONE-SHOT COMPARE]")
        print("You can:\n  - Pick a preset: 1) v0.2-beta  2) v0.3-beta  3) v0.4-beta  4) v1.0  5) master\n  - Type an existing tag (e.g., optimized, upstream-v1.0)\n  - Type an upstream ref (e.g., v1.0)\n  - Enter a repo with @ref (e.g., https://github.com/UZ-SLAMLab/ORB_SLAM3.git@v1.0)")
        # Show available tags
        avail = self._list_available_versions()
        if avail:
            print("\nAvailable local image tags:")
            print("  ", ", ".join(avail))

        def read_version_input(label: str, default_value: str) -> str:
            value = input(f"{label} (default {default_value}): ").strip()
            if not value:
                return default_value
            if value.isdigit():
                idx = int(value)
                if 1 <= idx <= len(self.common_upstream_refs):
                    return f"upstream-{self.common_upstream_refs[idx-1]}"
            return value

        v1_in = read_version_input("Version A", "upstream-v1.0")
        ok1, v1 = self._parse_version_input(v1_in)
        if not ok1:
            print(f"[ERROR] Could not resolve version A: {v1_in}")
            return
        v2_in = read_version_input("Version B", "optimized")
        ok2, v2 = self._parse_version_input(v2_in)
        if not ok2:
            print(f"[ERROR] Could not resolve version B: {v2_in}")
            return
        if v1 == v2:
            print("[ERROR] Please choose two different versions.")
            return

        seq = input("Sequence (default MH_01_easy, or 'all'): ").strip() or "MH_01_easy"
        runs_str = input("Runs per version [1]: ").strip()
        runs = int(runs_str) if runs_str.isdigit() and int(runs_str) > 0 else 1

        # Ensure container tags exist
        for tag in [v1, v2]:
            if not self._ensure_or_confirm_build(tag):
                print(f"[ERROR] Version '{tag}' is not available. Aborting.")
                return

        # Build compare command
        out_json = f"compare_dashboard_{v1.replace(':','_')}_vs_{v2.replace(':','_')}.json"
        cmd = [
            "python3", "compare_versions.py",
            "--runs", str(runs),
            "--versions", v1, v2,
            "--export-dashboard", out_json
        ]
        if seq.lower() != "all":
            cmd += ["--sequences", seq]

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["RICH_FORCE_TERMINAL"] = "1"

        print("\n[INFO] Running comparison and exporting dashboard...")
        print("Command:", " ".join(cmd))
        subprocess.run(" ".join(cmd), shell=True, env=env)

        # Show dashboard
        print("\n[INFO] Rendering dashboard (non-interactive)...")
        dash_cmd = f"python3 results_dashboard.py --results-file {out_json} --no-interactive"
        subprocess.run(dash_cmd, shell=True)

    def full_one_shot_pipeline(self):
        """End-to-end: ensure datasets, build images as needed, compare, export HTML dashboard, print path."""
        print("\n[ONE-SHOT FULL PIPELINE]")
        # 0. Optional clean removed; we now always write to a per-run results dir to avoid mixing data
        # 1. Ensure datasets present (machine_hall at least)
        euroc_dir = self.workspace / "datasets/EuRoC/machine_hall/MH_01_easy"
        if not euroc_dir.exists():
            print("Datasets missing. Downloading machine_hall sequences...")
            self.run_command("python3 euroc_dataset_scraper.py --location machine_hall", show_output=True)

        # 2. Choose versions (with presets and repo@ref supported)
        print("\nPick two versions to compare (presets: 1) v0.2-beta 2) v0.3-beta 3) v0.4-beta 4) v1.0 5) master)")
        def read_version(label, default_value):
            value = input(f"{label} (default {default_value}): ").strip()
            if not value:
                return default_value
            if value.isdigit() and 1 <= int(value) <= len(self.common_upstream_refs):
                return f"upstream-{self.common_upstream_refs[int(value)-1]}"
            ok, resolved = self._parse_version_input(value)
            if not ok or not resolved:
                print("Could not resolve input; using default.")
                return default_value
            return resolved
        v1 = read_version("Version A", "upstream-v1.0")
        v2 = read_version("Version B", "optimized")
        if v1 == v2:
            print("Selected the same version twice; changing Version B to 'optimized'.")
            v2 = "optimized"

        # 3. Confirm build if images are missing
        for tag in [v1, v2]:
            if not self._ensure_or_confirm_build(tag):
                print(f"[ERROR] Image '{tag}' unavailable. Aborting.")
                return

        # 4. Run compare with auto-dashboard and export HTML
        out_json = f"compare_dashboard_{v1.replace(':','_')}_vs_{v2.replace(':','_')}.json"
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["RICH_FORCE_TERMINAL"] = "1"
        # Use dedicated results dir for clean aggregation
        results_dir = self.workspace / f"results_run_{int(time.time())}"
        results_dir.mkdir(exist_ok=True)
        env["RESULTS_DIR"] = str(results_dir)
        cmd = (
            f"python3 compare_versions.py --runs 1 --sequences MH_01_easy --versions {v1} {v2} "
            f"--export-dashboard {out_json} --auto-dashboard"
        )
        print("\n[INFO] Running compare...")
        print("Command:", cmd)
        if subprocess.run(cmd, shell=True, env=env).returncode != 0:
            print("[ERROR] Compare failed.")
            return

        # 5. Export HTML
        out_html = self.workspace / f"dashboard_{v1.replace(':','_')}_vs_{v2.replace(':','_')}.html"
        dash_cmd = f"python3 results_dashboard.py --results-file {out_json} --export-html {out_html} --no-interactive"
        if subprocess.run(dash_cmd, shell=True).returncode == 0:
            print(f"\n[SUCCESS] HTML dashboard: {out_html}")
        else:
            print("[ERROR] HTML export failed.")

    def prepare_github_pages(self):
        """Collect latest HTML dashboards and JSON into docs/ for GitHub Pages."""
        print("\n[EXPORT GITHUB PAGES]")
        docs = self.workspace / "docs"
        docs.mkdir(exist_ok=True)
        # Copy dashboards and their JSONs
        dashboards = list(self.workspace.glob("dashboard_*.html"))
        jsons = list(self.workspace.glob("compare_dashboard_*.json"))
        if not dashboards and not jsons:
            print("No dashboards or JSON results found. Create them via one-shot/full pipeline first.")
            return
        for d in dashboards:
            shutil.copy2(d, docs / d.name)
        for j in jsons:
            shutil.copy2(j, docs / j.name)
        # Auto-generate HTML for any JSON that lacks an HTML counterpart in docs/
        generated = 0
        for j in sorted(docs.glob("compare_dashboard_*.json")):
            expected_html = docs / ("dashboard_" + j.name.replace("compare_dashboard_", "").replace(".json", ".html"))
            if not expected_html.exists():
                try:
                    cmd = f"python3 results_dashboard.py --results-file {j} --export-html {expected_html} --no-interactive"
                    subprocess.run(cmd, shell=True, check=False)
                    if expected_html.exists():
                        generated += 1
                except Exception:
                    pass
        # Ensure Jekyll is disabled so Liquid doesn't parse content
        (docs / ".nojekyll").write_text("")

        # Build items by reading JSON metadata
        items = []
        for j in sorted(docs.glob("compare_dashboard_*.json")):
            try:
                with open(j, "r") as fh:
                    data = json.load(fh)
                meta = data.get("metadata", {})
                labels = meta.get("labels", {})
                ts = meta.get("timestamp", "")
                base = labels.get("baseline", "Baseline")
                opt = labels.get("optimized", "Optimized")
                total = meta.get("total_runs", 0)
                succ = meta.get("successful_runs", 0)
                html_name = "dashboard_" + j.name.replace("compare_dashboard_", "").replace(".json", ".html")
                html_exists = (docs / html_name).exists()
                items.append({
                    "json": j.name,
                    "html": html_name if html_exists else "",
                    "timestamp": ts,
                    "baseline": base,
                    "optimized": opt,
                    "runs": f"{succ}/{total}"
                })
            except Exception:
                continue

        # Create richer index
        index = docs / "index.html"
        rows = []
        for it in items:
            link_html = f"<a href='{it['html']}'>Open</a>" if it["html"] else "(missing html)"
            link_json = f"<a href='{it['json']}'>JSON</a>"
            rows.append(f"<tr><td>{it['timestamp']}</td><td>{it['baseline']}</td><td>{it['optimized']}</td><td>{it['runs']}</td><td>{link_html} | {link_json}</td></tr>")
        table = """
<!doctype html>
<meta charset='utf-8'>
<title>ORB-SLAM3 Reports</title>
<style>
 body{font-family:system-ui,Arial,sans-serif;margin:24px}
 table{border-collapse:collapse;width:100%}
 th,td{border:1px solid #ddd;padding:8px}
 th{background:#f5f5f5;text-align:left}
 .hint{color:#666;margin:8px 0}
</style>
<h1>ORB-SLAM3 Comparison Runs</h1>
<div class='hint'>This index is auto-generated. Click a row's HTML link to view the full dashboard.</div>
<table>
  <thead><tr><th>Timestamp</th><th>Baseline</th><th>Improved</th><th>Runs</th><th>Links</th></tr></thead>
  <tbody>
    REPLACE_ROWS
  </tbody>
</table>
""".replace("REPLACE_ROWS", "\n".join(rows))
        index.write_text(table)
        print(f"Prepared {len(dashboards)} dashboards and {len(jsons)} JSONs in {docs} (generated {generated} HTML). Open docs/index.html. Push to publish.")

    def _detect_runtime_and_images(self):
        """Return (runtime, images_json) where images_json is a list of dicts for orb-slam3 images"""
        runtime = self.detect_container_runtime()
        if not runtime:
            print("[ERROR] No container runtime found. Please install Docker or Podman.")
            return None, []

        try:
            result = subprocess.run([runtime, "images", "--format", "json"],
                                    capture_output=True, text=True)
            images = json.loads(result.stdout or "[]")
        except Exception:
            images = []

        orb_images = []
        for img in images:
            names = img.get("Names") or []
            for name in names:
                if "orb-slam3:" in name:
                    orb_images.append({"name": name, **img})
        return runtime, orb_images

    def _list_available_versions(self) -> list:
        """List available container version tags plus optional 'local' if host binary exists."""
        _, orb_images = self._detect_runtime_and_images()
        tags = []
        for img in orb_images:
            # Names entries look like 'localhost/orb-slam3:optimized'
            for name in img.get("Names", []):
                if ":" in name:
                    tag = name.split(":", 1)[1]
                    if tag not in tags:
                        tags.append(tag)
        # Prefer to show stable/common first if available
        ordered = []
        for preferred in ["optimized", "upstream"]:
            if preferred in tags:
                ordered.append(preferred)
        ordered += [t for t in tags if t not in ordered]

        # Add 'local' option if host binary exists
        local_bin = self.workspace / "build/Examples/Monocular/mono_euroc"
        if local_bin.exists():
            ordered.append("local")
        return ordered

    def _ensure_container_tag(self, desired_tag: str) -> bool:
        """Ensure a given container tag exists; build it if it's an upstream-* alias.

        Supported patterns:
          - optimized, upstream (must already exist or be built via build command)
          - upstream-<ref> (e.g., upstream-v1.0, upstream-v0.3-beta, upstream-master)
        Returns True if available or built successfully.
        """
        runtime, orb_images = self._detect_runtime_and_images()
        if not runtime:
            return False

        # Already present?
        existing = set()
        for img in orb_images:
            for name in img.get("Names", []):
                if ":" in name:
                    existing.add(name.split(":", 1)[1])
        if desired_tag in existing:
            return True

        # Build upstream-<ref> on demand
        if desired_tag.startswith("upstream-"):
            ref = desired_tag[len("upstream-"):]
            env = os.environ.copy()
            env["ORBSLAM_REF"] = ref
            # Build upstream image (temporary tag: upstream)
            print(f"[INFO] Building upstream container for ref '{ref}'...")
            result = subprocess.run("python3 cross-platform-dev.py build-upstream", shell=True, env=env)
            if result.returncode != 0:
                print(f"[ERROR] Failed to build upstream ref {ref}")
                return False
            # Tag it to upstream-<ref>
            tag_cmd = f"{runtime} tag localhost/orb-slam3:upstream localhost/orb-slam3:{desired_tag}"
            tag_res = subprocess.run(tag_cmd, shell=True)
            if tag_res.returncode != 0:
                print(f"[ERROR] Failed to tag image as {desired_tag}")
                return False
            return True

        # Otherwise, we don't auto-build here
        print(f"[WARNING] Container tag '{desired_tag}' not found. Build it first.")
        return False

    def _parse_version_input(self, user_value: str) -> tuple:
        """Parse a version spec which may be:
        - existing container tag (optimized, upstream, upstream-<ref>, etc.)
        - 'local'
        - '<repo_url>@<ref>' or '<repo_url>' then prompt for ref
        Returns (ok, resolved_tag). If custom repo/ref, it will build and return resulting tag.
        """
        value = user_value.strip()
        # Custom repo@ref inline
        if "@" in value and (value.startswith("http://") or value.startswith("https://") or value.endswith(".git")):
            repo, ref = value.split("@", 1)
            if not self.validate_git_ref(repo, ref):
                print(f"[ERROR] Ref '{ref}' not found in repo {repo}")
                return False, None
            # Ask to build now
            if self.confirm(f"Build custom image for {repo}@{ref}?"):
                ok, tag = self.build_custom_upstream(repo, ref)
                return ok, tag
            return False, None
        # Custom repo only, prompt for ref
        if (value.startswith("http://") or value.startswith("https://") or value.endswith(".git")):
            ref = input("Enter ref to build from this repo (e.g., v1.0, master): ").strip() or "master"
            if not self.validate_git_ref(value, ref):
                print(f"[ERROR] Ref '{ref}' not found in repo {value}")
                return False, None
            if self.confirm(f"Build custom image for {value}@{ref}?"):
                ok, tag = self.build_custom_upstream(value, ref)
                return ok, tag
            return False, None
        # Local
        if value == "local":
            return True, "local"
        # Existing or upstream-<ref>
        if value.startswith("upstream-"):
            # Do not auto-build here; caller will ensure/build with confirmation
            return True, value
        # If plain ref, try upstream-<ref>
        # Resolve to upstream-<ref>, caller will decide to build
        tentative = f"upstream-{value}"
        return True, tentative
        # Fall back to checking existing tags
        available = set(self._list_available_versions())
        if value in available:
            return True, value
        return False, None

    def _ensure_or_confirm_build(self, tag: str) -> bool:
        """Ensure the given image tag exists; if missing and buildable, ask for confirmation and build."""
        if tag == "local":
            return True

        runtime, orb_images = self._detect_runtime_and_images()
        if not runtime:
            return False

        existing = set()
        for img in orb_images:
            for name in img.get("Names", []):
                if ":" in name:
                    existing.add(name.split(":", 1)[1])
        if tag in existing:
            return True

        if tag.startswith("upstream-"):
            ref = tag[len("upstream-"):]
            if self.confirm(f"Image '{tag}' not found. Build upstream ref '{ref}' now?"):
                return self._ensure_container_tag(tag)
            return False

        print(f"[WARNING] Image '{tag}' not found and cannot auto-build.")
        return False

    def build_common_versions(self):
        """Build and tag common upstream versions for comparison (Alpine-based)."""
        print("\n[BUILD COMMON VERSIONS]")
        common_refs = ["v0.2-beta", "v0.3-beta", "v0.4-beta", "v1.0", "master"]
        runtime = self.detect_container_runtime()
        if not runtime:
            print("[ERROR] No container runtime found.")
            return
        for ref in common_refs:
            env = os.environ.copy()
            env["ORBSLAM_REF"] = ref
            print(f"\n[INFO] Building upstream ref: {ref}")
            res = subprocess.run("python3 cross-platform-dev.py build-upstream", shell=True, env=env)
            if res.returncode != 0:
                print(f"[ERROR] Build failed for ref {ref}")
                continue
            # Tag as upstream-<ref>
            tag = f"upstream-{ref}"
            tag_cmd = f"{runtime} tag localhost/orb-slam3:upstream localhost/orb-slam3:{tag}"
            tag_res = subprocess.run(tag_cmd, shell=True)
            if tag_res.returncode == 0:
                print(f"[SUCCESS] Tagged as {tag}")
            else:
                print(f"[ERROR] Failed to tag image as {tag}")

    def compare_versions_interactive(self):
        """Interactive selector to compare any two versions (containers and optional local)."""
        print("\n[COMPARE VERSIONS]")
        versions = self._list_available_versions()
        if versions:
            print("Available versions (container tags):")
            for idx, v in enumerate(versions, start=1):
                print(f"  {idx}. {v}")
        else:
            print("[INFO] No local images yet. You can enter repo@ref (e.g., https://github.com/UZ-SLAMLab/ORB_SLAM3.git@v1.0)")

        def prompt_version(label: str) -> str:
            prompt = f"Select {label} by number, tag, upstream ref, or repo@ref: "
            while True:
                value = input(prompt).strip()
                if not value and versions:
                    print("Please enter a choice.")
                    continue
                # If numeric and in range, map to tag
                if value.isdigit() and versions and 1 <= int(value) <= len(versions):
                    return versions[int(value)-1]
                # Otherwise treat as free-form and try to resolve
                ok, resolved = self._parse_version_input(value)
                if ok and resolved:
                    return resolved
                print("Could not resolve that version. Try again.")

        v1 = prompt_version("version A")
        while True:
            v2 = prompt_version("version B")
            if v2 != v1:
                break
            print("Please choose a different second version.")

        # Ensure selected container tags exist (confirm before building)
        for tag in [v1, v2]:
            if not self._ensure_or_confirm_build(tag):
                print(f"[ERROR] Version '{tag}' is not available. Aborting.")
                return

        # Sequence selection
        dataset_cfg = self.workspace / "datasets/EuRoC/dataset_config.json"
        seq_options = []
        if dataset_cfg.exists():
            try:
                with open(dataset_cfg) as f:
                    data = json.load(f)
                for location, seqs in data.get("datasets", {}).items():
                    for seq_name in seqs.keys():
                        seq_options.append(f"{seq_name}")
            except Exception:
                pass
        # Fallback minimal list
        if not seq_options:
            seq_options = ["MH_01_easy", "V1_01_easy"]

        print("\nSequences (enter to accept default):")
        print("  default: MH_01_easy")
        print("  examples:", ", ".join(seq_options[:8]))
        seq_input = input("Sequence name (one), or 'all' for all available [MH_01_easy]: ").strip()
        if not seq_input:
            seq_input = "MH_01_easy"

        # Runs per version
        runs_input = input("Runs per version [1]: ").strip()
        runs = 1
        if runs_input.isdigit() and int(runs_input) > 0:
            runs = int(runs_input)

        # Build command
        include_local = False
        versions_arg = []
        for v in [v1, v2]:
            if v == "local":
                include_local = True
            else:
                versions_arg.append(v)

        cmd = ["python3", "compare_versions.py", "--runs", str(runs)]
        if seq_input.lower() != "all":
            cmd += ["--sequences", seq_input]
        if include_local:
            cmd.append("--include-local")
        if versions_arg:
            cmd += ["--versions"] + versions_arg

        # Execute
        print("\nStarting comparison...")
        self.run_command(" ".join(cmd), "Comparing selected versions")

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

    def check_existing_containers(self):
        """Check which containers already exist"""
        runtime = self.detect_container_runtime()
        if not runtime:
            return {}

        existing = {}

        # Check for upstream/baseline container
        result = subprocess.run([runtime, "images", "--format", "table"],
                              capture_output=True, text=True)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if "orb-slam3" in line and "upstream" in line:
                    existing["baseline"] = True
                elif "orb-slam3" in line and "optimized" in line:
                    existing["optimized"] = True

        return existing

    def build_containers(self):
        """Build Docker/Podman containers"""
        print("\n[CONTAINER BUILDING]")

        runtime = self.detect_container_runtime()
        if not runtime:
            print("[ERROR] No container runtime found. Please install Docker or Podman.")
            return False

        print(f"Using container runtime: {runtime}")

        # Check existing containers
        existing = self.check_existing_containers()
        if existing:
            print("\nExisting containers found:")
            for container_type, exists in existing.items():
                if exists:
                    print(f"[✓] {container_type} container already exists")

        # Ask user what to build
        build_options = [
            ("1", "baseline", "Build upstream baseline ORB-SLAM3"),
            ("2", "optimized", "Build our local version (optimized)"),
            ("3", "both", "Build both baseline and our local version"),
            ("4", "skip", "Skip building (use existing containers)")
        ]

        self.print_table(["Option", "Type", "Description"],
                        [(opt, btype, desc) for opt, btype, desc in build_options])

        # Default to skip if both containers exist
        default_choice = "4" if existing.get("baseline") and existing.get("optimized") else "3"
        choice = self.get_user_choice("Select build option", ["1", "2", "3", "4"], default_choice)

        if choice == "4":
            print("[INFO] Skipping container builds - using existing containers")
            return True

        option_map = {"1": "baseline", "2": "optimized", "3": "both"}
        build_type = option_map[choice]

        build_success = True

        if build_type in ["baseline", "both"]:
            if existing.get("baseline"):
                print("[INFO] Baseline container already exists, skipping...")
            else:
                result = self.run_command("python3 cross-platform-dev.py build-upstream",
                                        "Building baseline container")
                if result.returncode != 0:
                    print("[ERROR] Baseline container build failed!")
                    build_success = False

        if build_type in ["optimized", "both"]:
            if existing.get("optimized"):
                print("[INFO] Optimized container already exists, skipping...")
            else:
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

            cmd = f"python3 orbslam3_runner.py --runs {runs}"
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
                ("1", "status", "Show system status and check components"),
                ("2", "scrape", "Download EuRoC datasets for testing"),
                ("3", "build", "Build containers (Docker/Podman)"),
                ("4", "benchmark", "Run benchmarks and performance tests"),
                ("5", "results", "View results dashboard and analysis"),
                ("6", "dev", "Launch development environment"),
                ("7", "compare", "Compare versions (interactive picker)"),
                ("8", "compare-upstream", "Build two upstream refs and compare"),
                ("9", "build-common", "Build common upstream versions (v0.2/0.3/0.4/v1.0/master)"),
                ("10", "one-shot", "One-shot: ensure images, compare, export & show dashboard"),
                ("11", "one-shot-full", "One-shot FULL: get data, build, compare, export HTML"),
                ("12", "export-pages", "Prepare docs/ with dashboards for GitHub Pages"),
                ("0", "quit", "Exit application")
            ]

            self.print_table(["Option", "Command", "Description"],
                           [(opt, cmd, desc) for opt, cmd, desc in menu_options],
                           "Available Commands")

            choice = self.get_user_choice("Select option",
                                        [opt[0] for opt in menu_options],
                                        "1")

            # Map numbered choices to commands
            choice_map = {opt[0]: opt[1] for opt in menu_options}
            command = choice_map[choice]

            if command == "quit":
                break
            elif command == "status":
                self.show_status()
            elif command == "scrape":
                self.scrape_datasets()
            elif command == "build":
                self.build_containers()
            elif command == "benchmark":
                self.run_benchmarks()
            elif command == "results":
                self.view_results()
            elif command == "dev":
                self.development_environment()
            elif command == "compare":
                self.compare_versions_interactive()
            elif command == "compare-upstream":
                self.compare_upstream_build_and_run()
            elif command == "build-common":
                self.build_common_versions()
            elif command == "one-shot":
                self.one_shot_compare()
            elif command == "one-shot-full":
                self.full_one_shot_pipeline()
            elif command == "export-pages":
                self.prepare_github_pages()

            if command != "status":
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
                       choices=['status', 'scrape', 'build', 'benchmark', 'results', 'dev', 'compare', 'compare-upstream', 'build-common', 'one-shot'],
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
        elif args.command == 'compare':
            # Run comparator with defaults (1 run each on all sequences, include local if available)
            cli.compare_versions_interactive()
        elif args.command == 'dev':
            cli.development_environment()
        elif args.command == 'compare':
            cli.compare_versions_interactive()
        elif args.command == 'compare-upstream':
            cli.compare_upstream_build_and_run()
        elif args.command == 'build-common':
            cli.build_common_versions()
        elif args.command == 'one-shot':
            cli.one_shot_compare()
    else:
        # Interactive mode
        cli.interactive_mode()

if __name__ == "__main__":
    main()