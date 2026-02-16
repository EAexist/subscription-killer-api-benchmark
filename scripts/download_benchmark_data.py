#!/usr/bin/env python3
"""
Download Benchmark Data from GitHub Releases
Downloads the latest benchmark data files from GitHub releases.
"""

import argparse
import os
import sys
import requests
from pathlib import Path
import zipfile
import tempfile

def download_file_from_github(repo_owner, repo_name, release_tag, file_name, output_dir):
    """Download a specific file from GitHub release."""
    url = f"https://github.com/{repo_owner}/{repo_name}/releases/download/{release_tag}/{file_name}"
    
    print(f"Downloading {file_name} from release {release_tag}...")
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        output_path = Path(output_dir) / file_name
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"✅ Downloaded: {output_path}")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error downloading {file_name}: {e}")
        return False

def download_latest_release_data(repo_owner, repo_name, output_dir="results/reports"):
    """Download the latest benchmark data from GitHub releases."""
    try:
        # Get latest release info
        api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        response = requests.get(api_url)
        response.raise_for_status()
        
        release_data = response.json()
        release_tag = release_data['tag_name']
        
        print(f"📥 Found latest release: {release_tag}")
        print(f"📂 Downloading to: {output_dir}")
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Files to download
        files_to_download = [
            'ai-metrics.csv',
            'supplementary-metrics.csv', 
            'latest-benchmark-results.md'
        ]
        
        success_count = 0
        for file_name in files_to_download:
            if download_file_from_github(repo_owner, repo_name, release_tag, file_name, output_dir):
                success_count += 1
        
        print(f"\n🎉 Downloaded {success_count}/{len(files_to_download)} files successfully!")
        return success_count > 0
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting release info: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Download benchmark data from GitHub releases')
    parser.add_argument('--repo-owner', default='EAexist', help='GitHub repository owner (default: EAexist)')
    parser.add_argument('--repo-name', default='subscription-killer-api', help='GitHub repository name (default: subscription-killer-api)')
    parser.add_argument('--release-tag', help='Specific release tag to download (default: latest)')
    parser.add_argument('--output-dir', default='results/reports', help='Output directory (default: results/reports)')
    
    args = parser.parse_args()
    
    if args.release_tag:
        # Download specific release
        files_to_download = ['ai-metrics.csv', 'supplementary-metrics.csv', 'latest-benchmark-results.md']
        success_count = 0
        for file_name in files_to_download:
            if download_file_from_github(args.repo_owner, args.repo_name, args.release_tag, file_name, args.output_dir):
                success_count += 1
        
        print(f"\n🎉 Downloaded {success_count}/{len(files_to_download)} files from release {args.release_tag}!")
    else:
        # Download latest release
        download_latest_release_data(args.repo_owner, args.repo_name, args.output_dir)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
