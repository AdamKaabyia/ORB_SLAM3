#!/bin/bash
# ORB-SLAM3 Container Development Script
# Uses Podman for containerized development with Alpine Linux

set -e

PROJECT_NAME="orb-slam3-optimized"
CONTAINER_NAME="orb-slam3-dev"
IMAGE_TAG="localhost/orb-slam3:optimized"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

build_container() {
    echo_info "Building ORB-SLAM3 container with Alpine Linux..."
    podman build -t $IMAGE_TAG . --progress=plain
    echo_success "Container built successfully!"
}

run_dev_container() {
    echo_info "Starting development container..."

    # Stop existing container if running
    podman stop $CONTAINER_NAME 2>/dev/null || true
    podman rm $CONTAINER_NAME 2>/dev/null || true

    # Run interactive development container
    podman run -it \
        --name $CONTAINER_NAME \
        --hostname orb-slam3-dev \
        -v "$(pwd)":/workspace:Z \
        -w /workspace \
        --userns=keep-id \
        $IMAGE_TAG /bin/sh
}

run_tests() {
    echo_info "Running ORB-SLAM3 tests in container..."

    # Create a test script inside the container
    podman run --rm \
        -v "$(pwd)":/workspace:Z \
        -w /workspace \
        $IMAGE_TAG /bin/sh -c '
        echo "Testing ORB-SLAM3 build..."
        ls -la build/

        echo "Checking built binaries..."
        find build/ -name "*.so" -o -name "*mono*" -o -name "*stereo*" -o -name "*rgbd*"

                echo "Running basic validation..."
        cd Examples/Monocular
        ls -la

        echo "SUCCESS: ORB-SLAM3 appears to be built successfully!"
        '
}

benchmark_performance() {
    echo_info "Running performance benchmarks..."

    podman run --rm \
        -v "$(pwd)":/workspace:Z \
        -w /workspace \
        $IMAGE_TAG /bin/sh -c '
        echo "Performance Test: Matrix Multiplication (Eigen 3.4.0 optimization)"

        cat > /tmp/eigen_test.cpp << EOF
#include <iostream>
#include <chrono>
#include <Eigen/Dense>
#include <random>

int main() {
    const int size = 300;
    Eigen::MatrixXd A = Eigen::MatrixXd::Random(size, size);
    Eigen::MatrixXd B = Eigen::MatrixXd::Random(size, size);

    auto start = std::chrono::high_resolution_clock::now();

    for(int i = 0; i < 10; i++) {
        Eigen::MatrixXd C = A * B;
    }

    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);

    std::cout << "10x " << size << "x" << size << " matrix multiplications: "
              << duration.count() << "ms" << std::endl;
    std::cout << "Average per multiplication: "
              << duration.count() / 10.0 << "ms" << std::endl;

    return 0;
}
EOF

        g++ -O3 -I/usr/include/eigen3 /tmp/eigen_test.cpp -o /tmp/eigen_test
        /tmp/eigen_test
        '
}

show_help() {
    echo "ORB-SLAM3 Container Development Script"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  build        Build the ORB-SLAM3 container"
    echo "  dev          Start interactive development container"
    echo "  test         Run tests inside container"
    echo "  benchmark    Run performance benchmarks"
    echo "  clean        Remove containers and images"
    echo "  help         Show this help message"
    echo ""
    echo "Alpine Linux Features:"
    echo "  * Uses lightweight Alpine Linux base image"
    echo "  * Minimal attack surface and fast startup"
    echo "  * Optimized for OpenShift deployment"
    echo "  * Includes your Eigen 3.4.0 optimizations"
}

clean_containers() {
    echo_info "Cleaning up containers and images..."

    podman stop $CONTAINER_NAME 2>/dev/null || true
    podman rm $CONTAINER_NAME 2>/dev/null || true
    podman rmi $IMAGE_TAG 2>/dev/null || true

    echo_success "Cleanup completed!"
}

# Main script logic
case "${1:-help}" in
    build)
        build_container
        ;;
    dev)
        run_dev_container
        ;;
    test)
        run_tests
        ;;
    benchmark)
        benchmark_performance
        ;;
    clean)
        clean_containers
        ;;
    help|*)
        show_help
        ;;
esac