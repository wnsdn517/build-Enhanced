#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReVanced Build Script - APK Handler
APK 검색, 패키지명 추출, APKM 변환
"""

import os
import re
import subprocess
import zipfile
import tempfile
from pathlib import Path
from shutil import which, copy2, rmtree
from typing import List, Optional
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import DEFAULT_EXCLUDE_DIRS, MERGE_THREADS
from utils import print_success, print_warning, print_info, print_error, Colors

# ==================== APK 검색 ====================
def find_apk_files_recursively(root_dir: str = '.', 
                               exclude_dirs: Optional[List[str]] = None) -> List[Path]:
    if exclude_dirs is None:
        exclude_dirs = DEFAULT_EXCLUDE_DIRS
    
    root = Path(root_dir).resolve()
    found = []
    
    print_info(f"Searching in: {root}")
    
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if file.lower().endswith(('.apk', '.apkm', '.xapk')):
                path = Path(current) / file
                found.append(path)
                
                size_mb = path.stat().st_size / (1024 * 1024)
                rel = path.relative_to(root)
                print_success(f"{rel} ({size_mb:.1f} MB)")
    
    found.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    return found

def select_apk_interactively(apk_files: List[Path]) -> Optional[str]:
    if not apk_files:
        return None
    
    if len(apk_files) == 1:
        return str(apk_files[0])
    
    try:
        from questionary import select
        
        choices = []
        for apk in apk_files:
            size = apk.stat().st_size / (1024 * 1024)
            mtime = datetime.fromtimestamp(apk.stat().st_mtime)
            label = f"{apk.name} ({size:.1f} MB, {mtime:%Y-%m-%d %H:%M})"
            choices.append({"name": label, "value": str(apk)})
        
        result = select("Select APK/APKM:", choices=choices).ask()
        if result is None:
            print_info("Selection cancelled")
        return result
    
    except ImportError:
        print(f"\n{Colors.BOLD}[SELECT]{Colors.RESET} Found {len(apk_files)} files:")
        for i, apk in enumerate(apk_files, 1):
            print(f"  {i}. {apk.name}")
        
        while True:
            try:
                choice = input(f"Select (1-{len(apk_files)}, 'q' to quit): ").strip().lower()
                if choice == 'q':
                    print_info("Selection cancelled")
                    return None
                
                idx = int(choice) - 1
                if 0 <= idx < len(apk_files):
                    return str(apk_files[idx])
                else:
                    print_error(f"Enter 1-{len(apk_files)}")
            except (ValueError, KeyboardInterrupt):
                print_info("Selection cancelled")
                return None

# ==================== 패키지명 추출 ====================
def extract_package_name_from_apk(apk_path: str) -> Optional[str]:
    apk_path = Path(apk_path)
    
    if not apk_path.exists():
        return None
    
    # Method 1: aapt
    if which('aapt'):
        try:
            result = subprocess.run(
                ['aapt', 'dump', 'badging', str(apk_path)],
                capture_output=True,
                text=True,
                timeout=15,
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if line.startswith('package:'):
                        match = re.search(r"name='([^']+)'", line)
                        if match:
                            pkg = match.group(1)
                            print_success(f"Extracted via aapt: {pkg}")
                            return pkg
        except Exception as e:
            print_warning(f"aapt failed: {e}")
    
    # Method 2: Parse AndroidManifest.xml
    try:
        with zipfile.ZipFile(apk_path, 'r') as zf:
            try:
                manifest_data = zf.read('AndroidManifest.xml')
                text = manifest_data.decode('utf-8', errors='ignore')
                
                patterns = [
                    r'package="([^"]+)"',
                    r'([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*){2,})',
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        if '.' in match and len(match.split('.')) >= 2:
                            if re.match(r'^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$', 
                                      match, re.IGNORECASE):
                                print_success(f"Extracted from manifest: {match}")
                                return match
            except KeyError:
                pass
    except Exception as e:
        print_warning(f"Manifest parsing failed: {e}")
    
    return None

def prompt_package_name(auto_detected: Optional[str] = None) -> Optional[str]:
    if auto_detected:
        print(f"\n{Colors.GREEN}[DETECTED]{Colors.RESET} Package: {Colors.BOLD}{auto_detected}{Colors.RESET}")
        return auto_detected
    else:
        print_warning("Could not detect package name")
        print_info("Install 'aapt' for better detection:")
        print("       Ubuntu/Debian: sudo apt install aapt")
        
        try:
            from questionary import text
            pkg = text(
                "Enter package name (or press Enter for all patches):",
                default=""
            ).ask()
            
            if pkg is None:
                print_info("Cancelled")
                return None
            
            return pkg.strip() or None
        
        except ImportError:
            pkg = input("Enter package name (Enter for all, 'q' to quit): ").strip()
            if pkg.lower() == 'q':
                print_info("Cancelled")
                return None
            return pkg or None

# ==================== APKM 변환 ====================
def merge_with_apkeditor(apkeditor_jar: str, apk_files: List[str], 
                        output_path: str) -> str:
    temp_dir = Path(tempfile.mkdtemp())
    
    try:
        print_info("Preparing files for merge...")
        for apk in apk_files:
            dest = temp_dir / Path(apk).name
            copy2(apk, dest)
            print(f"  • {Path(apk).name}")
        
        print_info("Running APKEditor merge...")
        cmd = [
            'java', '-jar', apkeditor_jar,
            'm',
            '-i', str(temp_dir),
            '-o', output_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=300
        )
        
        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            raise RuntimeError(f"APKEditor failed: {error_msg[:500]}")
        
        if not Path(output_path).exists():
            raise RuntimeError("APKEditor did not create output")
        
        print_success("Merge completed")
        return output_path
    
    except subprocess.TimeoutExpired:
        raise RuntimeError("APKEditor timed out")
    except Exception as e:
        raise RuntimeError(f"APKEditor merge failed: {e}")
    finally:
        if temp_dir.exists():
            rmtree(temp_dir)

def convert_apkm_to_apk(apkm_path: str, output_dir: Optional[str] = None,
                        merge_splits: bool = True, 
                        cache_mgr = None) -> str:
    apkm_path = Path(apkm_path)
    
    if not apkm_path.exists():
        raise FileNotFoundError(f"APKM not found: {apkm_path}")
    
    print(f"\n{Colors.CYAN}[APKM]{Colors.RESET} Converting: {Colors.BOLD}{apkm_path.name}{Colors.RESET}")
    
    out_dir = Path(output_dir) if output_dir else apkm_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    
    output_apk_merged = out_dir / f"{apkm_path.stem}_merged.apk"
    output_apk_single = out_dir / f"{apkm_path.stem}.apk"
    
    extract_dir = out_dir / f"{apkm_path.stem}_temp"
    
    if extract_dir.exists():
        rmtree(extract_dir)
    
    extract_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        with zipfile.ZipFile(apkm_path, 'r') as zip_ref:
            apk_files = [f for f in zip_ref.namelist() if f.endswith('.apk')]
            
            if not apk_files:
                raise ValueError("No APK files in APKM")
            
            print_info(f"Found {len(apk_files)} APK(s), extracting...")
            
            extracted = []
            
            def extract_file(apk_file):
                dest = extract_dir / Path(apk_file).name
                with zip_ref.open(apk_file) as src, open(dest, 'wb') as dst:
                    dst.write(src.read())
                return str(dest)
            
            with ThreadPoolExecutor(max_workers=MERGE_THREADS) as executor:
                futures = [executor.submit(extract_file, apk) for apk in apk_files]
                for future in as_completed(futures):
                    extracted.append(future.result())
            
            print_success(f"Extracted {len(extracted)} files")
        
        # Merge if multiple APKs
        if merge_splits and len(extracted) > 1:
            print(f"\n{Colors.CYAN}[MERGE]{Colors.RESET} Merging {len(extracted)} split APKs...")
            
            if cache_mgr:
                from apkeditor import ensure_apkeditor
                apkeditor_jar = ensure_apkeditor(cache_mgr)
            else:
                raise RuntimeError("cache_mgr required for merging")
            
            merged_path = merge_with_apkeditor(apkeditor_jar, extracted, 
                                              str(output_apk_merged))
            rmtree(extract_dir)
            
            size_mb = Path(merged_path).stat().st_size / (1024 * 1024)
            print_success(f"Merged APK: {Path(merged_path).name}")
            print_info(f"Size: {size_mb:.1f} MB")
            
            return str(merged_path)
        
        # Single APK or no merge
        base_apk = None
        for apk in extracted:
            if 'base' in Path(apk).name.lower():
                base_apk = apk
                break
        
        if not base_apk:
            base_apk = extracted[0]
        
        copy2(base_apk, output_apk_single)
        rmtree(extract_dir)
        
        size_mb = Path(output_apk_single).stat().st_size / (1024 * 1024)
        print_success(f"Converted to APK: {output_apk_single.name}")
        print_info(f"Size: {size_mb:.1f} MB")
        
        if len(extracted) > 1:
            print_warning(f"⚠️  Only base APK used ({len(extracted)-1} splits ignored)")
        
        return str(output_apk_single)
    
    except zipfile.BadZipFile:
        raise ValueError(f"Invalid APKM/ZIP: {apkm_path}")
    except Exception as e:
        if extract_dir.exists():
            rmtree(extract_dir)
        raise RuntimeError(f"APKM conversion failed: {e}")