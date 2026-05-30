#!/usr/bin/env python
"""
Third-Party Clone Bootstrap Script
Parses third_party/manifest.yaml and handles cloning of vendor dependencies.
"""
import os
import sys
import argparse
import re
import subprocess

def parse_manifest(manifest_path):
    """Simple parser to read repositories from manifest.yaml."""
    if not os.path.exists(manifest_path):
        print(f"Error: Manifest not found at {manifest_path}")
        return {}
        
    with open(manifest_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    repos = {}
    # Use simple regex block matching to identify keys and properties
    blocks = re.split(r'\n  (\w+[-_]?\w+):', content)
    
    if len(blocks) > 1:
        # First block contains top level header
        for i in range(1, len(blocks), 2):
            repo_name = blocks[i]
            properties_text = blocks[i+1]
            
            # Extract url, purpose, target_dir
            url_match = re.search(r'url:\s*([^\s\n]+)', properties_text)
            target_match = re.search(r'target_dir:\s*([^\s\n]+)', properties_text)
            purpose_match = re.search(r'purpose:\s*([^\n]+)', properties_text)
            
            repos[repo_name] = {
                "url": url_match.group(1) if url_match else "",
                "target_dir": target_match.group(1) if target_match else f"third_party/{repo_name}",
                "purpose": purpose_match.group(1).strip() if purpose_match else ""
            }
    return repos

def clone_repos(repos, dry_run=True):
    """Iterate and clone listed repositories."""
    print(f"Dry Run: {dry_run}")
    print(f"Found {len(repos)} candidate repositories in manifest.\n")
    
    success_count = 0
    for name, data in repos.items():
        print(f"Repository: {name}")
        print(f"  URL: {data['url']}")
        print(f"  Purpose: {data['purpose']}")
        print(f"  Target: {data['target_dir']}")
        
        if dry_run:
            print("  [DRY RUN] Would clone to target directory.")
            success_count += 1
        else:
            if os.path.exists(data['target_dir']) and os.listdir(data['target_dir']):
                print(f"  [SKIPPED] Directory {data['target_dir']} is already occupied.")
                success_count += 1
                continue
                
            os.makedirs(os.path.dirname(data['target_dir']), exist_ok=True)
            print(f"  [CLONING] Cloning {data['url']} ...")
            try:
                cmd = ["git", "clone", data['url'], data['target_dir']]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                if res.returncode == 0:
                    print("  [SUCCESS] Successfully cloned.")
                    success_count += 1
                else:
                    print(f"  [FAILED] Git returned error: {res.stderr.strip()}")
            except Exception as e:
                print(f"  [FAILED] Execution error: {str(e)}")
        print("-" * 50)
        
    return success_count == len(repos)

def main():
    parser = argparse.ArgumentParser(description="Clone third-party vendors listed in manifest.yaml")
    parser.add_argument("--clone", action="store_true", help="Execute actual git clone actions.")
    args = parser.parse_args()
    
    manifest_path = os.path.join("third_party", "manifest.yaml")
    repos = parse_manifest(manifest_path)
    
    if not repos:
        print("No repositories parsed from manifest.yaml.")
        sys.exit(1)
        
    is_dry_run = not args.clone
    success = clone_repos(repos, dry_run=is_dry_run)
    
    if is_dry_run:
        print("\nManifest parsed successfully. To execute cloning, re-run with: --clone")
        sys.exit(0)
    else:
        if success:
            print("\nAll third party packages successfully synchronized.")
            sys.exit(0)
        else:
            print("\nSome repositories failed to clone.")
            sys.exit(1)

if __name__ == "__main__":
    main()
