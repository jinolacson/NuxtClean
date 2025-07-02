"""
Developer: leetz-kowd
Project: NuxtVuln
Date: 2023-10-30
Version: 1.0.0

Description:
A security scanning tool for Nuxt (Vue 3) projects.

Detects common frontend security vulnerabilities such as:
- Use of `eval()` (can lead to remote code execution)
- Unsafe `v-html` bindings (potential XSS vector)
- Dynamic `setTimeout` and `setInterval` with string or untrusted function names
- Unpatched NPM package vulnerabilities via `npm audit`

Supports scanning of .vue, .js, .ts files and ignores node_modules, build directories, and specified vendor scripts.

Outputs results in CSV format for easy review and reporting.
"""


import argparse
import os
import re
import subprocess
import json
import csv

def parse_args():
    parser = argparse.ArgumentParser(description='NuxtClean - Scan Nuxt project for possible vulnerabilities')
    parser.add_argument('--path', type=str, required=True, help='Path to the Nuxt project directory')
    return parser.parse_args()

# 1. Check for NPM vulnerabilities
def check_npm_vulnerabilities(project_path):
    print("Checking NPM vulnerabilities...")
    try:
        result = subprocess.run(['npm', 'audit', '--json'], cwd=project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = json.loads(result.stdout)
        advisories = data.get("advisories", {})
        if advisories:
            for _, advisory in advisories.items():
                print(f"[{advisory['severity'].upper()}] {advisory['module_name']}: {advisory['title']}")
        else:
            print(" No known NPM vulnerabilities found.")
    except Exception as e:
        print(f" Error during npm audit: {e}")

"""
Flag unsafe usage
1. setTimeout(userInput, 1000) (when userInput is not a function)
2. v-html = "userInput" (when userInput is not sanitized)
3. eval("userInput") (when userInput is not sanitized)
"""

def scan_files_for_security_patterns(project_path, output_csv_path="reports/nuxt_vuln_report.csv"):
    print(" Scanning for insecure code patterns...")

    insecure_patterns = {
        'eval_usage': r'\beval\s*\((.*?)\)',
        'v_html': r'v-html\s*=\s*["\'][^"\']+["\']',
        'settimeout_string': r'\bset(?:Timeout|Interval)\s*\(\s*["\'].*?["\']',
        'settimeout_variable': r'\bset(?:Timeout|Interval)\s*\(\s*[a-zA-Z_$][\w$]*\s*,\s*.*?\)',
    }

    exclude_dirs = {'node_modules', '.output', '.nuxt', 'dist', 'build'}

    excluded_files = {
        os.path.normpath(os.path.join(project_path, 'public/cloudflare/js/jquery.min.js')),
    }

    results = []

    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            if file.endswith(('.js', '.ts', '.vue')):
                path = os.path.normpath(os.path.join(root, file))

                if path in excluded_files:
                    continue

                try:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines, start=1):
                            for label, pattern in insecure_patterns.items():
                                if re.search(pattern, line):
                                    results.append({
                                        "type": label,
                                        "location": path,
                                        "line number": i,
                                        "code": line.strip()
                                    })
                except Exception as e:
                    print(f" Could not read {path}: {e}")

    # Write results to CSV
    if results:
        with open(output_csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['type', 'location', 'line number', 'code']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)

        print(f" Report saved to {output_csv_path}")
    else:
        print(" No insecure patterns found.")




def main():
    args = parse_args()
    project_path = args.path

    if not os.path.isdir(project_path):
        print(f" Invalid path: {project_path}")
        return

    # Run all checks
    check_npm_vulnerabilities(project_path)
    scan_files_for_security_patterns(project_path)

if __name__ == "__main__":
    main()
