import json
from pathlib import Path

from results_dashboard import ResultsDashboard


def sample_results(tmp_path: Path) -> Path:
    data = {
        "metadata": {
            "timestamp": "2025-08-20T00:00:00",
            "total_runs": 2,
            "successful_runs": 2,
            "sequences_tested": 1,
            "labels": {"baseline": "upstream-v1.0", "optimized": "optimized"},
            "system_info": {"cpu_count": 8, "memory_gb": 16, "platform": "Linux"},
        },
        "results": [
            {
                "sequence": "MH/01/easy",
                "version": "baseline",
                "success": True,
                "total_runtime_ms": 200000.0,
                "system_metrics": {"memory_mb_peak": 1000.0, "cpu_percent_avg": 85.0},
                "slam_metrics": {
                    "processed_frames": 3600,
                    "lost_frames": 50,
                    "keyframes_created": 300,
                },
                "accuracy_metrics": {"rmse_translation": 0.1, "rmse_rotation": 1.0},
            },
            {
                "sequence": "MH/01/easy",
                "version": "optimized",
                "success": True,
                "total_runtime_ms": 180000.0,
                "system_metrics": {"memory_mb_peak": 980.0, "cpu_percent_avg": 84.0},
                "slam_metrics": {
                    "processed_frames": 3550,
                    "lost_frames": 45,
                    "keyframes_created": 290,
                },
                "accuracy_metrics": {"rmse_translation": 0.1, "rmse_rotation": 0.9},
            },
        ],
    }
    f = tmp_path / "sample.json"
    f.write_text(json.dumps(data))
    return f


def test_calculate_comparison_stats(tmp_path: Path):
    rd = ResultsDashboard()
    fp = sample_results(tmp_path)
    assert rd.load_results(fp)

    stats = rd.calculate_comparison_stats("total_runtime_ms")
    assert stats.baseline_mean == 200000.0
    assert stats.optimized_mean == 180000.0
    assert stats.improvement_percent == ((200000.0 - 180000.0) / 200000.0) * 100


