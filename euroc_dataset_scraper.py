#!/usr/bin/env python3
"""
EuRoC Dataset Scraper for ORB-SLAM3 Testing
Downloads datasets from http://robotics.ethz.ch/~asl-datasets/ijrr_euroc_mav_dataset/

Targets:
- machine_hall/ (MH_01_easy to MH_05_difficult)
- vicon_room1/ (V1_01_easy to V1_03_difficult)
- vicon_room2/ (V2_01_easy to V2_03_difficult)
"""

import os
import zipfile
import argparse
from pathlib import Path
import time
from urllib.parse import urljoin
import hashlib
import sys

# Try to import requests, urllib as fallback
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    import urllib.request
    import urllib.error
    HAS_REQUESTS = False

# Try to import tqdm, use simple progress as fallback
try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

def simple_progress_bar(current, total, width=50):
    """Simple progress bar fallback when tqdm is not available"""
    percent = current / total
    filled = int(width * percent)
    bar = '=' * filled + '-' * (width - filled)
    print(f'\r[{bar}] {percent:.1%} ({current}/{total})', end='', flush=True)
    if current == total:
        print()  # New line when complete

class EuRoCDatasetScraper:
    def __init__(self, base_dir="datasets/EuRoC"):
        self.base_url = "http://robotics.ethz.ch/~asl-datasets/ijrr_euroc_mav_dataset/"
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        # Dataset definitions
        self.datasets = {
            "machine_hall": [
                "MH_01_easy", "MH_02_easy", "MH_03_medium",
                "MH_04_difficult", "MH_05_difficult"
            ],
            "vicon_room1": [
                "V1_01_easy", "V1_02_medium", "V1_03_difficult"
            ],
            "vicon_room2": [
                "V2_01_easy", "V2_02_medium", "V2_03_difficult"
            ]
        }

    def get_download_url(self, location, sequence):
        """Generate download URL for a specific sequence"""
        return f"{self.base_url}{location}/{sequence}/{sequence}.zip"

    def download_file(self, url, destination, show_progress=True):
        """Download file with progress bar"""
        try:
            if HAS_REQUESTS:
                # Use requests if available
                response = requests.get(url, stream=True)
                response.raise_for_status()
                total_size = int(response.headers.get('content-length', 0))

                with open(destination, 'wb') as file:
                    downloaded = 0
                    if HAS_TQDM and show_progress and total_size > 0:
                        # Use tqdm if available
                        with tqdm(desc=destination.name, total=total_size, unit='B', unit_scale=True, unit_divisor=1024) as pbar:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    file.write(chunk)
                                    downloaded += len(chunk)
                                    pbar.update(len(chunk))
                    else:
                        # Simple progress fallback
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                file.write(chunk)
                                downloaded += len(chunk)
                                if show_progress and total_size > 0:
                                    simple_progress_bar(downloaded, total_size)
                                elif show_progress:
                                    print(f'\rDownloaded: {downloaded // 1024}KB', end='', flush=True)
            else:
                # Fallback to urllib
                import urllib.request
                import urllib.error
                with urllib.request.urlopen(url) as response:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    chunk_size = 8192

                    with open(destination, 'wb') as file:
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            file.write(chunk)
                            downloaded += len(chunk)
                            if show_progress and total_size > 0:
                                simple_progress_bar(downloaded, total_size)
                            elif show_progress:
                                print(f'\rDownloaded: {downloaded // 1024}KB', end='', flush=True)

            if show_progress:
                print(f"\nCompleted: {destination.name}")
            return True

        except Exception as e:
            print(f"Error downloading {url}: {e}")
            return False

    def extract_dataset(self, zip_path, extract_to):
        """Extract dataset zip file"""
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
            print(f"Extracted: {zip_path.name}")
            return True
        except zipfile.BadZipFile as e:
            print(f"Error extracting {zip_path}: {e}")
            return False

    def verify_dataset(self, dataset_dir):
        """Verify dataset structure and essential files"""
        essential_files = [
            "mav0/cam0/data.csv",
            "mav0/cam1/data.csv",
            "mav0/imu0/data.csv",
            "mav0/state_groundtruth_estimate0/data.csv"
        ]

        missing_files = []
        for file_path in essential_files:
            full_path = dataset_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)

        if missing_files:
            print(f"Warning: Missing files in {dataset_dir.name}: {missing_files}")
            return False
        return True

    def download_sequence(self, location, sequence, extract=True):
        """Download and optionally extract a single sequence"""
        url = self.get_download_url(location, sequence)

        # Create directory structure
        location_dir = self.base_dir / location
        location_dir.mkdir(exist_ok=True)

        zip_path = location_dir / f"{sequence}.zip"
        extract_dir = location_dir / sequence

        # Skip if already exists and verified
        if extract_dir.exists() and self.verify_dataset(extract_dir):
            print(f"* {sequence} already exists and verified")
            return True

        print(f"Downloading {sequence} from {location}...")

        # Download
        if not self.download_file(url, zip_path):
            return False

        # Extract
        if extract:
            # Create the sequence-specific directory
            extract_dir.mkdir(exist_ok=True)
            if self.extract_dataset(zip_path, extract_dir):
                # Verify extraction
                if self.verify_dataset(extract_dir):
                    print(f"* {sequence} downloaded and verified")
                    # Remove zip file to save space
                    zip_path.unlink()
                    return True
                else:
                    print(f"! {sequence} failed verification")
                    return False

        return True

    def download_all(self, locations=None, extract=True):
        """Download all datasets or specific locations"""
        if locations is None:
            locations = list(self.datasets.keys())

        total_sequences = sum(len(self.datasets[loc]) for loc in locations if loc in self.datasets)
        downloaded = 0
        failed = []

        print(f"Starting download of {total_sequences} sequences...")
        print(f"Base directory: {self.base_dir.absolute()}")

        for location in locations:
            if location not in self.datasets:
                print(f"Warning: Unknown location '{location}', skipping...")
                continue

            print(f"\n=== Downloading {location} sequences ===")

            for sequence in self.datasets[location]:
                if self.download_sequence(location, sequence, extract):
                    downloaded += 1
                else:
                    failed.append(f"{location}/{sequence}")

                # Small delay to be respectful to server
                time.sleep(1)

        print(f"\n=== Download Summary ===")
        print(f"Successfully downloaded: {downloaded}/{total_sequences}")
        if failed:
            print(f"Failed downloads: {failed}")

        return downloaded, failed

    def list_available(self):
        """List all available datasets"""
        print("Available EuRoC datasets:")
        for location, sequences in self.datasets.items():
            print(f"\n{location}:")
            for seq in sequences:
                url = self.get_download_url(location, seq)
                local_path = self.base_dir / location / seq
                status = "* Downloaded" if local_path.exists() else "- Available"
                print(f"  {status} {seq}")
                print(f"    URL: {url}")

    def get_dataset_paths(self):
        """Get paths to all downloaded datasets"""
        dataset_paths = {}

        for location, sequences in self.datasets.items():
            dataset_paths[location] = {}
            for sequence in sequences:
                seq_path = self.base_dir / location / sequence
                if seq_path.exists():
                    dataset_paths[location][sequence] = seq_path

        return dataset_paths

    def create_dataset_config(self):
        """Create configuration file for ORB-SLAM3 testing"""
        config = {
            "base_directory": str(self.base_dir.absolute()),
            "datasets": self.get_dataset_paths(),
            "total_sequences": sum(len(seqs) for seqs in self.get_dataset_paths().values())
        }

        config_path = self.base_dir / "dataset_config.json"
        import json
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, default=str)

        print(f"Created dataset configuration: {config_path}")
        return config_path

