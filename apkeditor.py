#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReVanced Build Script - APKEditor
APKEditor 다운로드 및 관리
"""

from config import APKEDITOR_RELEASE_URL
from utils import print_info, download_file_smart

def ensure_apkeditor(cache_mgr) -> str:
    """APKEditor JAR 다운로드 또는 캐시 사용"""
    apkeditor_jar = cache_mgr.cache_dir / 'APKEditor.jar'
    
    if apkeditor_jar.exists():
        print_info(f"Using cached APKEditor: {apkeditor_jar.name}")
        return str(apkeditor_jar)
    
    print_info("Downloading APKEditor...")
    
    try:
        import requests
        
        resp = requests.get(APKEDITOR_RELEASE_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        
        tag = data.get('tag_name', '')
        assets = data.get('assets', [])
        
        jar_asset = None
        for asset in assets:
            name = asset.get('name', '').lower()
            if name.endswith('.jar') and 'apkeditor' in name:
                jar_asset = asset
                break
        
        if not jar_asset:
            raise Exception("APKEditor.jar not found in release")
        
        url = jar_asset.get('browser_download_url')
        if not url:
            raise Exception("No download URL for APKEditor.jar")
        
        print_info(f"Version: {tag}")
        download_file_smart(url, str(apkeditor_jar), use_mt=False)
        
        cache_mgr.add_to_cache('apkeditor', tag, 'APKEditor.jar', url)
        
        return str(apkeditor_jar)
    
    except Exception as e:
        raise RuntimeError(f"Failed to get APKEditor: {e}")