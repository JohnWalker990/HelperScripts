# README – HelperScripts

Welcome to the **HelperScripts** repository! This repository contains small scripts that help with everyday tasks or can be useful for various workflows. Currently, it includes two scripts, both licensed under the [GNU General Public License v3.0 (GPL-3.0)](https://www.gnu.org/licenses/gpl-3.0.en.html):

1. [**generate_filtered_tree.py**](#generate_filtered_treepy)
2. [**code_summarizer.py**](#code_summarizerpy)

---

## generate_filtered_tree.py

This script generates a directory tree for a specified path, excluding certain directories and files. The result is saved in a text file (*project_tree.txt*).

### How It Works

- Recursively scans the specified root folder and all of its subfolders.
- Certain directories (e.g., `bin`, `obj`, `.git`, etc.) are excluded by default.
- Certain files or file extensions (e.g., `*.dll`, `*.pdb`, `*.exe`) are also excluded by default.
- The generated directory tree is saved in a file named `project_tree.txt` located in the provided project path.

### Usage

1. **Run the script**:  
   ```bash
   python generate_filtered_tree.py
   ```
2. **Enter the project path**: Once started, you will be prompted to input the path where the directory tree should be generated.
3. **Result**: The output is saved as `project_tree.txt` in the same directory you provided.

Feel free to customize the lists of directories and files to exclude according to your needs.

---

## code_summarizer.py

This script recursively collects files of specified extensions (e.g., `.cs`, `.py`) within a project directory, cleans them based on file-type-specific rules, and aggregates their content into a single output. If possible, it also copies the final text to the clipboard.

### How It Works

- Recursively searches through all folders, skipping certain generated directories (e.g., `bin`, `obj`, `Resources`, `Assets`, etc.).
- Processes files matching the specified extensions (e.g., `.cs`, `.py`) and applies file-specific cleanup:
  - **.cs files**: Removes all lines starting with `using` and deletes any empty lines before the first occurrence of a line starting with `namespace`.
- Outputs the aggregated result to the console and copies it to the clipboard if the `pyperclip` module is available.

### Usage

1. **Run the script**:  
   ```bash
   python code_summarizer.py <path> <extension1> [<extension2> ...]
   ```
   - **<path>**: The base folder to search through (e.g., the root directory of a .NET solution).
   - **<extension1> [<extension2> ...]**: The file types you want to process (e.g., `.cs`, `.py`).
   
2. **Example**:  
   ```bash
   python code_summarizer.py "C:/Projects/MySolution" .cs .py
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