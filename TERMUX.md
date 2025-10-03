# Setup guide for termux

This is a guide to set up a Termux environment for building.

## Prerequisites
1. Install Termux from F-Droid (recommended) or Github releases.
2. Open Termux and update packages:
   ```sh
    pkg update && pkg upgrade
    ```
3. Install required packages:
   ```sh
   pkg install git openjdk-17 python
    ```
4. Clone the repository:
   ```sh
   git clone https://git.naijun.dev/ReVanced/revanced-build-script.git
   cd revanced-build-script
    ```
5. Install required Python packages:
   ```sh
   pip install -r requirements.txt
   ```
6. You must prepare the APK file to be patched in advance.

## Building
1. Run the build script:
    ```sh
    ./build.py --apk ~/Downloads/KakaoTalk.apk --package com.kakao.talk --include-universal --run
    ```

Notes:
- You can use the spacebar to select or deselect patches.
- Use the Arrow keys to navigate and Enter to confirm your selection.
- When patching KakaoTalk, enable the “Ignore Check Package Name” patch to change the package name, and activate updatePermissions and updateProvider in the options.