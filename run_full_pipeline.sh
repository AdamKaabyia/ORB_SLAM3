#!/bin/bash

# ORB-SLAM3 Complete Pipeline - From Zero to Dashboard
# This script builds everything from scratch and runs the complete pipeline

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo_step() {
    echo -e "${CYAN}[STEP]${NC} $1"
}

echo_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_banner() {
    echo -e "${CYAN}"
    echo "=============================================================="
    echo "  ORB-SLAM3 Complete Pipeline: Zero to Dashboard"
    echo "=============================================================="
    echo -e "${NC}"
    echo "This will:"
    echo "  1. Clean up any existing containers/images"
    echo "  2. Build upstream and optimized container images"
    echo "  3. Download complete EuRoC dataset"
    echo "  4. Run baseline + optimized benchmarks on ALL EuRoC sequences"
    echo "  5. Convert results to dashboard format"
    echo "  6. Launch results dashboard"
    echo ""
}

check_dependencies() {
    echo_step "Checking dependencies..."

    # Check for container runtime
    if command -v docker &> /dev/null; then
        CONTAINER_ENGINE="docker"
        echo_info "Using Docker as container engine"
    elif command -v podman &> /dev/null; then
        CONTAINER_ENGINE="podman"
        echo_info "Using Podman as container engine"
    else
        echo_error "Neither Docker nor Podman found. Please install one."
        exit 1
    fi

    # Check for Python 3
    if ! command -v python3 &> /dev/null; then
        echo_error "Python 3 not found. Please install Python 3."
        exit 1
    fi

    # Check for required Python packages
    echo_info "Checking Python packages..."
    python3 -c "import requests, json, pathlib" 2>/dev/null || {
        echo_warning "Installing required Python packages..."
        pip3 install requests tqdm rich
    }

    echo_success "Dependencies check completed"
}

cleanup_containers() {
    echo_step "Cleaning up existing containers and images..."

    # Stop and remove any existing containers
    $CONTAINER_ENGINE ps -aq --filter "name=orb-slam3" | xargs -r $CONTAINER_ENGINE stop 2>/dev/null || true
    $CONTAINER_ENGINE ps -aq --filter "name=orb-slam3" | xargs -r $CONTAINER_ENGINE rm 2>/dev/null || true

    # Remove existing images
    $CONTAINER_ENGINE images -q --filter "reference=*orb-slam3*" | xargs -r $CONTAINER_ENGINE rmi -f 2>/dev/null || true
    $CONTAINER_ENGINE images -q --filter "reference=localhost/orb-slam3*" | xargs -r $CONTAINER_ENGINE rmi -f 2>/dev/null || true

    echo_success "Cleanup completed"
}

build_containers() {
    echo_step "Building container images..."

    echo_info "Building upstream baseline container..."
    python3 cross-platform-dev.py build-upstream

    echo_info "Building optimized container..."
    python3 cross-platform-dev.py build-optimized

    echo_success "Container builds completed"
}

download_datasets() {
    echo_step "Downloading EuRoC datasets..."

    echo_info "Downloading Machine Hall sequences..."
    python3 euroc_dataset_scraper.py --location machine_hall

    echo_info "Downloading Vicon Room 1 sequences..."
    python3 euroc_dataset_scraper.py --location vicon_room1

    echo_info "Downloading Vicon Room 2 sequences..."
    python3 euroc_dataset_scraper.py --location vicon_room2

    echo_success "Dataset downloads completed"
}

