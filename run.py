#!/usr/bin/env python3
"""ReVanced Patcher - Optimized & Stable"""
import os,sys,json,re,subprocess,signal,shutil
from pathlib import Path
from shutil import which
from concurrent.futures import ThreadPoolExecutor,TimeoutError

QUERY=""
REPOS={"cli":"AmpleReVanced/revanced-cli","patches":"AmpleReVanced/revanced-patches","APKEditor":"REAndroid/APKEditor"}
CACHE,EXTS=Path(".cache"),(".apk",".apkm")

signal.signal(signal.SIGINT,lambda s,f:sys.exit(130))
signal.signal(signal.SIGTERM,lambda s,f:sys.exit(130))

class C:
 R,G,Y,B,X='\033[91m','\033[92m','\033[93m','\033[2m','\033[0m'
 if os.name=='nt'or not sys.stdout.isatty():R=G=Y=B=X=''

p=lambda m,c='',h='':print(f"{c}[{h}]{C.X if h else''} {m}{C.X}")
ok=lambda m,h='✓':p(m,C.G,h)
err=lambda m,h='✗':(p(m,C.R,h),sys.exit(1))
warn=lambda m,h='⚠':p(m,C.Y,h)
info=lambda m,h='ℹ':p(m,C.B,h)

def chk():
 if Path.cwd()!=Path(__file__).parent:err("Run in script directory")
 if sys.version_info<(3,7):err("Python >= 3.7 required")
 if not which('java'):err("Java not installed")
 ok("Environment OK")
 try:
  import requests,cloudscraper,bs4,tqdm,questionary
  from apkmirror import APKMirror
  ok("All modules loaded")
  return requests,tqdm,APKMirror,questionary
 except ImportError as e:err(f"Missing: {e.name}\nRun: pip install requests cloudscraper beautifulsoup4 tqdm questionary apkmirror-api")

requests,tqdm,APKMirror,questionary=chk()
jars={}

def dl_assets():
 info("Downloading assets");CACHE.mkdir(parents=True,exist_ok=True)
 mf=CACHE/"versions.json";meta=json.loads(mf.read_text())if mf.exists()else{}
 s=requests.Session()
 
 def fetch(k,repo):
  try:
   j=s.get(f"https://api.github.com/repos/{repo}/releases/latest",timeout=10).json()
   if "message"in j and"rate limit"in j.get("message",""):
    return k,"skip"if list(CACHE.glob(f"*{k}*"))else"rate",None
   return k,"ok",j
  except Exception as e:return k,"err",str(e)
 
 with ThreadPoolExecutor(max_workers=3)as ex:
  results=list(ex.map(lambda x:fetch(x[0],x[1]),REPOS.items()))
 
 for k,st,data in results:
  if st=="err":err(f"Failed: {k} ({data})")
  if st=="rate":err("GitHub rate limit. Wait or use token")
  if st=="skip":f = next(CACHE.glob(f"*{k}*"));jars[k] = f;warn(f"{k} cached");continue
  
  tag,asset=data["tag_name"],data["assets"][0]
  jars[k]=CACHE/asset["name"]
  if meta.get(k)==tag:ok(f"{k} {tag}");continue
  
  info(f"Downloading {k} {tag}")
  try:
   r=s.get(asset["browser_download_url"],stream=True,timeout=30)
   r.raise_for_status()
   with open(jars[k],'wb')as f:
    bar=tqdm.tqdm(total=int(r.headers.get("content-length",0)),unit="B",unit_scale=True,desc=k)
    for ch in r.iter_content(1024*256):f.write(ch);bar.update(len(ch))
    bar.close()
   meta[k]=tag
  except Exception as e:err(f"Download failed: {k} ({e})")
 
 mf.write_text(json.dumps(meta,indent=2))

