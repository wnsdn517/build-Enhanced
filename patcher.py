#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReVanced Build Script - Patcher
패치 로드, 선택, 빌드 (성능 최적화 포함)
"""

import re
import subprocess
from typing import List, Dict, Tuple, Optional

from config import INDEX_REGEX, NAME_REGEX, DESC_REGEX, ENABLED_REGEX, JVM_OPTS
from utils import print_info, print_success, print_warning, Colors

# ==================== 패치 파싱 ====================
def run_cli_list_patches(cli_jar: str, rvp_path: str, 
                        target_pkg: Optional[str] = None) -> str:
    """
    CLI list-patches 실행 (성능 최적화 적용)
    """
    cmd = ['java'] + JVM_OPTS + [
        '-jar', cli_jar, 
        'list-patches', rvp_path, 
        '-p=true', '-v=true', '-o=true'
    ]
    
    print_info(f"Loading patches..." + 
              (f" (filtering: {target_pkg})" if target_pkg else ""))
    
    proc = subprocess.run(cmd, capture_output=True, text=True, 
                         encoding='utf-8', errors='replace')
    
    if proc.returncode != 0:
        raise Exception(f"list-patches failed: {proc.stderr}")
    
    return proc.stdout

def parse_patches(text: str, target_pkg: Optional[str] = None,
                 include_universal: bool = False) -> List[Dict]:
    matches = list(re.finditer(r'(?m)^\s*Index:\s*\d+\s*$', text))
    
    if not matches:
        return []
    
    blocks = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        blocks.append(text[start:end])
    
    entries = [_parse_patch_block(block) for block in blocks if block.strip()]
    
    if target_pkg:
        entries = _filter_patches(entries, target_pkg, include_universal)
    
    return entries

def _parse_patch_block(block: str) -> Dict:
    entry = {
        'index': None, 'name': None, 'description': None, 'enabled': None,
        'packages': [], 'compatible_versions': {},
        'options_struct': [], 'is_universal': False, 'raw': block.strip()
    }
    
    if m := INDEX_REGEX.search(block):
        entry['index'] = int(m.group(1))
    if m := NAME_REGEX.search(block):
        entry['name'] = m.group(1).strip()
    
    desc_match = re.search(
        r'(?ms)^\s*Description:\s*(.+?)(?=^\s*(Enabled:|Options:|Index:|Name:|Packages:|Compatible packages:)|\Z)',
        block
    )
    if desc_match:
        entry['description'] = desc_match.group(1).strip()
    elif m := DESC_REGEX.search(block):
        entry['description'] = m.group(1).strip()
    
    if m := ENABLED_REGEX.search(block):
        entry['enabled'] = m.group(1).lower() == 'true'
    
    pkg_pattern = re.compile(r'([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+)', re.IGNORECASE)
    raw_pkgs = pkg_pattern.findall(block)
    
    seen = []
    for p in raw_pkgs:
        p = p.strip()
        if re.match(r'^[a-zA-Z]', p) and p not in seen:
            seen.append(p)
    
    entry['packages'] = seen
    for p in entry['packages']:
        entry['compatible_versions'][p] = []
    
    entry['is_universal'] = len(entry['packages']) == 0
    return entry

def _filter_patches(entries: List[Dict], target: str, include_univ: bool) -> List[Dict]:
    target = target.strip().lower()
    return [
        e for e in entries
        if target in [p.lower() for p in e.get('packages', [])]
        or (include_univ and e.get('is_universal'))
    ]

# ==================== 패치 선택 ====================
def interactive_select_patches(entries: List[Dict], pkg: Optional[str] = None,
                              auto_selected: bool = False) -> Optional[List[Tuple]]:
    try:
        from questionary import confirm, checkbox
    except ImportError:
        print_warning("questionary not installed")
        return None
    
    if auto_selected:
        default_enabled = [e for e in entries if e.get('enabled')]
        
        if default_enabled:
            print(f"\n{Colors.CYAN}[INFO]{Colors.RESET} {len(default_enabled)} patches enabled by default")
            for e in default_enabled[:5]:
                print(f"  • {e.get('name', 'Unknown')}")
            if len(default_enabled) > 5:
                print(f"  ... and {len(default_enabled) - 5} more")
        
        result = confirm("Customize patch selection?", default=False).ask()
        
        if result is None:
            print_info("Selection cancelled")
            return None
        
        if not result:
            return [
                (('idx', e['index']) if e['index'] is not None else ('name', e['name']))
                for e in default_enabled
            ]
    
    choices = []
    for e in entries:
        idx = f"[{e['index']}]" if e['index'] is not None else "[—]"
        name = e['name'] or '(Unnamed)'
        
        tags = []
        if e.get('enabled'):
            tags.append("enabled")
        if e.get('is_universal'):
            tags.append("universal")
        if e.get('packages'):
            tags.append(f"{len(e['packages'])} pkg(s)")
        
        tag_text = f" — {' | '.join(tags)}" if tags else ""
        label = f"{idx} {name}{tag_text}"
        value = ('idx', e['index']) if e['index'] is not None else ('name', name)
        
        choices.append({
            "name": label,
            "value": value,
            "checked": bool(e.get('enabled', False))
        })
    
    result = checkbox(
        "Select patches (Space=toggle, Enter=confirm):",
        choices=choices,
        validate=lambda ans: True if len(ans) >= 1 else "Select at least one patch",
    ).ask()
    
    if result is None:
        print_info("Selection cancelled")
        return None
    
    return result

def prompt_options(selected: List[Tuple], entries: List[Dict]) -> Optional[List[Dict]]:
    try:
        from questionary import confirm
    except ImportError:
        return [{'by': k, 'value': v, 'options': {}} for k, v in selected]
    
    by_idx = {e['index']: e for e in entries if e['index'] is not None}
    by_name = {e['name']: e for e in entries if e.get('name')}
    
    result = []
    
    for kind, val in selected:
        entry = by_idx.get(val) if kind == 'idx' else by_name.get(val)
        
        if entry and entry.get('options_struct'):
            name = entry.get('name') or str(val)
            confirm_result = confirm(f"Configure '{name}'?", default=False).ask()
            
            if confirm_result is None:
                print_info("Cancelled")
                return None
            
            if confirm_result:
                print_info("Using defaults (advanced config not implemented)")
        
        result.append({'by': kind, 'value': val, 'options': {}})
    
    return result

# ==================== 빌드 명령 생성 ====================
def build_patch_command(cli: str, rvp: str, apk: str, output: str,
                       exclusive: bool, selected: List[Dict],
                       keystore: Optional[str] = None,
                       keystore_pw: Optional[str] = None,
                       key_alias: Optional[str] = None,
                       key_pw: Optional[str] = None) -> List[str]:
    """
    성능 최적화된 패치 명령 생성
    """
    # JVM 옵션 포함
    cmd = ['java'] + JVM_OPTS + ['-jar', cli, 'patch', '-p', rvp]
    
    if exclusive:
        cmd.append('--exclusive')
    
    for sel in selected:
        kind, val = sel['by'], sel['value']
        
        if kind == 'idx':
            cmd.extend(['--ei', str(val)])
        else:
            cmd.extend(['-e', str(val)])
        
        for k, v in (sel.get('options') or {}).items():
            cmd.append(f"-O{k}={v}" if v else f"-O{k}")
    
    if keystore:
        cmd.extend(['--keystore', keystore])
    if keystore_pw:
        cmd.extend(['--keystore-password', keystore_pw])
    if key_alias:
        cmd.extend(['--keystore-entry-alias', key_alias])
    if key_pw:
        cmd.extend(['--keystore-entry-password', key_pw])
    
    cmd.extend(['-o', output, apk])
    return cmd