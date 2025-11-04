"""
Developer: leetz-kowd
Project: NuxtClean
Date: 2023-10-30
Version: 1.0.1 (Variable Detection Fix)

Description:
A tool for Nuxt (Vue 3) developers to detect:
- Unused CSS class definitions
- Console.log / warn / error debug statements
- Dead code (unused exports)
- Unused named imports
- Unused variables (local and global)
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

    # First pass: collect all code content from all files for global usage check
    all_project_content = ""
    for file in code_files:
        try:
            content = file.read_text(encoding="utf-8")
            
            # For .vue files, extract script and template blocks
            if file.suffix == ".vue":
                script_matches = script_block_pattern.findall(content)
                template_match = re.search(r'<template[^>]*>(.*?)</template>', content, re.DOTALL)
                
                file_content = "\n".join(script_matches)
                if template_match:
                    file_content += "\n" + template_match.group(1)
                
                all_project_content += file_content + "\n"
            else:
                all_project_content += content + "\n"
        except Exception as e:
            print(f"Failed to read {file}: {e}")

    # Second pass: check each import against ALL project content
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
                lines = script_content.splitlines()
            else:
                lines = original_lines

            # Go line-by-line to detect imports
            for i, line in enumerate(lines, start=1):
                match = import_pattern.search(line)
                if match:
                    imported_names = [name.strip() for name in match.group(1).split(",")]

                    # Remove the import line from global content to avoid false positive
                    check_text = all_project_content.replace(line, "")

                    for name in imported_names:
                        # Check if used ANYWHERE in the project
                        if not re.search(rf'\b{re.escape(name)}\b', check_text):
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


def find_all_unused_variables(project_path):
    """
    Find variables that are:
    1. Not used in their own file (local unused)
    2. Not used anywhere in the entire project (global unused)
    
    A variable is considered *used* if it appears more than once 
    (one declaration + one or more usages).
    """
    code_files = get_all_files(project_path, [".js", ".ts", ".vue"])
    unused_vars = []
    
    script_block_pattern = re.compile(r'<script(?:\s+setup)?[^>]*>(.*?)</script>', re.DOTALL)
    template_block_pattern = re.compile(r'<template[^>]*>(.*?)</template>', re.DOTALL)
    
    # First pass: collect all code content from entire project
    all_project_content = ""
    for file in code_files:
        try:
            content = file.read_text(encoding="utf-8")
            
            file_content = ""
            # For .vue files, extract script and template blocks
            if file.suffix == ".vue":
                script_matches = script_block_pattern.findall(content)
                template_match = template_block_pattern.search(content)
                
                file_content += "\n".join(script_matches)
                if template_match:
                    file_content += "\n" + template_match.group(1)
            else:
                # For .js/.ts files, use full content
                file_content = content
                
            all_project_content += file_content + "\n"
        except Exception as e:
            print(f"Failed to read {file}: {e}")
    
    # Second pass: check each declared variable
    for file in code_files:
        try:
            full_text = file.read_text(encoding="utf-8")
            
            # --- Determine Content for Declaration Finding ---
            if file.suffix == ".vue":
                script_match = script_block_pattern.search(full_text)
                if not script_match:
                    continue
                script_content = script_match.group(1)
                
                # For local usage check, use both script and template content
                template_match = template_block_pattern.search(full_text)
                local_content = script_content
                if template_match:
                    local_content += "\n" + template_match.group(1)
            else:
                script_content = full_text
                local_content = full_text
            
            # Find all variable declarations
            # Look for: const/let/var NAME = ... OR destructuring { NAME } = ...
            decl_pattern = re.compile(r"\b(?:const|let|var)\s+([a-zA-Z_$][\w$]*)\s*=")
            declared = decl_pattern.findall(script_content)
            
            # Add variables from object destructuring (simple case)
            destruct_pattern = re.compile(r"\b(?:const|let|var)\s*\{([^}]+)\}\s*=")
            for destruct_match in destruct_pattern.findall(script_content):
                 declared.extend([d.strip() for d in destruct_match.split(',') if d.strip()])
            
            # Check each declared variable
            for var in set(declared): # Use set to handle duplicates from destructuring/regex
                var_usage_pattern = re.compile(rf"\b{re.escape(var)}\b")
                
                # --- Check local usage (in same file) ---
                local_matches = var_usage_pattern.findall(local_content)
                # A variable is used if it appears more than once (Declaration + Usage)
                local_used = len(local_matches) > 1
                local_unused = not local_used
                
                # --- Check global usage (entire project) ---
                global_matches = var_usage_pattern.findall(all_project_content)
                global_used = len(global_matches) > 1
                global_unused = not global_used
                
                # Add to report with appropriate scope
                if global_unused:
                    # Filter out common false positives for global check if they are imports/props
                    # This simple tool won't perfectly handle scope, but prioritize global findings
                    unused_vars.append((file.relative_to(project_path), var, "global"))
                elif local_unused:
                    unused_vars.append((file.relative_to(project_path), var, "local"))
        
        except Exception as e:
            print(f"Failed to process {file}: {e}")
    
    return unused_vars


# Create report
def export_all_to_master_csv(css_classes, console_logs, dead_exports, unused_imports, unused_packages, unused_variables, output_path="reports/nuxtclean_report.csv"):
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Type", "File", "Line Number", "Code", "Scope"])

        for cls in css_classes:
            writer.writerow(["Unused CSS", "", "", f".{cls}", ""])

        for level, logs in console_logs.items():
            for file, line, statement in logs:
                writer.writerow([f"Console {level}", str(file), line, statement, ""])

        for file, name in dead_exports:
            writer.writerow(["Dead Export", str(file), "", name, ""])

        for file, line, name in unused_imports:
            writer.writerow(["Unused Import", str(file), line, name, ""])

        for pkg in unused_packages:
            writer.writerow(["Unused Package", "package.json", "", pkg, ""])
        
        for file, var, scope in unused_variables:
            writer.writerow(["Unused Variable", str(file), "", var, scope])

    print(f"\n Exported full report to {output_path}")


# ----------------- CLI Runner -----------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect unused CSS classes, packages, variables, and search for console logs in a Nuxt project"
    )
    parser.add_argument("--path", required=True, help="Path to the Nuxt project directory")

    args = parser.parse_args()
    project_path = Path(args.path)


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
        for filepath, var, scope in unused_vars:
            scope_label = f"({scope})" if scope else ""
            print(f"  - {filepath}: {var} {scope_label}")
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