def main():
    parser = argparse.ArgumentParser(description="Download EuRoC datasets for ORB-SLAM3 testing")
    parser.add_argument("--location", "-l",
                       choices=["machine_hall", "vicon_room1", "vicon_room2"],
                       help="Specific location to download")
    parser.add_argument("--sequence", "-s",
                       help="Specific sequence to download (requires --location)")
    parser.add_argument("--list", action="store_true",
                       help="List available datasets")
    parser.add_argument("--no-extract", action="store_true",
                       help="Download only, don't extract")
    parser.add_argument("--base-dir", default="datasets/EuRoC",
                       help="Base directory for downloads")

    args = parser.parse_args()

    scraper = EuRoCDatasetScraper(args.base_dir)

    if args.list:
        scraper.list_available()
        return

    if args.sequence:
        if not args.location:
            print("Error: --sequence requires --location")
            return

        success = scraper.download_sequence(
            args.location,
            args.sequence,
            extract=not args.no_extract
        )
        if success:
            scraper.create_dataset_config()
        return

    # Download specified location or all
    locations = [args.location] if args.location else None
    downloaded, failed = scraper.download_all(locations, extract=not args.no_extract)

    if downloaded > 0:
        scraper.create_dataset_config()
        print(f"\nDatasets ready for ORB-SLAM3 testing!")

if __name__ == "__main__":
    main()