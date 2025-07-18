param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("build","dev","test","benchmark","clean","help")]
    [string]$Command
)

$ImageTag = "orb-slam3:optimized"
$ContainerName = "orb-slam3-dev"

function Show-Help {
    Write-Host "ORB-SLAM3 Windows Development Tool" -ForegroundColor Cyan
    Write-Host "=================================="
    Write-Host ""
    Write-Host "Usage: .\windows-dev.ps1 [COMMAND]"
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Yellow
    Write-Host "  build      Build optimized container" -ForegroundColor White
    Write-Host "  dev        Start development environment" -ForegroundColor White
    Write-Host "  test       Run validation tests" -ForegroundColor White
    Write-Host "  benchmark  Run performance benchmarks" -ForegroundColor White
    Write-Host "  clean      Remove containers and images" -ForegroundColor White
    Write-Host "  help       Show this help message" -ForegroundColor White
    Write-Host ""
    Write-Host "Features:" -ForegroundColor Green
    Write-Host "  * Uses Docker Desktop for Windows"
    Write-Host "  * Includes our comprehensive optimization improvements"
    Write-Host "  * Virtual environment isolation"
    Write-Host "  * Cross-platform compatibility"
}

function Test-Docker {
    try {
        docker --version | Out-Null
        return $true
    }
    catch {
        Write-Host "Error: Docker not found!" -ForegroundColor Red
        Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop"
        return $false
    }
}

switch ($Command) {
    "build" {
        if (-not (Test-Docker)) { exit 1 }
        Write-Host "Building ORB-SLAM3 with our optimizations..." -ForegroundColor Green
        docker build -t $ImageTag .
    }
    "dev" {
        if (-not (Test-Docker)) { exit 1 }
        Write-Host "Starting development environment..." -ForegroundColor Blue
        Write-Host "Note: Container will mount current directory as /workspace"
        docker run -it --name $ContainerName -v ${PWD}:/workspace $ImageTag
    }
    "test" {
        if (-not (Test-Docker)) { exit 1 }
        Write-Host "Running validation tests..." -ForegroundColor Yellow
        docker run --rm -v ${PWD}:/workspace $ImageTag /bin/bash -c "cd /workspace && ./quick-test.sh"
    }
    "benchmark" {
        if (-not (Test-Docker)) { exit 1 }
        Write-Host "Running performance benchmarks..." -ForegroundColor Cyan
        Write-Host "Testing our Eigen 3.4.0 optimizations..."
        docker run --rm -v ${PWD}:/workspace $ImageTag /workspace/benchmark-test
    }
    "clean" {
        if (-not (Test-Docker)) { exit 1 }
        Write-Host "Cleaning up containers and images..." -ForegroundColor Red
        docker stop $ContainerName 2>$null
        docker rm $ContainerName 2>$null
        docker rmi $ImageTag 2>$null
        Write-Host "Cleanup completed!" -ForegroundColor Green
    }
    "help" {
        Show-Help
    }
}