def find_apk():
 info("Finding APK");files=[]
 for root,dirs,fnames in os.walk("."):
  dirs[:]=[d for d in dirs if d not in("output",".cache",".git","__pycache__")]
  files.extend([Path(root)/f for f in fnames if f.lower().endswith(EXTS)])
 
 if not files:warn("No APK found");return dl_apkm()
 
 print("0: Download from APKMirror")
 for i,f in enumerate(files,1):print(f"{i}: {f.stem[:40]}..{f.suffix}")
 
 try:
  c=input(f"Select (0-{len(files)}): ").strip()
  if not c.isdigit()or not 0<=int(c)<=len(files):raise ValueError
  c=int(c)
 except:err("Invalid selection")
 return dl_apkm()if c==0 else files[c-1]

def dl_apkm():
 if not QUERY:err("Set QUERY in script")
 info(f"Searching: {QUERY}")
 try:
  res=APKMirror().search(QUERY)
  if not res:err(f"No results: {QUERY}")
  ok(f"Found: {res[0]['name']}")
  return Path(APKMirror().get_app_details(res[0]["link"]))
 except Exception as e:err(f"APKMirror error: {e}")

def apkm2apk(apkm):
 apkm,tmp,out=Path(apkm),CACHE/"apkm_tmp",Path(apkm).parent/f"{Path(apkm).stem}.apk"
 out.exists()and out.unlink()
 tmp.exists()and shutil.rmtree(tmp)
 tmp.mkdir(parents=True,exist_ok=True)
 
 try:
  info("Converting APKM → APK in background")
  if subprocess.run(["unzip","-q","-o",str(apkm),"-d",str(tmp)],stderr=subprocess.PIPE).returncode!=0:
   raise Exception("Unzip failed")
  r=subprocess.run(["java","-jar",str(jars["APKEditor"]),"m","-i",str(tmp),"-o",str(out)],
                   capture_output=True,text=True,timeout=300)
  if r.returncode!=0:raise Exception(f"Merge failed: {r.stderr[:150]}")
  return out if out.exists()else None
 except subprocess.TimeoutExpired:err("APKM conversion timeout")
 except Exception as e:err(f"APKM conversion failed: {e}")
 finally:shutil.rmtree(tmp,ignore_errors=True)

def get_pkg(apk):
 try:
  out=subprocess.run(['aapt','dump','badging',str(apk)],capture_output=True,text=True,timeout=10).stdout
  return m.group(1)if(m:=re.search(r"package: name='([^']+)'",out))else None
 except:return None

def get_pkg_apkm(apkm):
 tmp=CACHE/"apkm_pkg"
 tmp.exists()and shutil.rmtree(tmp)
 tmp.mkdir()
 try:
  subprocess.run(["unzip","-q","-o",str(apkm),"-d",str(tmp)],check=True,timeout=30)
  base=next(tmp.glob("base*.apk"),None)
  return get_pkg(base)if base else None
 except:return None
 finally:shutil.rmtree(tmp,ignore_errors=True)

