import os
import argparse

# Try to import pyperclip to enable clipboard copy
try:
    import pyperclip
    clipboard_available = True
except ImportError:
    clipboard_available = False

def generate_filtered_tree(path, exclude_dirs=None, exclude_files=None):
    """
    Generates a directory tree for a given path, excluding specified directories and files.

    Args:
        path (str): The root directory to start scanning.
        exclude_dirs (list): List of directory names to exclude.
        exclude_files (list): List of file names or extensions to exclude.

    Returns:
        str: Directory tree as a text representation.
    """
    if exclude_dirs is None:
        exclude_dirs = ["bin", "obj", "Properties", ".vs", ".idea", ".vscode", ".git", "Platforms", "Resources"]
    if exclude_files is None:
        exclude_files = ["*.dll", "*.pdb", "*.log", "*.exe", ".dockerignore", ".editorconfig", ".gitignore", "project_tree.txt"]

    def should_exclude(item, is_dir):
        """Check if the item should be excluded based on its name or type."""
        if is_dir:
            return item in exclude_dirs
        for pattern in exclude_files:
            # Summary: Check if file name ends with the pattern (ignoring the asterisk)
            if item.endswith(pattern.strip("*")):
                return True
        return False

    def recurse(directory, prefix=""):
        """Recursively generate the tree structure."""
        entries = []
        for item in sorted(os.listdir(directory)):
            full_path = os.path.join(directory, item)
            if os.path.isdir(full_path):
                if should_exclude(item, is_dir=True):
                    continue
                # Summary: Append directory entry
                entries.append(f"{prefix}├── {item}/")
                # Summary: Recursively generate subtree and append only if it's not empty
                subtree = recurse(full_path, prefix + "│   ")
                if subtree:
                    entries.append(subtree)
            else:
                if should_exclude(item, is_dir=False):
                    continue
                # Summary: Append file entry
                entries.append(f"{prefix}├── {item}")
        return "\n".join(entries)

    return recurse(path)

# Example usage
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a filtered directory tree.")
    parser.add_argument("path", type=str, help="Path to the project directory.")
    args = parser.parse_args()

    project_path = args.path
    if not os.path.isdir(project_path):
        print("Invalid directory path.")
        raise SystemExit(1)

    tree = generate_filtered_tree(project_path)

    copied = False
    if clipboard_available:
        try:
            pyperclip.copy(tree)
            print("Directory tree copied to clipboard.")
            copied = True
        except Exception as e:
            print(f"Failed to copy to clipboard: {e}")

    if not copied:
        base_name = os.path.basename(os.path.abspath(os.path.normpath(project_path))) + ".txt"
        output_dir = os.path.dirname(__file__)
        output_file = os.path.join(output_dir, base_name)
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(tree)
        print(f"Directory tree saved to: {output_file}")
