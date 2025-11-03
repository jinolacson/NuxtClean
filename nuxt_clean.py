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

import re, csv, json
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

def find_unused_packages(project_path):
    pkg_json_path = Path(project_path) / "package.json"
    if not pkg_json_path.exists():
        print("  No package.json found.")
        return []

    with pkg_json_path.open(encoding="utf-8") as f:
        pkg_data = json.load(f)

    # Combine dependencies and devDependencies
    dependencies = pkg_data.get("dependencies", {})
    dev_dependencies = pkg_data.get("devDependencies", {})
    all_packages = list(dependencies.keys()) + list(dev_dependencies.keys())

    # Get all code files where packages may be imported
    code_files = get_all_files(project_path, [".js", ".ts", ".vue"])
    all_code = ""
    for file in code_files:
        try:
            text = file.read_text(encoding="utf-8")
            all_code += text + "\n"
        except Exception as e:
            print(f"Failed to read {file}: {e}")

    unused = []
    for pkg in all_packages:
        # Escape special characters in package name (like @)
        pattern = re.compile(rf"(from\s+['\"]{re.escape(pkg)}['\"]|require\(['\"]{re.escape(pkg)}['\"]\))")
        if not pattern.search(all_code):
            unused.append(pkg)

    return sorted(unused)


def find_unused_variables_in_file(file_path):
    """
    Detect variables declared with const, let, or var that are never used.
    Only works for JS, TS, and <script> blocks in .vue files.
    """
    try:
        text = Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        print(f" Failed to read {file_path}: {e}")
        return []

    # Extract only <script> content if it's a Vue file
    if file_path.suffix == ".vue":
        match = re.search(r"<script[^>]*>(.*?)</script>", text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            return []

    # Find all variable declarations
    decl_pattern = re.compile(r"\b(?:const|let|var)\s+([a-zA-Z_$][\w$]*)")
    declared = decl_pattern.findall(text)

    unused_vars = []
    for var in declared:
        # Match word boundaries, ignore the declaration line
        var_usage_pattern = re.compile(rf"\b{re.escape(var)}\b")
        matches = var_usage_pattern.findall(text)

        if len(matches) <= 1:
            unused_vars.append(var)

    return unused_vars

# wrapper of find_unused_variables_in_file() function
def find_all_unused_variables(project_path):
    unused_vars = []
    code_files = get_all_files(project_path, [".js", ".ts", ".vue"])
    for file in code_files:
        result = find_unused_variables_in_file(file)
        for var in result:
            unused_vars.append((file, var))
    return unused_vars


# Create report
def export_all_to_master_csv(css_classes, console_logs, dead_exports, unused_imports, unused_packages, unused_variables, output_path="reports/nuxtclean_report.csv"):
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Type", "File", "Line Number", "Code"])

        for cls in css_classes:
            writer.writerow(["Unused CSS", "", "", f".{cls}"])

        for level, logs in console_logs.items():
            for file, line, statement in logs:
                writer.writerow([f"Console {level}", str(file), line, statement])

        for file, name in dead_exports:
            writer.writerow(["Dead Export", str(file), "", name])

        for file, line, name in unused_imports:
            writer.writerow(["Unused Import", str(file), line, name])

        for pkg in unused_packages:
            writer.writerow(["Unused Package", "package.json", "", pkg])
        
        for file, var in unused_variables:
            writer.writerow(["Unused Variable", str(file), "", var])

    print(f"\n Exported full report to {output_path}")


# ----------------- CLI Runner -----------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect unused CSS classes, packages, variables, and search for console logs in a Nuxt project"
    )
    parser.add_argument("--path", required=True, help="Path to the Nuxt project directory")

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
    dead_exports = find_dead_code_exports(project_path)
    if dead_exports:
        for filepath, name in dead_exports:
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
    
    
    print("\n  Unused NPM Packages:\n")
    unused_packages = find_unused_packages(project_path)
    if unused_packages:
        for pkg in unused_packages:
            print(f"  - {pkg}")
    else:
        print(" All dependencies appear to be used.")
    
    print("\n  Unused Variables:\n")
    unused_vars = find_all_unused_variables(project_path)
    if unused_vars:
        for filepath, var in unused_vars:
            print(f"  - {filepath}: {var}")
    else:
        print("  All declared variables appear to be used.")
    
    export_all_to_master_csv(
        unused_classes,
        console_logs,
        dead_exports,
        unused_imports,
        unused_packages,
        unused_vars,
        output_path="reports/nuxt_clean_report.csv"
    )