def list_patches(cli,rvp,pkg):
 info(f"Loading patches: {pkg}")
 try:
  proc=subprocess.Popen(['java','-jar',cli,'list-patches',rvp,'-p=true','-v=true','-o=true'],
                        stdout=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
  entries,block=[],[]
  for line in proc.stdout:
   if line.strip().startswith("Index:"):
    if block and(e:=parse_block(''.join(block),pkg)):entries.append(e)
    block=[]
   block.append(line)
  if block and(e:=parse_block(''.join(block),pkg)):entries.append(e)
  proc.wait()
  return entries
 except Exception as e:err(f"Failed to load patches: {e}")

def parse_block(block,pkg):
 pkgs=[p.lower()for p in re.findall(r'[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+',block,re.I)]
 is_universal=len(pkgs)==0
 if pkgs and pkg.lower()not in pkgs:return None
 entry={'index':int(m.group(1))if(m:=re.search(r'Index:\s*(\d+)',block))else None,
        'name':(m.group(1).strip()if(m:=re.search(r'Name:\s*(.+?)$',block,re.M))else"Unknown"),
        'enabled':m.group(1).lower()=='true'if(m:=re.search(r'Enabled:\s*(true|false)',block,re.I|re.M))else False,
        'packages':pkgs,'universal':is_universal,'options':[]}
 for opt in re.finditer(r'Key:\s*(\S+)\s*\n\tType:\s*(\S+)(?:\s*\n\tDefault:\s*(\S+))?',block):
  entry['options'].append({'key':opt.group(1),'default':opt.group(3)or''})
 return entry
def select_patches(entries):
 default=[e for e in entries if e.get('enabled')]
 if default:
  ok(f"{len(default)} patches enabled by default")
  for e in default[:5]:print(f"  • {e['name']}")
  if len(default)>5:print(f"  ... +{len(default)-5} more")
 try:
  if not questionary.confirm("Customize patches?",default=False).ask():
   return[(('idx',e['index'])if e['index']is not None else('name',e['name']),
           e['index']if e['index']is not None else e['name'],{})for e in default]
  
  choices=[{"name":f"[{e['index']or'—'}] {e['name'][:60]}"+(" ✦"if e.get('enabled')else"")+(" ✧"if e.get('universal')else""),
            "value":(e['index'],e['name']),
            "checked":e.get('enabled',False)}for e in entries]

  selected=questionary.checkbox("",choices=choices, instruction="↑↓ move | SPACE select | ENTER confirm | A toggle | I invert \n ✧ universal | ✦ recommend").ask()
 except KeyboardInterrupt:sys.exit(130)
 if not selected:return None
 result=[]
 for idx,name in selected:
  entry=next((e for e in entries if e['index']==idx or e['name']==name),None)
  opts={}
  if entry and entry.get('options'):
   print(f"\n{entry['name']} options:")
   try:
    for opt in entry['options']:
     val=questionary.text(f"  {opt['key']}:",default=opt['default']).ask()
     if val and val!=opt['default']:opts[opt['key']]=val
   except KeyboardInterrupt:sys.exit(130)
  kind='idx'if idx is not None else'name'
  val=idx if idx is not None else name
  result.append((kind,val,opts))
 return result

def build_cmd(cli,rvp,apk,out,selected):
 cmd=['java','-jar',cli,'patch','-p',rvp]
 for kind,val,opts in selected:
  cmd+=['--ei'if kind=='idx'else'-e',str(val)]
  cmd+=[f"-O{k}={v}"for k,v in opts.items()]
 return cmd+['-o',out,apk]

def patch(cmd):
 info("Patching... (this takes time)")
 try:
  subprocess.run(cmd,check=True,encoding='utf-8',errors='replace')
  ok("Patch completed!")
 except subprocess.CalledProcessError as e:err(f"Patch failed: {e}")
 except KeyboardInterrupt:sys.exit(130)

try:
 warn("Use at your own risk","WARNING");print()
 
 dl_assets()
 apk_file=find_apk()
 if not apk_file:sys.exit(0)
 apk_path=Path(apk_file)
 is_apkm=apk_path.suffix.lower()==".apkm"
 ex,fut=None,None
 if is_apkm:
  ex=ThreadPoolExecutor(max_workers=1)
  fut=ex.submit(apkm2apk,apk_path)
 pkg=get_pkg_apkm(apk_path)if is_apkm else get_pkg(apk_path)
 if not pkg:err("Failed to detect package")
 patches_list=list_patches(str(jars["cli"]),str(jars["patches"]),pkg)
 if not patches_list:warn("No patches found");sys.exit(0)
 selected=select_patches(patches_list)
 if not selected:warn("No patches selected");sys.exit(0)
 if fut:
  info("Waiting for APKM conversion")
  try:apk_path=fut.result(timeout=600)
  except TimeoutError:err("APKM conversion timeout")
  except Exception as e:err(f"APKM conversion error: {e}")
 if ex:ex.shutdown(wait=False)
 if not apk_path or not apk_path.exists():err("APK not found after conversion")
 
 out=Path("output")/f"{apk_path.stem}_patched{apk_path.suffix}"
 out.parent.mkdir(parents=True,exist_ok=True)
 patch(build_cmd(str(jars["cli"]),str(jars["patches"]),str(apk_path),str(out),selected))

except KeyboardInterrupt:print("\nInterrupted");sys.exit(130)
except Exception as e:err(f"Unexpected error: {e}")