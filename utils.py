#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReVanced Build Script - Utilities
색상 출력, 네트워크, 의존성 관리 등
"""

import os
import sys
import subprocess
from typing import List, Optional

# ==================== 색상 ====================
class Colors:
    """ANSI color codes"""
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'

    @staticmethod
    def disable():
        for attr in dir(Colors):
            if not attr.startswith('_') and attr.isupper() and attr != 'disable':
                setattr(Colors, attr, '')

if os.name == 'nt' or not sys.stdout.isatty():
    Colors.disable()

# ==================== 출력 함수 ====================
def print_box(title: str, content: List[str] = None, color: str = Colors.CYAN):
    width = 60
    print(f"\n{color}{'═' * width}{Colors.RESET}")
    print(f"{color}{title:^{width}}{Colors.RESET}")
    print(f"{color}{'═' * width}{Colors.RESET}")
    if content:
        for line in content:
            print(f"{color}║{Colors.RESET} {line}")
        print(f"{color}{'═' * width}{Colors.RESET}")

def print_step(step: int, total: int, title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}[STEP {step}/{total}]{Colors.RESET} {Colors.BOLD}{title}{Colors.RESET}")
    print(f"{Colors.DIM}{'─' * 60}{Colors.RESET}")

def print_success(message: str):
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")

def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")

def print_error(message: str):
    print(f"{Colors.RED}✗{Colors.RESET} {message}")

def print_info(message: str):
    print(f"{Colors.CYAN}ℹ{Colors.RESET} {message}")

# ==================== 의존성 설치 ====================
def auto_install_dependencies():
    required = {
        'requests': 'requests',
        'questionary': 'questionary',
        'bs4': 'beautifulsoup4',
        'tqdm': 'tqdm',
    }
    
    missing = []
    for module, package in required.items():
        try:
            __import__(module)
        except ImportError:
            missing.append(package)
    
    if missing:
        print_info(f"Installing: {', '.join(missing)}")
        try:
            subprocess.check_call(
                [sys.executable, '-m', 'pip', 'install', '--quiet', *missing],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print_success("Dependencies installed")
        except subprocess.CalledProcessError:
            print_warning("Some dependencies failed to install")

# ==================== 네트워크 ====================
def check_network_connection(timeout: int = 5) -> bool:
    try:
        import requests
        requests.get("https://api.github.com", timeout=timeout)
        return True
    except:
        return False

def create_session_with_headers():
    import requests
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
    })
    return session

def download_file_smart(url: str, dest: str, use_mt: bool = True):
    """진행바 포함 다운로드"""
    try:
        import requests
        from tqdm import tqdm
    except ImportError:
        import requests
        print_info(f"Downloading {os.path.basename(dest)}...")
        response = requests.get(url, stream=True, timeout=60)
        response.raise_for_status()
        with open(dest, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
        print_success(f"Downloaded: {os.path.basename(dest)}")
        return
    
    response = requests.get(url, stream=True, timeout=60)
    response.raise_for_status()
    total = int(response.headers.get('content-length', 0))
    
    with open(dest, 'wb') as f, tqdm(
        desc=os.path.basename(dest),
        total=total,
        unit='iB',
        unit_scale=True,
        unit_divisor=1024,
    ) as pbar:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                size = f.write(chunk)
                pbar.update(size)