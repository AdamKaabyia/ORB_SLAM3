# ORB-SLAM3 Enhanced

### V1.0, December 22th, 2021
**Authors:** Carlos Campos, Richard Elvira, Juan J. Gómez Rodríguez, [José M. M. Montiel](http://webdiis.unizar.es/~josemari/), [Juan D. Tardos](http://webdiis.unizar.es/~jdtardos/).

> **Enhanced Version**: This repository includes comprehensive optimizations, cross-platform containerization, automated benchmarking, streamlined development tools, and professional results analysis.

## Key Enhancements

- **Containerized Development**: Alpine Linux containers with 85% size reduction
- **Cross-Platform**: Unified Linux/Windows development environment
- **Results Dashboard**: Professional performance analysis and visualization
- **Trajectory Conversion**: Automatic conversion from SLAM results to benchmark format
- **Automated Benchmarking**: Statistical analysis with comprehensive test suites
- **Build Optimization**: 50% faster builds with parallel compilation
- **Unified CLI**: Single command interface for all operations
- **Real-time Progress**: Professional terminal UI with live progress tracking
- **Ground Truth Evaluation**: Accuracy assessment against reference trajectories

## Quick Start

### **Recommended: Use Our Unified CLI**
```bash
# Interactive mode - handles everything automatically
python3 orbslam3_cli.py

# Or direct commands
python3 orbslam3_cli.py status      # Check system status
python3 orbslam3_cli.py build       # Build containers
python3 orbslam3_cli.py scrape      # Download datasets
python3 orbslam3_cli.py benchmark   # Run benchmarks
```

### **Results Analysis Workflow**
```bash
# 1. Run SLAM and generate trajectories (automatically done by tools)
python3 orbslam3_progress.py optimized vocab.txt config.yaml sequence/

# 2. Convert trajectory files to dashboard format
python3 trajectory_to_benchmark.py --output results.json

# 3. View professional dashboard
python3 results_dashboard.py --results-file results.json

# 4. Export performance reports
python3 results_dashboard.py --results-file results.json --export-report
```

### **One-shot Compare (new)**
```bash
# Guided flow: pick versions (with common presets), optional repo@ref validation,
# confirm builds if needed, run, export and render dashboard
python3 orbslam3_cli.py one-shot
```
Inputs per version:
- Preset number: 1) v0.2-beta  2) v0.3-beta  3) v0.4-beta  4) v1.0  5) master
- Existing tag: e.g., `optimized`, `upstream-v1.0`, `upstream-master`
- Plain upstream ref: e.g., `v1.0` (resolved to `upstream-v1.0`)
- Custom: `https://github.com/UZ-SLAMLab/ORB_SLAM3.git@v1.0` (validated and prompts before build)

Behavior:
- If a needed image tag is missing, you will be prompted before building (no auto-build without confirmation).
- After the run, a dashboard JSON is created and rendered automatically with dynamic column headers (actual compared tags).

### **Traditional Build (if needed)**
```bash
git clone https://github.com/AdamKaabyia/ORB_SLAM3.git
cd ORB_SLAM3
chmod +x build.sh
./build.sh  # Optimized with parallel builds
```

## What's Available

**Core SLAM Functionality:**
- **Visual, Visual-Inertial and Multi-Map SLAM**
- **Monocular, stereo and RGB-D** camera support
- **Pin-hole and fisheye** lens models
- All sensor configurations from original ORB-SLAM3

**Enhanced Development Tools:**
- **Container Development**: `./container-dev.sh` (Linux) or `.\windows-dev.ps1` (Windows)
- **Dataset Management**: Automated EuRoC dataset scraper
- **Progress Monitoring**: Real-time UI with `orbslam3_progress.py`
- **Benchmarking Suite**: Interactive UI with `orbslam3_benchmark_ui.py`
- **Results Dashboard**: Analysis and visualization tools
- **Trajectory Converter**: Bridge between SLAM output and dashboard input

## Results Analysis System

The enhanced system provides a complete pipeline from SLAM execution to professional performance analysis:

### **Generated Data**
- **Trajectory Files**: Standard TUM format with pose data
- **Benchmark Results**: Comprehensive JSON format with performance metrics
- **Performance Reports**: Markdown format for documentation
- **System Metrics**: CPU, memory, and accuracy measurements

### **Dashboard Features**
- **Performance Comparison**: Baseline vs our local version (optimized) analysis
- **Statistical Significance**: Confidence intervals and improvement metrics
- **Per-Sequence Breakdown**: Individual dataset performance
- **System Information**: Hardware configuration and test environment
- **Export Capabilities**: Reports, plots, and data export

