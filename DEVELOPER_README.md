# Developer Guide: ORB-SLAM3 Benchmark Suite

Welcome to the ORB-SLAM3 comprehensive benchmarking and evaluation system! This guide will help you understand the codebase, set up your development environment, and contribute effectively.

## Project Structure

```
ORB_SLAM3/
├── Core ORB-SLAM3 (C++)
│   ├── src/                    # ORB-SLAM3 source code
│   ├── include/                # Headers
│   ├── Examples/               # Example executables
│   └── Thirdparty/            # Dependencies
│
├── Containerization
│   ├── Dockerfile             # Main container
│   ├── Dockerfile.upstream    # Upstream version
│   ├── container-dev.sh       # Container development tools
│   └── build.sh              # Optimized build script
│
├── Benchmarking & Evaluation
│   ├── orbslam3_benchmark_ui.py         # Interactive benchmark suite
│   ├── ground_truth_comparison.py       # Accuracy evaluation
│   ├── orbslam3_progress.py            # Real-time progress monitoring
│   ├── orbslam3_runner.py              # Automated benchmark runner
│   ├── results_dashboard.py            # Results analysis & visualization
│   ├── trajectory_to_benchmark.py      # Results format converter
│   └── orbslam3_cli.py                # Unified CLI interface
│
├── Evaluation Tools
│   ├── evaluation/
│   │   ├── evaluate_ate_scale.py   # Trajectory accuracy evaluation
│   │   ├── associate.py           # Timestamp association
│   │   └── Ground_truth/          # Reference trajectories
│   └── euroc_dataset_scraper.py   # Dataset download automation
│
├── Cross-Platform Support
│   ├── cross-platform-dev.py     # Universal development script
│   ├── windows-dev.ps1          # Windows PowerShell script
│   └── README_CrossPlatform.md  # Cross-platform documentation
│
└── Results & Data
    ├── results/               # Generated trajectory files
    ├── benchmark_results/     # Performance metrics (JSON format)
    └── datasets/             # EuRoC dataset storage
```

## Quick Start

### Prerequisites
- **Container Runtime**: Podman or Docker
- **Python 3.8+** with pip
- **Git** for version control
- **Linux/Windows/macOS** (cross-platform support)

### Development Setup

1. **Clone and Initialize**
   ```bash
   git clone <your-fork>
   cd ORB_SLAM3
   ```

2. **Cross-Platform Development Environment**
   ```bash
   # Linux/macOS
   python3 cross-platform-dev.py --setup-dev

   # Windows
   .\windows-dev.ps1 -SetupDev
   ```

3. **Install Python Dependencies**
   ```bash
   pip install rich numpy matplotlib
   ```

4. **Build Containers**
   ```bash
   ./build.sh                    # Build our local version (optimized)
   ./container-dev.sh --build    # Build development environment
   ```

## Development Workflow

### Building and Testing

1. **Code Changes**: Make your changes to C++ or Python code
2. **Rebuild**: `./build.sh` (only needed for C++ changes)
3. **Test**: Use the benchmark suite to verify changes
4. **Evaluate**: Run accuracy tests against ground truth

### Testing Your Changes

```bash
# Quick single test
python3 orbslam3_progress.py optimized \
  /opt/orb-slam3/Vocabulary/ORBvoc.txt \
  /opt/orb-slam3/Examples/Monocular/EuRoC.yaml \
  /workspace/datasets/EuRoC/machine_hall/MH_01_easy

# Interactive benchmark suite
python3 orbslam3_benchmark_ui.py

# Ground truth accuracy comparison
python3 ground_truth_comparison.py \
  /opt/orb-slam3/Vocabulary/ORBvoc.txt \
  /opt/orb-slam3/Examples/Monocular/EuRoC.yaml \
  /workspace/datasets/EuRoC/machine_hall/MH_01_easy

# Unified CLI interface
python3 orbslam3_cli.py benchmark
```

## Component Guide

### Core Components

#### **orbslam3_progress.py**
- Real-time SLAM execution monitoring
- Clean status updates without fake progress bars
- File generation with proper permissions
- Used by other tools for actual ORB-SLAM3 execution

#### **trajectory_to_benchmark.py** (NEW)
- Converts raw trajectory files to dashboard-compatible JSON format
- Bridges the gap between SLAM output and performance analysis
- Extracts metrics from trajectory data (frames, duration, estimated performance)
- Generates comprehensive benchmark results with system and accuracy metrics

