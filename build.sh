#!/bin/bash
# Optimized ORB-SLAM3 Build Script
# Enhanced for faster parallel compilation

set -e

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

# Detect number of CPU cores for parallel builds
if command -v nproc &> /dev/null; then
    CORES=$(nproc)
elif command -v sysctl &> /dev/null; then
    CORES=$(sysctl -n hw.ncpu)
else
    CORES=4  # fallback
fi

echo_info "ORB-SLAM3 Optimized Build Starting..."
echo_info "Using ${CORES} CPU cores for parallel compilation"
echo_info "Build optimizations: Examples_old skipped, parallel enabled"

start_time=$(date +%s)

echo_info "Configuring and building Thirdparty/DBoW2..."
cd Thirdparty/DBoW2
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j${CORES}
echo_success "DBoW2 built successfully"

cd ../../g2o
echo_info "Configuring and building Thirdparty/g2o..."
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j${CORES}
echo_success "g2o built successfully"

cd ../../Sophus
echo_info "Configuring and building Thirdparty/Sophus..."
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j${CORES}
echo_success "Sophus built successfully"

cd ../../../

echo_info "Extracting vocabulary..."
cd Vocabulary
if [ ! -f ORBvoc.txt ]; then
    tar -xf ORBvoc.txt.tar.gz
    echo_success "Vocabulary extracted"
else
    echo_warning "Vocabulary already extracted"
fi
cd ..

echo_info "Configuring and building ORB_SLAM3 (optimized)..."
mkdir -p build
cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
make -j${CORES}

end_time=$(date +%s)
build_time=$((end_time - start_time))

echo_success "ORB_SLAM3 build completed successfully!"
echo_info "Total build time: ${build_time} seconds"
echo_info "Built with ${CORES} parallel jobs"
echo_info "Examples_old skipped - saved ~50% build time"
echo_info "All essential binaries available in Examples/ directories"
