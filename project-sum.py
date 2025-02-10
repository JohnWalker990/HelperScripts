#!/usr/bin/env python3
"""
Summary:
This script recursively collects files with given file-type extensions from a provided base path,
cleans their content based on file type-specific rules (currently for .cs files), and aggregates the results
into one output. The output is printed to the console and, if possible, automatically copied to the clipboard.
Auto-generated directories and projects (e.g. bin, obj, Resources, Assets, *.Droid, *.WinUI) are excluded.
For .cs files, all "using" lines are removed and any empty lines preceding the "namespace" declaration are discarded.
The file header uses the following format:
=============
<solution-path>/<project-path>/<file>
-------------
<cleaned up code>

Usage:
    python code_summarizer.py <path> <extension1> [<extension2> ...]
Example:
    python code_summarizer.py "C:/Projects/MySolution" .cs .py
"""

import os
import sys
import argparse
import logging

# Try to import pyperclip to enable clipboard copy
try:
    import pyperclip
    clipboard_available = True
except ImportError:
    clipboard_available = False

def clean_code(file_path, extension):
    """
    Cleans the code of the given file based on its extension.
    For .cs files, removes all lines starting with 'using' (handling potential BOM characters)
    and removes any empty lines (or any lines) preceding the first occurrence of a line starting with 'namespace'.
    
    Parameters:
        file_path (str): The full path to the file.
        extension (str): The file extension (e.g. ".cs").
        
    Returns:
        str: The cleaned code as a single string or None if an error occurs.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        logging.error(f"Error reading file '{file_path}': {e}")
        return None

    if extension.lower() == ".cs":
        # Remove lines that start with "using" (ignoring leading whitespace and BOM)
        filtered_lines = [line for line in lines if not line.lstrip("\ufeff").lstrip().startswith("using ")]
        # Find the first line that starts with "namespace" to remove any leading empty or irrelevant lines
        namespace_index = None
        for idx, line in enumerate(filtered_lines):
            if line.lstrip().startswith("namespace"):
                namespace_index = idx
                break
        if namespace_index is not None:
            filtered_lines = filtered_lines[namespace_index:]
        cleaned_content = "".join(filtered_lines)
        return cleaned_content
    else:
        # For other file types, no specific cleanup rules are applied (but can be extended later)
        return "".join(lines)

def summarize_project_code(base_path, extensions):
    """
    Recursively traverses the base_path directory, processes files that match the given extensions,
    cleans their content based on file type-specific rules, and aggregates them into one output string.
    Auto-generated directories (bin, obj, Resources, Assets) and projects (e.g. *.Droid, *.WinUI) are excluded.
    
    Parameters:
        base_path (str): The root directory of the solution.
        extensions (list): A list of file extensions to process (e.g. [".cs", ".py"]).
        
    Returns:
        str: The aggregated output with file headers and cleaned code.
    """
    output_parts = []
    # Directories to exclude (case-insensitive)
    exclude_dirs = {"bin", "obj", "resources", "assets"}
    auto_generated_project_suffixes = {".droid", ".winui"}

    # Walk through the directory recursively
    for root, dirs, files in os.walk(base_path):
        # Filter out auto-generated directories and projects
        dirs[:] = [d for d in dirs
                   if d.lower() not in exclude_dirs
                   and not any(d.lower().endswith(suffix) for suffix in auto_generated_project_suffixes)]
        
        for file in files:
            # Check if file extension matches one of the provided extensions
            for ext in extensions:
                if file.lower().endswith(ext.lower()):
                    full_path = os.path.join(root, file)
                    # Calculate the relative path to the base_path and replace OS-specific separators with '/'
                    rel_path = os.path.relpath(full_path, base_path)
                    rel_path_forward = rel_path.replace(os.sep, "/")
                    cleaned_code = clean_code(full_path, ext)
                    if cleaned_code is None:
                        # Log and skip files that couldn't be processed
                        logging.error(f"Skipping file '{full_path}' due to previous errors.")
                        continue

                    # Create a header for the file using the specified format
                    header = f"=============\n{rel_path_forward}\n-------------\n"
                    part = f"{header}{cleaned_code}\n"
                    output_parts.append(part)
                    break  # Break inner loop when a matching extension is found
    return "".join(output_parts)

def main():
    """
    Parses command-line arguments, processes the files, and outputs the aggregated result.
    Also copies the result to the clipboard if possible.
    """
    parser = argparse.ArgumentParser(description="Summarize project code into one aggregated output.")
    parser.add_argument("path", type=str, help="Path to the solution directory (base path).")
    parser.add_argument("extensions", type=str, nargs="+", help="List of file type extensions to process (e.g. .cs, .py).")
    args = parser.parse_args()

    base_path = args.path
    extensions = args.extensions

    # Setup logging configuration
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Validate the base path
    if not os.path.exists(base_path):
        logging.error(f"The given path '{base_path}' does not exist.")
        sys.exit(1)
    if not os.path.isdir(base_path):
        logging.error(f"The given path '{base_path}' is not a directory.")
        sys.exit(1)

    logging.info(f"Processing files in directory: {base_path}")
    output = summarize_project_code(base_path, extensions)

    if output.strip() == "":
        logging.info("No files were processed. Please check the provided extensions or the directory content.")
    else:
        # Print the aggregated output to the console
        print(output)
        # Attempt to copy the output to the clipboard if possible
        if clipboard_available:
            try:
                pyperclip.copy(output)
                logging.info("Output has been successfully copied to the clipboard.")
            except Exception as e:
                logging.error(f"Failed to copy output to clipboard: {e}")
        else:
            logging.info("pyperclip module not available. Clipboard copy has been skipped.")

if __name__ == "__main__":
    main()