#### **results_dashboard.py**
- Professional performance analysis dashboard
- Rich terminal UI with tables and statistical comparisons
- Export capabilities (markdown reports, plots)
- Non-interactive mode for automation

#### **orbslam3_benchmark_ui.py**
- Interactive menu-driven benchmark suite
- Performance comparison (runtime, memory)
- Currently uses simulated data (needs integration)
- Rich terminal UI with progress tracking

#### **ground_truth_comparison.py**
- Accuracy evaluation against reference trajectories
- Compares upstream vs our local version
- Uses real ATE (Absolute Trajectory Error) metrics
- Integrates with existing evaluation tools

#### **orbslam3_cli.py**
- Unified command-line interface
- Orchestrates all other tools
- Entry point for automated workflows

### Results Analysis Pipeline

The enhanced system provides a complete pipeline from SLAM execution to professional performance analysis:

#### **1. SLAM Execution**
```bash
# Real-time progress monitoring
python3 orbslam3_progress.py optimized vocab.txt config.yaml sequence/
# Generates: results/f_sequence_version_timestamp_trajectory.txt
```

#### **2. Results Conversion**
```bash
# Convert trajectory files to dashboard format
python3 trajectory_to_benchmark.py --output analysis.json
# Generates: Comprehensive JSON with performance metrics
```

#### **3. Professional Analysis**
```bash
# Interactive dashboard
python3 results_dashboard.py --results-file analysis.json

# Export reports
python3 results_dashboard.py --results-file analysis.json --export-report
```

## Version Comparison Toolkit

Container-based comparator to evaluate upstream refs, forks, and our local version.

### Building upstream refs (Alpine)

```bash
# Release tags
ORBSLAM_REF=v0.2-beta python3 cross-platform-dev.py build-upstream
podman tag localhost/orb-slam3:upstream localhost/orb-slam3:upstream-v0.2-beta

ORBSLAM_REF=v0.3-beta python3 cross-platform-dev.py build-upstream
podman tag localhost/orb-slam3:upstream localhost/orb-slam3:upstream-v0.3-beta

ORBSLAM_REF=v0.4-beta python3 cross-platform-dev.py build-upstream
podman tag localhost/orb-slam3:upstream localhost/orb-slam3:upstream-v0.4-beta

ORBSLAM_REF=v1.0 python3 cross-platform-dev.py build-upstream
podman tag localhost/orb-slam3:upstream localhost/orb-slam3:upstream-v1.0

# Master
ORBSLAM_REF=master python3 cross-platform-dev.py build-upstream
podman tag localhost/orb-slam3:upstream localhost/orb-slam3:upstream-master
```

### Compare versions

```bash
# Live streaming logs
PYTHONUNBUFFERED=1 RICH_FORCE_TERMINAL=1 \
python3 compare_versions.py --runs 1 --sequences MH_01_easy \
  --versions upstream-v1.0 our-local

# Arbitrary tags (forks/branches)
python3 compare_versions.py --runs 1 --sequences MH_01_easy \
  --versions upstream-v0.4-beta upstream-master

# Include local (host build) if present
python3 compare_versions.py --include-local --versions our-local upstream-v1.0 --sequences MH_01_easy
```

### Interactive comparison via CLI

```bash
python3 orbslam3_cli.py compare
```

- Pick any two versions (container tags, optional `local`).
- Missing `upstream-<ref>` tags are auto-built using `ORBSLAM_REF`.

#### **4. Ground Truth Evaluation**
```bash
# Accuracy assessment
python3 ground_truth_comparison.py vocab.txt config.yaml sequence/
```

### Data Flow Architecture

```
Raw SLAM Execution
        ↓
Trajectory Files (TUM format)
        ↓
trajectory_to_benchmark.py
        ↓
Benchmark JSON (Dashboard format)
        ↓
results_dashboard.py
        ↓
Professional Analysis & Reports
```

### Key Data Formats

#### **Trajectory Files** (TUM format)
```
timestamp x y z qx qy qz qw
1403636579863555584.000000 0.000041200 0.005926782 0.002408904 -0.000855298 0.004876168 -0.002615274 0.999984324
```

#### **Benchmark JSON** (Dashboard format)
```json
{
  "metadata": {
    "timestamp": "2025-07-18T15:56:01.443348",
    "total_runs": 4,
    "successful_runs": 4,
    "sequences_tested": 2
  },
  "results": [
    {
      "sequence": "MH/01/easy",
      "version": "optimized",
      "total_runtime_ms": 441479.99,
      "system_metrics": {
        "memory_mb_peak": 1218.0,
        "cpu_percent_avg": 87.36
      },
      "slam_metrics": {
        "total_frames": 3680,
        "processed_frames": 3680,
        "keyframes_created": 368
      },
      "accuracy_metrics": {
        "rmse_translation": 0.05,
        "rmse_rotation": 0.8
      }
    }
  ]
}
```

