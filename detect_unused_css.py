"""
Developer: leetz-kowd
Project: NuxtClean
Date: 2023-10-30
Version: 1.0.0

Description:
A tool for Nuxt (Vue 3) developers to detect:
- Unused CSS class definitions
- Console.log / warn / error debug statements
- Dead code (unused exports)
- Unused named imports

It scans through .vue, .js, .ts, .css, .scss, and .sass files
"""

import re
from pathlib import Path

# File types to search
CSS_EXTENSIONS = [".css", ".scss", ".sass"] # CSS and preprocessor files
CODE_EXTENSIONS = [".vue", ".js", ".ts"] # JavaScript and TypeScript files
EXCLUDE_FOLDERS = ["node_modules", ".output", ".nuxt"] # Folders to exclude from search


def get_all_files(root, extensions):
    files = []
    for path in Path(root).rglob("*"):
        if path.suffix in extensions:
            if any(excluded in path.parts for excluded in EXCLUDE_FOLDERS):
                continue
            files.append(path)
    return files


# ----------------- Unused CSS Class Detection -----------------

def extract_css_classes(css_text):
    pattern = re.compile(r"\.([a-zA-Z0-9_\-]+)")
    return set(pattern.findall(css_text))


def extract_used_classes(file_content):
    pattern = re.compile(r'class[=:]?\s*["\']([^"\']+)["\']')
    matches = pattern.findall(file_content)
    classes = set()
    for match in matches:
        for cls in match.strip().split():
            classes.add(cls.strip())
    return classes


def find_unused_css_classes(project_path):
    css_files = get_all_files(project_path, CSS_EXTENSIONS)
    code_files = get_all_files(project_path, CODE_EXTENSIONS)

    declared_classes = set()
    for file in css_files:
        try:
            content = file.read_text(encoding="utf-8")
            declared_classes.update(extract_css_classes(content))
        except Exception as e:
            print(f"Failed to read {file}: {e}")

    used_classes = set()
    for file in code_files:
        try:
            content = file.read_text(encoding="utf-8")
            used_classes.update(extract_used_classes(content))
        except Exception as e:
            print(f"Failed to read {file}: {e}")

    unused = declared_classes - used_classes
    return sorted(unused)


# ----------------- Console Log / Warn / Error Detection -----------------

def find_console_logs(project_path):
    code_files = get_all_files(project_path, CODE_EXTENSIONS)
    log_occurrences = {
        "log": [],
        "warn": [],
        "error": []
    }

    # Define subpath patterns to exclude (relative to project path)
    excluded_console_paths = [
        "public/cloudflare/js/jquery.min.js"
    ]

    for file in code_files:
        # Convert to relative path for easy matching
        relative_path = file.relative_to(project_path)

        # Skip exact or matching subpath
        if any(str(relative_path).startswith(p) for p in excluded_console_paths):
            continue

        try:
            with file.open("r", encoding="utf-8") as f:
                for i, line in enumerate(f, start=1):
                    stripped = line.strip()
                    if "console.log" in stripped:
                        log_occurrences["log"].append((relative_path, i, stripped))
                    elif "console.warn" in stripped:
                        log_occurrences["warn"].append((relative_path, i, stripped))
                    elif "console.error" in stripped:
                        log_occurrences["error"].append((relative_path, i, stripped))
        except Exception as e:
            print(f"Failed to read {file}: {e}")
    return log_occurrences



# ----------------- Dead Code Detection (Unused JS/TS exports) -----------------

def extract_named_exports(content):
    pattern = re.compile(r'export\s+(?:const|function|class)\s+([a-zA-Z0-9_]+)')
    return set(pattern.findall(content))


def extract_possible_usages(content):
    return set(re.findall(r'\b([a-zA-Z0-9_]+)\b', content))


def find_dead_code_exports(project_path):
    code_files = get_all_files(project_path, [".js", ".ts"])
    declared_exports = {}
    all_usages = set()

    for file in code_files:
        try:
            content = file.read_text(encoding="utf-8")
            exports = extract_named_exports(content)
            if exports:
                declared_exports[file] = exports
            all_usages.update(extract_possible_usages(content))
        except Exception as e:
            print(f"Failed to read {file}: {e}")

    dead_code = []
    for file, exports in declared_exports.items():
        unused = exports - all_usages
        if unused:
            for item in unused:
                dead_code.append((file.relative_to(project_path), item))
    return dead_code

def find_unused_imports(project_path):
    code_files = get_all_files(project_path, [".js", ".ts", ".vue"])
    unused_imports = []

    import_pattern = re.compile(r'import\s+{([^}]+)}\s+from\s+[\'"][^\'"]+[\'"]')
    script_block_pattern = re.compile(r'<script(?:\s+setup)?[^>]*>(.*?)</script>', re.DOTALL)

    for file in code_files:
        try:
            content = file.read_text(encoding="utf-8")
            original_lines = content.splitlines()

            # Only analyze <script> blocks for .vue files
            if file.suffix == ".vue":
                script_matches = script_block_pattern.findall(content)
                if not script_matches:
                    continue
                script_content = "\n".join(script_matches)
                full_text = script_content
                lines = script_content.splitlines()
            else:
                full_text = content
                lines = original_lines

            # Go line-by-line to detect imports and whether they’re used
            for i, line in enumerate(lines, start=1):
                match = import_pattern.search(line)
                if match:
                    imported_names = [name.strip() for name in match.group(1).split(",")]

                    # Remove the line from text to avoid false positive (import counts as usage)
                    check_text = full_text.replace(line, "")

                    for name in imported_names:
                        if not re.search(rf'\b{name}\b', check_text):
                            unused_imports.append((file.relative_to(project_path), i, name))

        except Exception as e:
            print(f"Failed to process {file}: {e}")

    return unused_imports



# ----------------- CLI Runner -----------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect unused CSS classes, console logs, and dead code in a Nuxt project"
    )
    parser.add_argument("--path", required=True, help="")

    args = parser.parse_args()
    project_path = args.path


    print("\n Unused CSS Classes:\n")
    unused_classes = find_unused_css_classes(project_path)
    if unused_classes:
        for cls in unused_classes:
            print(f"  - .{cls}")
    else:
        print(" All declared classes appear to be used!")


    print("\n Detected console statements:\n")
    console_logs = find_console_logs(project_path)
    has_logs = False
    for log_type, logs in console_logs.items():
        if logs:
            has_logs = True
            print(f" console.{log_type}:")
            for filepath, lineno, line in logs:
                print(f"    - {filepath} [line {lineno}]: {line}")
            print()
    if not has_logs:
        print(" No console.log, console.warn, or console.error statements found.")


    print("\n Dead Code (Unused Exports):\n")
    dead_code = find_dead_code_exports(project_path)
    if dead_code:
        for filepath, name in dead_code:
            print(f"  - {filepath}: {name}")
    else:
        print(" No unused exports found.")


    print("\n Unused Named Imports:\n")
    unused_imports = find_unused_imports(project_path)
    if unused_imports:
        for filepath, lineno, name in unused_imports:
            print(f"  - {filepath} [line {lineno}]: {name}")
    else:
        print(" All named imports appear to be used.")