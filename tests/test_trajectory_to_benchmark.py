import io
import os
from pathlib import Path

from trajectory_to_benchmark import TrajectoryConverter


def test_parse_trajectory_filename_valid():
    conv = TrajectoryConverter()
    meta = conv.parse_trajectory_filename(
        "f_MH_01_easy_upstream-v1.0_20250820_123456_trajectory.txt"
    )
    assert meta["sequence"] == "MH_01_easy"
    assert meta["version"] == "upstream-v1.0"


def test_parse_trajectory_filename_keyframe():
    conv = TrajectoryConverter()
    meta = conv.parse_trajectory_filename(
        "kf_MH_02_easy_optimized_20250820_123456_trajectory.txt"
    )
    assert meta["sequence"] == "MH_02_easy"
    assert meta["version"] == "optimized"


def test_analyze_trajectory_file(tmp_path: Path):
    # Two lines with nanosecond timestamps one second apart
    content = (
        "1403636579863555584 0 0 0 0 0 0 1\n"
        "1403636580863555584 0 0 0 0 0 0 1\n"
    )
    f = tmp_path / "f_MH_01_easy_upstream-v1.0_20250820_123456_trajectory.txt"
    f.write_text(content)

    conv = TrajectoryConverter(results_dir=tmp_path)
    analysis = conv.analyze_trajectory_file(f)
    assert analysis["valid"] is True
    assert analysis["frames"] == 2
    # Duration ~ 1.0s
    assert 0.9 <= analysis["duration_s"] <= 1.1


def test_create_benchmark_result_normalization(tmp_path: Path):
    # upstream should normalize to baseline
    f1 = tmp_path / "f_MH_01_easy_upstream-v1.0_20250820_123456_trajectory.txt"
    f1.write_text(
        "1403636579863555584 0 0 0 0 0 0 1\n1403636580863555584 0 0 0 0 0 0 1\n"
    )
    conv = TrajectoryConverter(results_dir=tmp_path)
    r1 = conv.create_benchmark_result(f1)
    assert r1 is not None
    assert r1.version == "baseline"

    # optimized should remain optimized
    f2 = tmp_path / "f_MH_01_easy_optimized_20250820_123456_trajectory.txt"
    f2.write_text(
        "1403636579863555584 0 0 0 0 0 0 1\n1403636580863555584 0 0 0 0 0 0 1\n"
    )
    r2 = conv.create_benchmark_result(f2)
    assert r2 is not None
    assert r2.version == "optimized"