## Development Priorities

### Current Status
- Real-time progress monitoring (no fake progress bars)
- Ground truth evaluation system
- Cross-platform development support
- Container optimization (50% build speedup)
- Universal EuRoC dataset support
- **Complete results analysis pipeline (NEW)**

### Integration Completed
- **Trajectory-to-dashboard conversion**: Bridge between SLAM output and analysis
- **Professional dashboard system**: Comprehensive performance analysis
- **Export capabilities**: Markdown reports and data visualization
- **Non-interactive modes**: Automation-friendly interfaces

### Integration Still Needed
- **Combine benchmark UI with real execution** (currently uses simulated data)
- **Standardize version naming** (baseline/upstream/optimized)
- **Add performance metrics** to ground truth comparison
- **Integrate real-time system monitoring** into benchmark runs

## Results Analysis System

### Comprehensive Metrics Tracking

#### **Performance Metrics**
- **Runtime**: Total execution time, processing speed
- **Memory**: Peak and average memory consumption
- **CPU**: Average and maximum CPU utilization
- **Thermal**: System temperature monitoring

#### **SLAM Quality Metrics**
- **Frames**: Total frames, processed frames, lost frames
- **Keyframes**: Created keyframes, keyframe density
- **Map Points**: Generated map points, active points
- **Loop Closures**: Detected and validated closures

#### **Accuracy Metrics**
- **RMSE Translation**: Root mean square error in position
- **RMSE Rotation**: Root mean square error in orientation
- **ATE**: Absolute Trajectory Error vs ground truth
- **RPE**: Relative Pose Error analysis

### Dashboard Features

#### **Performance Comparison**
- Baseline vs optimized analysis
- Statistical significance testing
- Confidence intervals and improvement metrics
- Per-sequence performance breakdown

#### **Visualization**
- Professional terminal UI with Rich library
- ASCII tables and charts
- Progress bars and status indicators
- Export to markdown reports

#### **Export Capabilities**
- **JSON**: Machine-readable benchmark results
- **CSV**: Spreadsheet-compatible data
- **Markdown**: Documentation-ready reports
- **Plots**: Visual performance comparisons (if matplotlib available)

## Benchmarking Architecture

### Version Comparison Strategy

**Current**: Complete evaluation pipeline
```
Real SLAM Execution: orbslam3_progress.py
         ↓
Results Conversion: trajectory_to_benchmark.py
         ↓
Performance Analysis: results_dashboard.py
         ↓
Ground Truth Accuracy: ground_truth_comparison.py
```

**Previous**: Separate tools for different metrics
```
Performance: orbslam3_benchmark_ui.py (simulated)
Accuracy:    ground_truth_comparison.py (real)
```

### Evaluation Pipeline Components

#### **Dataset Management**: `euroc_dataset_scraper.py`
- Automated EuRoC dataset download
- Sequence auto-detection and organization
- Dataset configuration management

#### **SLAM Execution**: `orbslam3_progress.py`
- Real-time execution monitoring
- Container orchestration
- Results file generation with proper permissions

#### **Results Conversion**: `trajectory_to_benchmark.py`
- Trajectory file parsing and analysis
- Performance metrics estimation
- Benchmark format generation

#### **Performance Analysis**: `results_dashboard.py`
- Statistical analysis and comparison
- Professional visualization
- Report generation and export

#### **Accuracy Evaluation**: `evaluation/evaluate_ate_scale.py`
- Ground truth trajectory comparison
- ATE/RPE metrics calculation
- Reference trajectory management

## Container Development

### Container Architecture
- **Base**: Alpine Linux 3.22.1 (85% size reduction)
- **Optimization**: Parallel builds, minimal dependencies
- **Cross-platform**: Podman (Linux) / Docker (Windows)

### Development Commands
```bash
# Build containers
./container-dev.sh build              # Linux
.\windows-dev.ps1 build              # Windows
python3 cross-platform-dev.py build  # Universal

# Development environment
./container-dev.sh dev
.\windows-dev.ps1 dev
python3 cross-platform-dev.py dev

# Testing
./container-dev.sh test
.\windows-dev.ps1 test
python3 cross-platform-dev.py test
```

