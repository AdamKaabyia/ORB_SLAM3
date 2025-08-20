import json
import os
import subprocess
from pathlib import Path

import pytest


def _which(cmd: str) -> bool:
    return subprocess.run(["bash", "-lc", f"command -v {cmd}"], capture_output=True).returncode == 0


def _detect_runtime():
    if _which("podman"):
        return "podman"
    if _which("docker"):
        return "docker"
    return None


def _list_image_tags(runtime: str):
    try:
        if runtime == "podman":
            proc = subprocess.run([runtime, "images", "--format", "json"], capture_output=True, text=True)
            if proc.returncode != 0:
                return set()
            import json as _json
            imgs = _json.loads(proc.stdout or "[]")
            tags = set()
            for img in imgs:
                for name in img.get("Names", []) or []:
                    if ":" in name:
                        tags.add(name.split(":", 1)[1])
            return tags
        else:
            # docker format differs
            proc = subprocess.run([runtime, "images", "--format", "{{.Repository}}:{{.Tag}}"], capture_output=True, text=True)
            if proc.returncode != 0:
                return set()
            tags = set()
            for line in (proc.stdout or "").splitlines():
                if "orb-slam3:" in line:
                    tags.add(line.split(":", 1)[1])
            return tags
    except Exception:
        return set()


def _ensure_image(tag: str) -> bool:
    """Ensure the given image tag exists. If ORB_ALLOW_BUILD=1, build when missing."""
    runtime = _detect_runtime()
    if not runtime:
        return False
    tags = _list_image_tags(runtime)
    if tag in tags:
        return True

    allow_build = os.environ.get("ORB_ALLOW_BUILD") == "1"
    if not allow_build:
        return False

    # Build missing images
    if tag == "optimized":
        res = subprocess.run("python3 cross-platform-dev.py build-optimized", shell=True)
        return res.returncode == 0
    if tag.startswith("upstream-"):
        ref = tag[len("upstream-") :]
        env = os.environ.copy()
        env["ORBSLAM_REF"] = ref
        res = subprocess.run("python3 cross-platform-dev.py build-upstream", shell=True, env=env)
        if res.returncode != 0:
            return False
        # Tag the built image
        tag_cmd = f"{runtime} tag localhost/orb-slam3:upstream localhost/orb-slam3:{tag}"
        return subprocess.run(tag_cmd, shell=True).returncode == 0
    return False


@pytest.mark.skipif(os.environ.get("ORB_INTEGRATION") != "1", reason="Set ORB_INTEGRATION=1 to run container smoke tests")
def test_compare_versions_container_smoke(tmp_path: Path):
    # Preconditions
    runtime = _detect_runtime()
    if not runtime:
        pytest.skip("No container runtime available")

    # Basic dataset presence check
    host_seq = Path("datasets/EuRoC/machine_hall/MH_01_easy")
    if not host_seq.exists():
        pytest.skip("Required dataset MH_01_easy not present on host")

    # Ensure images (build on demand when allowed)
    assert _ensure_image("upstream-v1.0") or _ensure_image("upstream-master"), "Missing upstream image and building disabled"
    assert _ensure_image("optimized"), "Missing optimized image and building disabled"

    # Pick upstream tag that exists
    upstream_tag = "upstream-v1.0" if _ensure_image("upstream-v1.0") else "upstream-master"

    out_json = tmp_path / "integration_compare.json"
    cmd = [
        "python3",
        "compare_versions.py",
        "--runs",
        "1",
        "--sequences",
        "MH_01_easy",
        "--versions",
        upstream_tag,
        "optimized",
        "--export-dashboard",
        str(out_json),
    ]

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["RICH_FORCE_TERMINAL"] = "1"
    proc = subprocess.run(" ".join(cmd), shell=True, env=env)
    assert proc.returncode == 0
    assert out_json.exists()

    data = json.loads(out_json.read_text())
    labels = data.get("metadata", {}).get("labels", {})

    def _normalize_label(val: str) -> str:
        # Strip any suffix like " (baseline)" or " (improved)"
        if not isinstance(val, str):
            return ""
        return val.split(" (", 1)[0]

    baseline_label = _normalize_label(labels.get("baseline"))
    optimized_label = _normalize_label(labels.get("optimized"))

    assert baseline_label in {"upstream-v1.0", "upstream-master"}
    assert optimized_label == "optimized"


