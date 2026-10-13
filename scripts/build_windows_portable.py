"""Assemble official embedded CPython and Windows wheels; execution verified in CI."""
import argparse,subprocess,sys,zipfile,urllib.request,hashlib,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser=argparse.ArgumentParser();parser.add_argument('--python-cache');args=parser.parse_args()
    cache=ROOT/'build/downloads';cache.mkdir(parents=True,exist_ok=True)
    p=cache/'python-3.12.10-embed-amd64.zip'
    if not p.exists():
        if args.python_cache:shutil.copy2(args.python_cache,p)
        else:
            with urllib.request.urlopen('https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip',timeout=120) as r:p.write_bytes(r.read())
    subprocess.run([sys.executable,'-m','pip','download','--platform','win_amd64','--python-version','312','--implementation','cp','--abi','cp312','--only-binary=:all:','--dest',str(cache),'-r',str(ROOT/'requirements.txt')],check=True)
    target=ROOT/'dist/申报参谋_Windows免安装版';target.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(p) as z:z.extractall(target/'python')
    site=target/'python/Lib/site-packages';site.mkdir(parents=True,exist_ok=True)
    for wheel in cache.glob('*.whl'):
        with zipfile.ZipFile(wheel) as z:z.extractall(site)
    (target/'python/python312._pth').write_text('python312.zip\n.\nLib/site-packages\n..\nimport site\n')
    for name in ['advisor','web','samples']:
        shutil.copytree(ROOT/name,target/name,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
    for name in ['app.py','desktop_native.py','.env.example','README.md','LICENSE']:shutil.copy2(ROOT/name,target/name)
    (target/'启动申报参谋.bat').write_text('@echo off\nchcp 65001 >nul\ncd /d "%~dp0"\npython\\pythonw.exe desktop_native.py\n',encoding='utf-8')
    (target/'诊断启动.bat').write_text('@echo off\nchcp 65001 >nul\ncd /d "%~dp0"\npython\\python.exe desktop_native.py\npause\n',encoding='utf-8')
    manifest={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in cache.iterdir() if x.suffix in ['.zip','.whl']}
    (target/'构建依赖SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
    out=ROOT/'dist/申报参谋_Windows免安装版.zip'
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        for f in target.rglob('*'):
            if f.is_file():z.write(f,f.relative_to(target.parent))
    print(out)
if __name__=='__main__':main()