### Performance Optimizations
- **50% faster builds**: Examples_old compilation skipped
- **Parallel compilation**: Uses all CPU cores automatically
- **Container efficiency**: Optimized layers and minimal packages
- **Resource management**: Configurable memory and CPU limits

## Testing and Validation

### Automated Testing Suite
```bash
# System validation
python3 orbslam3_cli.py status

# Component testing
python3 trajectory_to_benchmark.py --list
python3 results_dashboard.py --help
python3 ground_truth_comparison.py --help

# End-to-end workflow
python3 orbslam3_cli.py benchmark
```

### Performance Validation
```bash
# Quick performance check
python3 orbslam3_progress.py optimized vocab.txt config.yaml sequence/

# Convert and analyze
python3 trajectory_to_benchmark.py --output test.json
python3 results_dashboard.py --results-file test.json --no-interactive

# Ground truth comparison
python3 ground_truth_comparison.py vocab.txt config.yaml sequence/
```

### Cross-Platform Testing
```bash
# Linux testing
./container-dev.sh test

# Windows testing
.\windows-dev.ps1 test

# Universal testing
python3 cross-platform-dev.py test
```

## Contribution Guidelines

### Code Style
- **Python**: Follow PEP 8, use type hints
- **C++**: Follow existing ORB-SLAM3 conventions
- **Documentation**: Clear docstrings and comments
- **No visual elements**: Professional, clean output

### Testing Requirements
- **Unit tests**: For new functionality
- **Integration tests**: For workflow changes
- **Cross-platform**: Test on Linux and Windows
- **Performance validation**: Benchmark comparisons

### Pull Request Process
1. **Fork and branch**: Create feature branches
2. **Implement changes**: Follow coding standards
3. **Test thoroughly**: All platforms and workflows
4. **Update documentation**: READMEs and comments
5. **Submit PR**: Clear description and test results

### Development Priorities
1. **Reliability**: Robust error handling and validation
2. **Performance**: Optimize execution and resource usage
3. **Usability**: Clear interfaces and documentation
4. **Compatibility**: Cross-platform support
5. **Maintainability**: Clean, documented code

## Advanced Development

### Custom Evaluation Metrics
```python
# Example: Adding custom accuracy metric
def calculate_custom_metric(trajectory_file: Path) -> float:
    # Parse trajectory and compute metric
    pass

# Integrate into trajectory_to_benchmark.py
```

### Dashboard Customization
```python
# Example: Adding custom dashboard view
def custom_analysis_view(self):
    # Create custom Rich table or panel
    pass

# Add to results_dashboard.py interactive menu
```

### Container Optimization
```bash
# Custom build flags
export CXXFLAGS="-O3 -march=native"
python3 cross-platform-dev.py build

# Custom resource limits
podman run --memory=12g --cpus=6 orb-slam3:optimized
```

### Performance Profiling
```bash
# Memory profiling
python3 -m memory_profiler orbslam3_progress.py

# CPU profiling
python3 -m cProfile -o profile.out orbslam3_progress.py

# Container resource monitoring
podman stats orb-slam3-container
```

## Troubleshooting Development Issues

### Common Development Problems

#### **Build Issues**
```bash
# Clean rebuild
python3 cross-platform-dev.py clean
python3 cross-platform-dev.py build

# Check dependencies
python3 orbslam3_cli.py status
```

#### **Container Issues**
```bash
# Check container engine
podman --version  # or docker --version

# Verify permissions
ls -la results/

# Test container functionality
python3 cross-platform-dev.py test
```

#### **Results Analysis Issues**
```bash
# Validate trajectory files
python3 trajectory_to_benchmark.py --list

# Check JSON format
python3 -m json.tool benchmark_results.json

# Test dashboard
python3 results_dashboard.py --results-file test.json --no-interactive
```

### Performance Debugging
```bash
# Monitor system resources
htop  # or top on Windows

# Check container resources
podman stats

# Profile Python scripts
python3 -m cProfile script.py
```

### Getting Development Help
1. **Documentation**: Review this guide and cross-platform README
2. **System status**: Run `python3 orbslam3_cli.py status`
3. **Verbose logging**: Add `--verbose` to commands
4. **Container logs**: Check container output for errors
5. **GitHub issues**: Report bugs or discuss features

This developer guide provides comprehensive information for contributing to and extending the ORB-SLAM3 enhanced benchmarking system. The modular architecture and professional tooling make it easy to add new features and maintain code quality.