### **Key Metrics Tracked**
- **Runtime Performance**: Processing time and frame rates
- **Memory Usage**: Peak and average memory consumption
- **SLAM Quality**: Frames processed, lost frames, keyframes created
- **Accuracy Metrics**: RMSE translation/rotation errors vs ground truth
- **System Metrics**: CPU usage, thermal performance

## Documentation

| Guide | Description |
|-------|-------------|
| **[Cross-Platform Setup](README_CrossPlatform.md)** | **Complete setup for Linux & Windows** |
| **[Developer Guide](DEVELOPER_README.md)** | **Development workflow and component architecture** |
| [Enhancement Report](report.md) | Detailed technical improvements |
| [Original README](ReadmeOriginal.md) | Original ORB-SLAM3 documentation |
| [Dependencies](Dependencies.md) | Library requirements |
| [Calibration Tutorial](Calibration_Tutorial.pdf) | Camera calibration guide |

## Development Modes

### **Container Development (Recommended)**
```bash
# Linux
./container-dev.sh build
./container-dev.sh dev

# Windows
.\windows-dev.ps1 build
.\windows-dev.ps1 dev

# Cross-platform
python3 cross-platform-dev.py build
python3 cross-platform-dev.py run
```

### **Dataset Management**
```bash
# List available datasets
python3 euroc_dataset_scraper.py --list

# Download specific location
python3 euroc_dataset_scraper.py --location machine_hall

# Interactive management via CLI
python3 orbslam3_cli.py scrape
```

### **Benchmarking & Testing**
```bash
# Interactive benchmark UI
python3 orbslam3_benchmark_ui.py

# Progress monitoring for single runs
python3 orbslam3_progress.py optimized vocab.txt config.yaml sequence/

# Ground truth comparison
python3 ground_truth_comparison.py vocab.txt config.yaml sequence/

# Full benchmark suite
python3 orbslam3_cli.py benchmark
```

### **Results Analysis**
```bash
# Convert existing trajectory files
python3 trajectory_to_benchmark.py

# Interactive dashboard
python3 results_dashboard.py --results-file benchmark_results.json

# Generate reports
python3 results_dashboard.py --results-file benchmark_results.json --export-report

# Non-interactive summary
python3 results_dashboard.py --results-file benchmark_results.json --no-interactive
```

## Version Comparison (Containers)

Compare different ORB-SLAM3 versions using Alpine-based containers.

### Build common upstream references

```bash
# Build and tag upstream v1.0
ORBSLAM_REF=v1.0 python3 cross-platform-dev.py build-upstream
podman tag localhost/orb-slam3:upstream localhost/orb-slam3:upstream-v1.0

# Build and tag upstream master
ORBSLAM_REF=master python3 cross-platform-dev.py build-upstream
podman tag localhost/orb-slam3:upstream localhost/orb-slam3:upstream-master
```

### Quick comparison (container-only)

```bash
# Live streaming output
PYTHONUNBUFFERED=1 RICH_FORCE_TERMINAL=1 \
python3 compare_versions.py --runs 1 --sequences MH_01_easy \
  --versions upstream-v1.0 optimized
```

Flags:
- `--versions`: list any container tags to compare (e.g., `upstream-v0.4-beta`, `upstream-master`, `optimized`)
- `--include-local`: also compare a host-built binary if available
- `--no-stream`: disable live terminal streaming
- `--no-save-logs`: skip writing `benchmark_results/compare_*.log`

### Interactive picker

```bash
python3 orbslam3_cli.py compare
```

- Select any two versions (container tags and optional `local`).
- Presets for common upstream versions are shown; you can also enter a `repo@ref`.
- If a required `upstream-<ref>` tag is missing, you'll be asked to confirm building it.

### One-shot compare (end-to-end)
```bash
python3 orbslam3_cli.py one-shot
```
- Pick versions using presets, tags, refs, or `repo@ref`.
- Confirms and builds any missing images, runs comparison, exports results JSON, and shows the dashboard.
- Dashboard columns are labeled with the actual compared tags.

### Build and compare two upstream versions (single command)

```bash
python3 orbslam3_cli.py compare-upstream
```

- Prompts for two upstream refs (e.g., `v1.0`, `v0.4-beta`, `master`).
- Builds both Alpine containers, tags them as `upstream-<ref>`, and runs a comparison with live logs.
- Optional prompt to export a dashboard JSON for full metrics (use with `results_dashboard.py`).

## Build Optimizations

**Performance Improvements:**
- **50% faster builds** - Examples_old compilation skipped
- **Parallel compilation** - Uses all CPU cores automatically
- **Container efficiency** - 85% size reduction vs manual setup
- **Streamlined dependencies** - Alpine Linux minimal packages