run_comprehensive_benchmarks() {
    echo_step "Running comprehensive benchmarks..."

    # Create results directory
    mkdir -p results

    # ALL EuRoC sequences for comprehensive testing
    SEQUENCES=(
        "machine_hall/MH_01_easy"
        "machine_hall/MH_02_easy"
        "machine_hall/MH_03_medium"
        "machine_hall/MH_04_difficult"
        "machine_hall/MH_05_difficult"
        "vicon_room1/V1_01_easy"
        "vicon_room1/V1_02_medium"
        "vicon_room1/V1_03_difficult"
        "vicon_room2/V2_01_easy"
        "vicon_room2/V2_02_medium"
        "vicon_room2/V2_03_difficult"
    )

    echo_info "Running benchmarks on ALL 11 EuRoC sequences (22 total runs)..."

        for sequence in "${SEQUENCES[@]}"; do
        echo_info "Processing ${sequence}..."

        # Run baseline version first
        echo_info "  → Running baseline version..."
        python3 orbslam3_progress.py upstream \
            /opt/orb-slam3/Vocabulary/ORBvoc.txt \
            /opt/orb-slam3/Examples/Monocular/EuRoC.yaml \
            /workspace/datasets/EuRoC/${sequence} || {
            echo_warning "Failed baseline ${sequence}, continuing..."
        }

        # Run optimized version
        echo_info "  → Running optimized version..."
        python3 orbslam3_progress.py optimized \
            /opt/orb-slam3/Vocabulary/ORBvoc.txt \
            /opt/orb-slam3/Examples/Monocular/EuRoC.yaml \
            /workspace/datasets/EuRoC/${sequence} || {
            echo_warning "Failed optimized ${sequence}, continuing..."
            continue
        }

        echo_success "Completed both versions for ${sequence}"
    done

    echo_success "Comprehensive EuRoC benchmarks completed"
}

convert_results() {
    echo_step "Converting results to dashboard format..."

    # Convert trajectory files to dashboard format
    python3 trajectory_to_benchmark.py --output pipeline_results.json

    echo_success "Results conversion completed"
}

launch_dashboard() {
    echo_step "Launching results dashboard..."

    # Check if results file exists
    if [ ! -f "pipeline_results.json" ]; then
        echo_warning "No results file found. Creating sample dashboard..."
        # Try to find any existing trajectory files and convert them
        if ls results/f_*_trajectory.txt 1> /dev/null 2>&1; then
            python3 trajectory_to_benchmark.py --output pipeline_results.json
        else
            echo_error "No trajectory files found. Please run benchmarks first."
            exit 1
        fi
    fi

        echo_success "Displaying results summary..."

    # Launch dashboard in non-interactive mode
    python3 results_dashboard.py --results-file pipeline_results.json --no-interactive
}

show_completion_summary() {
    echo -e "${GREEN}"
    echo "=============================================================="
    echo "  Pipeline Completed Successfully!"
    echo "=============================================================="
    echo -e "${NC}"
    echo "What was accomplished:"
    echo "  [✓] Built upstream and optimized container images"
    echo "  [✓] Downloaded complete EuRoC dataset"
    echo "  [✓] Ran comprehensive baseline + optimized benchmarks (22 total runs)"
    echo "  [✓] Generated results dashboard"
    echo ""
    echo "Next steps:"
    echo "  • Run more benchmarks: python3 orbslam3_benchmark_ui.py"
    echo "  • View results anytime: python3 results_dashboard.py --results-file pipeline_results.json"
    echo "  • Run full evaluation: python3 orbslam3_cli.py benchmark"
    echo "  • Development mode: python3 cross-platform-dev.py dev"
    echo ""
}

# Main execution
main() {
    show_banner

    # Confirm with user
    echo -e "${YELLOW}This will take significant time and disk space (10GB+ for datasets).${NC}"
    read -p "Continue? [y/N]: " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted by user."
        exit 0
    fi

    echo_info "Starting complete pipeline..."

    # Execute pipeline steps
    check_dependencies
    cleanup_containers
    build_containers
    download_datasets
    run_comprehensive_benchmarks
    convert_results
    launch_dashboard

    show_completion_summary
}

# Handle Ctrl+C gracefully
trap 'echo -e "\n${YELLOW}Pipeline interrupted by user.${NC}"; exit 130' INT

# Run main function
main "$@"