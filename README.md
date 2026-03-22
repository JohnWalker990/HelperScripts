# README – HelperScripts

Welcome to the **HelperScripts** repository! This repository contains small scripts that help with everyday tasks or can be useful for various workflows. Currently, it includes three scripts, all licensed under the [GNU General Public License v3.0 (GPL-3.0)](https://www.gnu.org/licenses/gpl-3.0.en.html):

1. [**generate_tree.py**](#generate_treepy)
2. [**project-sum.py**](#project-sumpy)
3. [**download-youtube-audio.py**](#download-youtube-audiopy)

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
- You can add extra directory names to exclude via `--exclude` (case-insensitive).
- Processes files matching the specified extensions (e.g., `.cs`, `.py`) and applies file-specific cleanup:
  - **.cs files**: Removes all lines starting with `using` and deletes any empty lines before the first occurrence of a line starting with `namespace`.
- Applies Unicode normalization (default: `basic`) to avoid hidden characters from breaking summaries.
- Outputs the aggregated result to the console and copies it to the clipboard if the `pyperclip` module is available.

### Usage

1. **Run the script**:
   ```bash
   python project-sum.py <path> <extension1> [<extension2> ...] [--exclude <dir1> <dir2> ...] [--normalize none|basic|ascii] [-v]
   ```
   - **<path>**: The base folder to search through (e.g., the root directory of a .NET solution).
   - **<extension1> [<extension2> ...]**: The file types you want to process (e.g., `.cs`, `.py`).
   - **--exclude**: Additional directory names to skip (case-insensitive). Example: `--exclude build dist`.
   - **--normalize**: Text cleanup mode:
     - `none`: no normalization
     - `basic` (default): safe cleanup (NBSP/ZWSP/soft-hyphen etc.)
     - `ascii`: additionally replaces smart quotes/dashes/ellipsis
   - **-v / --verbose**: Enable debug logging.
   
2. **Example**:  
   ```bash
   python project-sum.py "C:/Projects/MySolution" .cs .py --exclude build dist --normalize basic
   ```
   
3. **Output**:  
   - The script prints the aggregated text of all processed files to the console.  
   - If `pyperclip` is installed, the script also copies the text to your clipboard.
   
---

## download-youtube-audio.py

This script downloads a YouTube URL in two modes:
- By default, it downloads audio-only and converts it to high-quality `mp3`.
- With `--video`, it downloads the full video in the best available quality and saves it as `mp4` for broad playback compatibility.

If you paste a playlist-style link interactively, the script can ask whether you want the whole playlist and whether you want audio-only or full video. For non-interactive runs, watch URLs with `&list=...` still default to the current video only, while pure playlist URLs default to the full playlist.

### Requirements

- Python package: `yt-dlp`
- `ffmpeg` and `ffprobe` available in your `PATH`

Install `yt-dlp` with:

```bash
python -m pip install --user yt-dlp
```

### Usage

1. **Run the script**:
   ```bash
   python download-youtube-audio.py <youtube-url>
   ```
   - If you omit `<youtube-url>`, the script prompts you to paste one.

2. **Optional flags**:
   - `-o, --output-dir`: Choose where the downloaded files are saved.
   - `--video`: Download the full video in best available quality as `mp4`.
   - `--audio-only`: Force audio-only mode.
   - `--playlist`: Download the full playlist instead of only the current video.
   - `--single`: Force a single-video download when the URL also contains playlist information.
   - `--audio-format`: Convert the extracted audio to a specific format such as `mp3`, `m4a`, or `flac`. Default: `mp3`.
   - `--cookies-from-browser`: Reuse cookies from a local browser profile such as `edge:Default` when YouTube asks you to sign in.
   - `--cookies`: Use an exported `cookies.txt` file instead.
   - `--list-browser-profiles`: Show detected local profiles you can pass to `--cookies-from-browser`.

3. **Examples**:
   ```bash
   python download-youtube-audio.py https://www.youtube.com/watch?v=BaW_jenozKc
   python download-youtube-audio.py "https://www.youtube.com/watch?v=abc123&list=playlist123"
   python download-youtube-audio.py --video https://www.youtube.com/watch?v=BaW_jenozKc
   python download-youtube-audio.py --cookies-from-browser edge:Default https://www.youtube.com/watch?v=BaW_jenozKc
   python download-youtube-audio.py -o D:/Music https://youtu.be/BaW_jenozKc
   python download-youtube-audio.py --playlist https://www.youtube.com/playlist?list=...
   ```

### Interactive Playlist Flow

When you paste a playlist link in an interactive terminal session, the script can do this:

1. Ask whether to download the whole playlist.
2. Ask whether to download audio-only or full video.
3. Download the selected result in best available quality.

When a playlist is downloaded with an authenticated browser profile or cookies, unavailable/private items are skipped and the rest of the playlist continues.
When you rerun the same playlist into the same output folder and mode, the script scans the playlist against its resume archive and starts at the first unfinished item instead of restarting from item 1.
Existing files already present in the output folder are also added to the resume archive automatically, so older partial runs can be continued without starting from the beginning.

### Bot Check

If YouTube responds with "Sign in to confirm you're not a bot", the script now automatically retries with detected local browser profiles. You can still force a specific profile or an exported cookies file manually:

```bash
python download-youtube-audio.py --list-browser-profiles
python download-youtube-audio.py --cookies-from-browser edge:Default "<youtube-url>"
python download-youtube-audio.py --cookies "C:/path/to/cookies.txt" "<youtube-url>"
```

If `--cookies-from-browser edge:...` or `chrome:...` fails with a DPAPI decryption error on Windows, use a Firefox profile or an exported `cookies.txt` file instead.
If a detected browser profile has stale or rotated YouTube cookies, the script warns once, can try the next detected profile for the remaining playlist items, and tells you to refresh that browser login or cookies export.

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
