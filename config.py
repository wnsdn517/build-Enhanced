#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReVanced Build Script - Configuration
설정 및 상수 관리
"""

from pathlib import Path
import re

# ==================== API URLs ====================
CLI_RELEASE_URL = 'https://api.github.com/repos/AmpleReVanced/revanced-cli/releases/latest'
PATCHES_RELEASE_URL = 'https://api.github.com/repos/AmpleReVanced/revanced-patches/releases/latest'
APKEDITOR_RELEASE_URL = 'https://api.github.com/repos/REAndroid/APKEditor/releases/latest'

# ==================== Paths ====================
CACHE_DIR = Path.home() / '.revanced_cache'
CACHE_METADATA_FILE = CACHE_DIR / 'metadata.json'

# ==================== Threading ====================
DOWNLOAD_THREADS = 8
MERGE_THREADS = 4

# ==================== Regular Expressions ====================
VERSION_REGEX = re.compile(r'version "([^"]+)"')
INDEX_REGEX = re.compile(r'(?m)^\s*Index:\s*(\d+)\s*$')
NAME_REGEX = re.compile(r'(?m)^\s*Name:\s*(.+?)\s*$')
DESC_REGEX = re.compile(r'(?m)^\s*Description:\s*(.+?)\s*$')
ENABLED_REGEX = re.compile(r'(?m)^\s*Enabled:\s*(true|false)\s*$')

# ==================== Exclusion Lists ====================
DEFAULT_EXCLUDE_DIRS = [
    'output', '.git', '__pycache__', 'venv', '.venv',
    'node_modules', '.cache', '.revanced_cache', 'build', 'dist'
]

# ==================== Java Configuration ====================
JAVA_MIN_VERSION = 17
JAVA_MAX_VERSION = 24

# JVM 최적화 옵션 (성능 개선)
JVM_OPTS = [
    '-XX:+UseG1GC',              # G1 GC 사용 (빠른 처리)
    '-XX:+ParallelRefProcEnabled',  # 병렬 참조 처리
    '-XX:MaxGCPauseMillis=200',  # GC 정지 시간 최소화
    '-Xmx4G',                    # 최대 힙 메모리 4GB
    '-Xms512M',                  # 초기 힙 메모리 512MB
]

ZULU_INSTALL_GUIDANCE = """
╔═══════════════════════════════╗
║         Java Environment Setup Required                      ║
╚═══════════════════════════════╝

Install Java 17-24 (OpenJDK):

Ubuntu/Debian:
  sudo apt update && sudo apt install -y openjdk-17-jdk

Fedora:
  sudo dnf install -y java-17-openjdk-devel

Arch Linux:
  sudo pacman -Syu jdk-openjdk

macOS:
  brew install openjdk@17

Windows:
  Download from https://adoptium.net/ or https://www.azul.com/downloads/

After installation, ensure 'java' is in your PATH.
"""
# ==================== API URLs ====================
PARSER = "lxml"
TIMEOUT_APKM = 1
RESULTS_LIST = 1