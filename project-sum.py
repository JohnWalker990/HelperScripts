#!/usr/bin/env python3
import os
import sys
import argparse
import logging
import unicodedata
from typing import Tuple, Optional

# Try to import pyperclip to enable clipboard copy
try:
    import pyperclip
    clipboard_available = True
except ImportError:
    clipboard_available = False


# <summary>
# Robustly read a text file with multiple encoding fallbacks.
# Tries UTF-8 (strict), UTF-8 with BOM, UTF-16 (with BOM), CP1252, ISO-8859-1;
# as a last resort, decodes with UTF-8 using 'surrogateescape' to avoid crashes.
# Returns the decoded text and the name of the encoding used.
# </summary>
def read_text_robust(file_path: str) -> Tuple[str, str]:
    # Read raw bytes once
    data = None
    try:
        with open(file_path, "rb") as f:
            data = f.read()
    except Exception as e:
        raise RuntimeError(f"Error opening file '{file_path}': {e}")

    # Fast path: strict UTF-8
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        pass

    # UTF-8 with BOM
    try:
        return data.decode("utf-8-sig"), "utf-8-sig"
    except UnicodeDecodeError:
        pass

    # UTF-16/UTF-32 if BOM present (Python auto-detects endianness)
    if data.startswith(b"\xff\xfe") or data.startswith(b"\xfe\xff"):
        try:
            return data.decode("utf-16"), "utf-16"
        except UnicodeDecodeError:
            pass
    if data.startswith(b"\xff\xfe\x00\x00") or data.startswith(b"\x00\x00\xfe\xff"):
        try:
            return data.decode("utf-32"), "utf-32"
        except UnicodeDecodeError:
            pass

    # Common Windows encodings
    for enc in ("cp1252", "latin-1"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue

    # Last resort: keep undecodable bytes via surrogateescape
    try:
        return data.decode("utf-8", errors="surrogateescape"), "utf-8-surrogateescape"
    except Exception as e:
        # Should not normally happen
        raise RuntimeError(f"Failed to decode '{file_path}' with fallbacks: {e}")


# <summary>
# Normalize Unicode in a conservative way that is safe for source code.
# - NFC composition to canonical form
# - Replace NBSP and narrow NBSP with regular spaces
# - Strip zero-width chars and soft hyphens
# - Replace non-breaking hyphen with regular hyphen
# </summary>
def normalize_text_basic(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    # Translation table for invisible/problematic whitespace/hyphenation
    tr = {
        0x00A0: " ",  # NBSP
        0x202F: " ",  # Narrow NBSP
        0xFEFF: "",   # BOM/ZWNBS
        0x200B: "",   # Zero Width Space
        0x200C: "",   # Zero Width Non-Joiner
        0x200D: "",   # Zero Width Joiner
        0x2060: "",   # Word Joiner
        0x00AD: "",   # Soft hyphen (shy)
        0x2011: "-",  # Non-breaking hyphen
    }
    return text.translate(tr)


# <summary>
# Optionally normalize typographic punctuation to ASCII.
# This is more aggressive and intended only if you explicitly want ASCII-only punctuation.
# </summary>
def normalize_text_ascii_punct(text: str) -> str:
    text = normalize_text_basic(text)
    tr = {
        0x2018: "'", 0x2019: "'",  # ‘ ’
        0x201C: '"', 0x201D: '"',  # “ ”
        0x2013: "-", 0x2014: "-",  # – —
        0x2026: "...",             # …
    }
    return text.translate(tr)


# <summary>
# Apply selected normalization: 'none' | 'basic' | 'ascii'.
# </summary>
def apply_normalization(text: str, mode: str) -> str:
    if mode == "none":
        return text
    if mode == "ascii":
        return normalize_text_ascii_punct(text)
    # default/basic
    return normalize_text_basic(text)


# <summary>
# Cleans the code of the given file based on its extension:
#   - For .cs: removes 'using' lines and all lines before the first 'namespace'.
#   - Otherwise: returns file as-is (after robust reading and normalization).
# Uses robust decoding and Unicode normalization to avoid UnicodeDecodeError.
# </summary>
def clean_code(file_path: str, extension: str, normalize_mode: str) -> Optional[str]:
    """
    Cleans the code of the given file based on its extension.
    For .cs files, removes all lines starting with 'using' (handling potential BOM characters)
    and removes any lines preceding the first occurrence of a line starting with 'namespace'.

    Returns:
        str | None: The cleaned code as a single string or None if an error occurs.
    """
    try:
        text, used_enc = read_text_robust(file_path)
        text = apply_normalization(text, normalize_mode)
        # Normalize line endings to LF to keep output consistent
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        logging.debug(f"Decoded '{file_path}' using {used_enc}")
    except Exception as e:
        logging.error(f"Error reading file '{file_path}': {e}")
        return None

    if extension.lower() == ".cs":
        lines = text.split("\n")
        # Remove lines that start with "using" (ignoring leading whitespace and BOM remnants)
        filtered_lines = [ln for ln in lines if not ln.lstrip("\ufeff").lstrip().startswith("using ")]
        # Find first 'namespace' to drop everything before it
        namespace_index = next((i for i, l in enumerate(filtered_lines) if l.lstrip().startswith("namespace")), None)
        if namespace_index is not None:
            filtered_lines = filtered_lines[namespace_index:]
        cleaned = "\n".join(filtered_lines)
        # Ensure trailing newline for readability
        if not cleaned.endswith("\n"):
            cleaned += "\n"
        return cleaned

    # Default: return as-is (already normalized)
    if not text.endswith("\n"):
        text += "\n"
    return text


# <summary>
# Traverses the base path, excludes certain folders and projects,
# processes files with the given extensions and aggregates the result.
# Uses robust decoding and normalization to avoid crashes on mixed encodings.
# </summary>
def summarize_project_code(base_path: str, extensions, normalize_mode: str, extra_exclude_dirs=None) -> str:
    """
    Recursively traverses the base_path directory, processes files that match the given extensions,
    cleans their content based on file type-specific rules, and aggregates them into one output string.
    Auto-generated directories (bin, obj, Resources, Assets) and projects (e.g. *.Droid, *.WinUI) are excluded.
    """
    output_parts = []

    # Lower-cased names for case-insensitive filtering
    exclude_dirs = {
        "bin", "obj", "resources", "assets", "apim", "apiops", "management-api",
        "attachments", "employee-masterdata", "example-integration", "configurations",
        "payroll-mock", "functions.policymanagement.unittests", "functions.tenantmanagement.unittests", "migrations",
        "reporting", "decorator", "client", ".git", ".vscode", ".idea", ".vs", "venv", ".venv", "node_modules", 
        ".node_modules", ".angular"
    }
    if extra_exclude_dirs:
        exclude_dirs.update(d.strip().lower() for d in extra_exclude_dirs if d.strip())
    auto_generated_project_suffixes = {".droid", ".winui", ".unittests", ".tests"}

    # Walk through the directory recursively
    for root, dirs, files in os.walk(base_path):
        # Filter out excluded directories and auto-generated projects (case-insensitive)
        dirs[:] = [
            d for d in dirs
            if d.lower() not in exclude_dirs
            and not any(d.lower().endswith(suffix) for suffix in auto_generated_project_suffixes)
        ]

        for file in files:
            for ext in extensions:
                if file.lower().endswith(ext.lower()):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, base_path).replace(os.sep, "/")
                    cleaned_code = clean_code(full_path, ext, normalize_mode)
                    if cleaned_code is None:
                        logging.error(f"Skipping file '{full_path}' due to previous errors.")
                        continue

                    header = f"=============\n{rel_path}\n"
                    output_parts.append(f"{header}{cleaned_code}\n")
                    break  # do not re-process the same file for other extensions

    return "".join(output_parts)


# <summary>
# CLI entry point: parses arguments, processes files, prints and optionally copies to clipboard.
# </summary>
def main():
    """
    Parses command-line arguments, processes the files, and outputs the aggregated result.
    Also copies the result to the clipboard if possible.
    """
    parser = argparse.ArgumentParser(description="Summarize project code into one aggregated output.")
    parser.add_argument("path", type=str, help="Path to the solution directory (base path).")
    parser.add_argument("extensions", type=str, nargs="+",
                        help="List of file type extensions to process (e.g. .cs, .py).")
    parser.add_argument("--normalize", choices=["none", "basic", "ascii"], default="basic",
                        help="Unicode normalization mode: "
                             "'none' = disabled, "
                             "'basic' = safe cleanup (NBSP/ZWSP/soft-hyphen etc.), "
                             "'ascii' = also replace smart quotes/dashes/ellipsis.")
    parser.add_argument("--exclude", nargs="*", default=[],
                        help="Additional directory names to exclude (case-insensitive).")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging.")
    args = parser.parse_args()

    base_path = args.path
    extensions = args.extensions
    normalize_mode = args.normalize

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(levelname)s: %(message)s")

    if not os.path.exists(base_path):
        logging.error(f"The given path '{base_path}' does not exist.")
        sys.exit(1)
    if not os.path.isdir(base_path):
        logging.error(f"The given path '{base_path}' is not a directory.")
        sys.exit(1)

    logging.info(f"Processing files in directory: {base_path}")
    output = summarize_project_code(base_path, extensions, normalize_mode, args.exclude)

    if not output.strip():
        logging.info("No files were processed. Please check the provided extensions or the directory content.")
    else:
        print(output)
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
