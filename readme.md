# ReVanced Build Script

My Revanced app includes several modifications designed to support multiple apps, rather than using the components from the original Revanced.

This led to builds not working smoothly in the Android Manager app. To resolve this without going through a complex build process on a computer, I created a simple single script.

## Requirements

- Python 3.8+ (tested on macOS/Linux/Windows)
- Java (JRE/JDK) installed and available on PATH
  - Check with: `java -version`
  - If you see UnsupportedClassVersionError, install a newer Java (e.g., 17 or 21)
- Python packages:
  - `requests`
  - `questionary`

Install Python deps:
```bash
pip install -U requests questionary
```

## Quick Start

```bash
# 1) Provide the APK you want to patch and a target package name to filter the patches
python build.py --apk /path/to/app.apk --package com.example.app --output out

# 2) Include universal/common patches as well (off by default)
python build.py --apk /path/to/app.apk --package com.example.app --include-universal --output out

# 3) Actually run the patch command after selection (by default it only prints the command)
python build.py --apk /path/to/app.apk --package com.example.app --include-universal --run
```

What happens:
- Downloads the latest ReVanced CLI JAR and patches `.rvp` into `out/`
- Lists compatible patches for the given package (plus universal patches if `--include-universal`)
- Opens an interactive checklist (Space to select, Enter to confirm)
- If a patch has options, you’ll be prompted to set values (uses defaults if you skip)
- Prints the final CLI command; with `--run`, executes it and produces `out/patched.apk`

## Common Options

- `--apk PATH` (required unless you provide it interactively): The input APK to patch
- `--package NAME`: Filter patches that explicitly declare compatibility with this package (e.g., `com.kakao.talk`)
- `--include-universal`: When used with `--package`, also show universal/common patches
- `--exclusive` / `--no-exclusive`:
  - `--exclusive` (default): Only enable the patches you select
  - `--no-exclusive`: Start from the default patch set and add/remove based on your selection
- `--output DIR`: Output directory (default: `output`)
- `--run`: Execute the patch command after selection

Note:
- The selector pre-checks patches that are “Enabled: true” by default. You can untick them if you don’t want them.

## Examples

YouTube with only package-specific patches:
```bash
python build.py --apk ~/Downloads/KakaoTalk.apk --package com.kakao.talk --output out
```

YouTube including universal/common patches:
```bash
python build.py --apk ~/Downloads/KakaoTalk.apk --package com.kakao.talk --include-universal --output out
```

Run end-to-end and produce a patched APK:
```bash
python build.py --apk ~/Downloads/KakaoTalk.apk --package com.kakao.talk --include-universal --run
```

## How It Works

- Java check: runs `java -version` to ensure Java is available
- Downloads:
  - Latest ReVanced CLI (JAR)
  - Latest ReVanced patches bundle (`.rvp`)
- Lists patches via `revanced-cli list-patches` (with packages, versions, and options)
- Parses “Index/Name/Description/Enabled/Options/Compatible packages” output
- Interactive selection (Space to toggle, Enter to confirm)
- Option prompts:
  - Shows keys, defaults, types, and possible values (if any)
  - Choose from provided values or enter a custom value
  - Blank input means “null” (translates to `-Okey` without a value)
- Builds a `revanced-cli patch` command using `--ei` (by index) or `-e` (by name) and `-Okey[=value]`
- Prints the command; runs it if `--run` is given

## Platform Notes

- macOS/Linux:
  - Use `python3` if `python` points to Python 2 on your system
  - Ensure you run from a real terminal (Terminal/iTerm, GNOME Terminal, etc.) so the interactive UI renders properly
- Windows:
  - Use `py -3 build.py ...` or `python` depending on your setup
  - Prefer Windows Terminal or PowerShell for proper TUI rendering
  - If `java` is not recognized, add your Java bin folder to PATH and restart the terminal

## Troubleshooting

- “Java is not installed or not found in PATH.”:
  - Install Java and ensure `java -version` works in your terminal, then retry
- “UnsupportedClassVersionError”:
  - Your Java is too old for the CLI. Install a newer Java (e.g., 17 or 21)
- Terminal UI issues:
  - Run in a real terminal (not an IDE’s limited console). Resize the window if necessary
- Patching fails for specific versions:
  - Ensure your APK version is within the patch’s compatible versions (shown in the list)
  - Try a different APK version supported by the patch

## Output

- Downloads saved to: `output/` (or the directory you specify with `--output`)
  - `revanced-cli-*.jar` and `patches-*.rvp`
  - `patched.apk` after a successful run with `--run`

## Notes

- This helper focuses on selection and option configuration; installation/uninstallation (ADB) is out of scope
- Use `--no-exclusive` if you want to start from the default patch set instead of only your selections