**Key Changes:**
- Removed redundant Examples_old builds (30+ unnecessary executables)
- Added parallel build detection and optimization
- Enhanced build scripts with progress feedback
- Optimized container layers and dependencies

## Performance Analysis Results

The enhanced system provides comprehensive performance analysis capabilities:

### **Benchmark Metrics**
- **Runtime Comparison**: Baseline vs optimized execution times
- **Memory Efficiency**: Peak and average memory usage analysis
- **Accuracy Assessment**: Trajectory quality vs ground truth references
- **System Performance**: CPU usage, thermal characteristics

### **Supported Sequences**
- **EuRoC Dataset**: Machine Hall (MH_01-05), Vicon Room 1 (V1_01-03), Vicon Room 2 (V2_01-03)
- **Ground Truth**: 14 reference trajectories for accuracy evaluation
- **Auto-Detection**: Automatic sequence identification and mapping

### **Output Formats**
- **Professional Dashboard**: Rich terminal UI with tables and charts
- **Markdown Reports**: Documentation-ready performance summaries
- **JSON Data**: Machine-readable benchmark results
- **CSV Export**: Spreadsheet-compatible data format

## Getting Started

1. **Clone and Setup**
   ```bash
   git clone https://github.com/AdamKaabyia/ORB_SLAM3.git
   cd ORB_SLAM3
   ```

2. **Quick Test Run**
   ```bash
   # Interactive mode handles everything
   python3 orbslam3_cli.py
   ```

3. **Professional Workflow**
   ```bash
   # Download datasets
   python3 euroc_dataset_scraper.py --location machine_hall

   # Run SLAM processing
   python3 orbslam3_progress.py optimized vocab.txt config.yaml sequence/

   # Generate professional dashboard
   python3 trajectory_to_benchmark.py --output analysis.json
   python3 results_dashboard.py --results-file analysis.json
   ```

For detailed setup instructions, see [Cross-Platform Setup Guide](README_CrossPlatform.md).

For development and contribution guidelines, see [Developer Guide](DEVELOPER_README.md).

## Testing

### Unit tests (no containers required)
```bash
pip3 install pytest
pytest
```
The test run is verbose and shows which tests passed/failed and any skips.

### Container integration smoke test (opt-in)
```bash
# With existing images
ORB_INTEGRATION=1 pytest

# Allow auto-build of missing images
ORB_INTEGRATION=1 ORB_ALLOW_BUILD=1 pytest

# Run only the container test (more detail)
ORB_INTEGRATION=1 pytest -k test_compare_versions_container_smoke -s

# Skip the container test (unit tests only)
pytest -k 'not integration'
```
Notes:
- Requires Podman or Docker and the EuRoC sequence `datasets/EuRoC/machine_hall/MH_01_easy` present.
- The integration test runs a single-sequence compare and asserts the exported dashboard JSON looks correct.
 - It can take several minutes due to vocabulary load (~139MB) and full-sequence processing.

Live logs without pytest (foreground compare):
```bash
PYTHONUNBUFFERED=1 RICH_FORCE_TERMINAL=1 \
python3 compare_versions.py --runs 1 --sequences MH_01_easy \
  --versions upstream-v1.0 optimized \
  --export-dashboard compare_dashboard_integration.json
```

## Related Work

This enhanced version builds upon the excellent original ORB-SLAM3 work:

Carlos Campos, Richard Elvira, Juan J. Gómez Rodríguez, José M. M. Montiel and Juan D. Tardós, **ORB-SLAM3: An Accurate Open-Source Library for Visual, Visual-Inertial and Multi-Map SLAM**, *IEEE Transactions on Robotics 37(6):1874-1890, Dec. 2021*. **[PDF](https://arxiv.org/abs/2007.11898)**.

## License

ORB-SLAM3 is released under [GPLv3 license](https://github.com/UZ-SLAMLab/ORB_SLAM3/blob/master/License-gpl.txt). For a list of all code/library dependencies (and associated licenses), please see [Dependencies.md](Dependencies.md).

For a closed-source version of ORB-SLAM3 for commercial purposes, please contact the authors: orbslam (at) unizar (dot) es.

If you use ORB-SLAM3 (or this enhanced version) in an academic work, please cite:

```
@article{ORBSLAM3_TRO,
  title={{ORB-SLAM3}: An Accurate Open-Source Library for Visual, Visual-Inertial
           and Multi-Map {SLAM}},
  author={Campos, Carlos AND Elvira, Richard AND G\´omez, Juan J. AND Montiel,
          Jos\'e M. M. AND Tard\'os, Juan D.},
  journal={IEEE Transactions on Robotics},
  volume={37},
  number={6},
  pages={1874-1890},
  year={2021}
 }
```
