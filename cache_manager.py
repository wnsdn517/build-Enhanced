#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReVanced Build Script - Cache Manager
캐시 관리 및 다운로드
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime
from functools import lru_cache

from config import CACHE_DIR
from utils import print_info, print_success, download_file_smart

# ==================== 캐시 관리 ====================
class CacheManager:
    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache_dir = cache_dir
        self.metadata_file = cache_dir / 'metadata.json'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.metadata = self._load_metadata()
    
    def _load_metadata(self) -> Dict:
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def _save_metadata(self):
        try:
            with open(self.metadata_file, 'w') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception:
            pass
    
    def is_cached(self, key: str, tag: str) -> bool:
        if key not in self.metadata:
            return False
        
        entry = self.metadata[key]
        cached_tag = entry.get('tag')
        cached_path = self.cache_dir / entry.get('filename', '')
        
        if not cached_path.exists():
            return False
        
        if cached_tag != tag:
            print_info(f"New version: {cached_tag} → {tag}")
            return False
        
        return True
    
    def get_cached_path(self, key: str) -> Optional[Path]:
        if key in self.metadata:
            filename = self.metadata[key].get('filename')
            if filename:
                path = self.cache_dir / filename
                if path.exists():
                    return path
        return None
    
    def add_to_cache(self, key: str, tag: str, filename: str, url: str):
        self.metadata[key] = {
            'tag': tag,
            'filename': filename,
            'url': url,
            'cached_at': datetime.now().isoformat()
        }
        self._save_metadata()
    
    def clear_cache(self):
        import shutil
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.metadata = {}
            print_success("Cache cleared")

# ==================== GitHub Release ====================
@lru_cache(maxsize=2)
def get_latest_release(url: str, offline_mode: bool = False) -> Tuple[str, List[Dict]]:
    if offline_mode:
        return "offline", []
    
    import requests
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        tag = data.get('tag_name', '')
        assets = data.get('assets', [])
        
        if not tag:
            raise Exception("No tag_name in release")
        
        return tag, assets
    except Exception as e:
        raise Exception(f"Failed to fetch release: {e}")

def find_asset(assets: List[Dict], ext: str, 
               keyword: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    matching = [a for a in assets if str(a.get('name', '')).lower().endswith(ext)]
    
    if keyword:
        preferred = [a for a in matching 
                    if keyword.lower() in str(a.get('name', '')).lower()]
        chosen = preferred[0] if preferred else (matching[0] if matching else None)
    else:
        chosen = matching[0] if matching else None
    
    if not chosen:
        return None, None
    
    url = chosen.get('browser_download_url') or chosen.get('url') or ''
    name = chosen.get('name') or os.path.basename(url) or f'download{ext}'
    
    return (url, name) if url else (None, None)

# ==================== 다운로드 ====================
def download_or_use_cached(cache_key: str, url: str, filename: str, tag: str,
                          cache_mgr: CacheManager, output_dir: Optional[str] = None,
                          use_mt: bool = True, offline_mode: bool = False) -> str:
    if cache_mgr.is_cached(cache_key, tag):
        cached = cache_mgr.get_cached_path(cache_key)
        if cached:
            print_success(f"Using cached {cache_key}: {cached.name}")
            print_info(f"Version: {tag}")
            
            if output_dir:
                import shutil
                dest = os.path.join(output_dir, filename)
                if str(cached) != dest:
                    shutil.copy2(cached, dest)
                return dest
            return str(cached)
    
    if offline_mode:
        cached = cache_mgr.get_cached_path(cache_key)
        if cached:
            print_info(f"Offline: using cached {cache_key}")
            if output_dir:
                import shutil
                dest = os.path.join(output_dir, filename)
                if str(cached) != dest:
                    shutil.copy2(cached, dest)
                return dest
            return str(cached)
        else:
            raise RuntimeError(f"Offline: {cache_key} not in cache")
    
    print_info(f"Downloading {cache_key}...")
    dest = cache_mgr.cache_dir / filename
    
    try:
        download_file_smart(url, str(dest), use_mt)
        cache_mgr.add_to_cache(cache_key, tag, filename, url)
    except Exception as e:
        print_warning(f"Download failed: {e}")
        cached = cache_mgr.get_cached_path(cache_key)
        if cached:
            print_info("Using outdated cached version")
            dest = cached
        else:
            raise
    
    if output_dir:
        import shutil
        output_path = os.path.join(output_dir, filename)
        if str(dest) != output_path:
            shutil.copy2(dest, output_path)
        return output_path
    
    return str(dest)