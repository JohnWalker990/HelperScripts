# README – HelperScripts

Welcome to the **HelperScripts** repository! This repository contains small scripts that help with everyday tasks or can be useful for various workflows. Currently, it includes two scripts, both licensed under the [GNU General Public License v3.0 (GPL-3.0)](https://www.gnu.org/licenses/gpl-3.0.en.html):

1. [**generate_tree.py**](#generate_treepy)
2. [**project-sum.py**](#project-sumpy)

---

## generate_tree.py

This script generates a directory tree for a specified path, excluding certain directories and files. The result is copied to the clipboard if possible, otherwise it is written to a text file in the script folder.

### How It Works

- Recursively scans the specified root folder and all of its subfolders.
- Certain directories (e.g., `bin`, `obj`, `.git`, etc.) are excluded by default.
- Certain files or file extensions (e.g., `*.dll`, `*.pdb`, `*.exe`) are also excluded by default.
- The generated directory tree is copied to the clipboard if possible. If clipboard access is not available, it is written to a text file in the script folder.

### Usage

1. **Run the script**:
   ```bash
   python generate_tree.py <path>
   ```
   - **<path>**: The folder for which the tree should be generated.
2. **Result**:
   - If `pyperclip` is installed, the directory tree is copied to your clipboard.
   - Otherwise, a text file named after the last directory in `<path>` is created in the script's folder.

Feel free to customize the lists of directories and files to exclude according to your needs.

---

## project-sum.py

This script recursively collects files of specified extensions (e.g., `.cs`, `.py`) within a project directory, cleans them based on file-type-specific rules, and aggregates their content into a single output. If possible, it also copies the final text to the clipboard.

### How It Works

- Recursively searches through all folders, skipping certain generated directories (e.g., `bin`, `obj`, `Resources`, `Assets`, etc.).
- Processes files matching the specified extensions (e.g., `.cs`, `.py`) and applies file-specific cleanup:
  - **.cs files**: Removes all lines starting with `using` and deletes any empty lines before the first occurrence of a line starting with `namespace`.
- Outputs the aggregated result to the console and copies it to the clipboard if the `pyperclip` module is available.

### Usage

1. **Run the script**:
   ```bash
   python project-sum.py <path> <extension1> [<extension2> ...]
   ```
   - **<path>**: The base folder to search through (e.g., the root directory of a .NET solution).
   - **<extension1> [<extension2> ...]**: The file types you want to process (e.g., `.cs`, `.py`).
   
2. **Example**:  
   ```bash
   python project-sum.py "C:/Projects/MySolution" .cs .py
   ```
   
3. **Output**:  
   - The script prints the aggregated text of all processed files to the console.  
   - If `pyperclip` is installed, the script also copies the text to your clipboard.
   
---

## License

This repository is licensed under the [GNU General Public License v3.0 (GPL-3.0)](https://www.gnu.org/licenses/gpl-3.0.en.html).  
Please note that when redistributing or publishing your changes, you must adhere to the GPL-3.0 requirements, including giving appropriate credit to the original authors.

---

## Contributing

If you have suggestions for additional useful scripts or enhancements, feel free to create an **Issue** or open a **Pull Request**:

1. **Fork** this repository  
2. **Implement** your feature or fix  
3. **Open** a Pull Request  

---

## Contact

For questions or feedback, please open an [Issue](../../issues) or reach out directly.  

Enjoy using **HelperScripts**!