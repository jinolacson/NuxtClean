"""
Developer: leetz-kowd
Project: nuxt_tool
Date: 2023-10-30
Version: 1.0.0
"""

import argparse
import subprocess
import os

def parse_args():
    parser = argparse.ArgumentParser(description='Nuxt Tool - Run cleaning or vulnerability checks')
    parser.add_argument('--mode', choices=['clean', 'vuln'], required=True, help='Which tool to run: clean or vuln')
    parser.add_argument('--path', type=str, required=True, help='Path to the Nuxt project directory')
    return parser.parse_args()

def run_tool(mode, path):
    script_map = {
        'clean': 'nuxt_clean.py',
        'vuln': 'nuxt_vuln.py'
    }

    script = script_map.get(mode)
    if not os.path.exists(script):
        print(f" Script not found: {script}")
        return

    print(f" Running {script} on {path}")
    try:
        subprocess.run(['python', script, '--path', path], check=True)
    except subprocess.CalledProcessError as e:
        print(f" {mode} script failed: {e}")

def main():
    args = parse_args()
    run_tool(args.mode, args.path)

if __name__ == "__main__":
    main()
