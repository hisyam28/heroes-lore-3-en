#!/usr/bin/env python3
"""Audit the Git index before publication without reading private build inputs."""
from pathlib import Path
import ast,json,re,subprocess

ROOT=Path(__file__).resolve().parents[1]
RULES={
 'credential token':r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16})',
 'private key':r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
 'private filesystem path':r'(?i)\b[A-Z]:[\\/]Users[\\/]',
 'credential URL':r'https?://[^\s/@]+:[^\s/@]+@',
}
ROOT_FILES={'.gitignore','.gitattributes','README.md','CREDITS.md'}
DIRECTORIES={'docs','reports','tools','translations'}
FORBIDDEN={'.apk','.jar','.ipa','.dex','.so','.keystore','.jks','.pem','.pfx','.key','.idsig','.pyc'}


def main():
    raw=subprocess.check_output(['git','ls-files','--cached','-z'],cwd=ROOT)
    paths=[Path(p.decode('utf-8')) for p in raw.split(b'\0') if p]
    if not paths:raise ValueError('Stage the intended public files before auditing')
    failures=[];total=0
    modules={p.stem for p in paths if p.parts[0]=='tools' and p.suffix=='.py'}
    for rel in paths:
        name=rel.as_posix()
        if name not in ROOT_FILES and rel.parts[0] not in DIRECTORIES:failures.append((name,'unexpected public path'))
        if rel.suffix.lower() in FORBIDDEN:failures.append((name,'private/binary build file'))
        # Audit exactly what will be committed, including any staged-only changes.
        data=subprocess.check_output(['git','show',':'+name],cwd=ROOT);total+=len(data)
        if rel.suffix=='.png':continue
        text=data.decode('utf-8-sig')
        for rule,pattern in RULES.items():
            if re.search(pattern,text):failures.append((name,rule))
        if rel.suffix=='.py':
            tree=ast.parse(text,filename=name)
            for node in ast.walk(tree):
                if isinstance(node,ast.ImportFrom) and node.module and node.module.startswith('hl3_') and node.module not in modules:
                    failures.append((name,'missing local import '+node.module))
        if rel.suffix=='.md':
            for link in re.findall(r'\]\(([^)]+)\)',text):
                if '://' in link or link.startswith('#'):continue
                target=(ROOT/rel.parent/link.split('#')[0]).resolve()
                if not target.is_relative_to(ROOT) or not target.exists():failures.append((name,'broken local link'))
    inventory=json.loads(subprocess.check_output(['git','show',':reports/source-inventory.json'],cwd=ROOT))
    assert 'source_apk' not in inventory and 'source_sha256' not in inventory
    readme=subprocess.check_output(['git','show',':README.md'],cwd=ROOT).decode('utf-8')
    assert 'https://github.com/sanixmon/heroes-lore-5-en' in readme
    for private in ['work/heroes-lore-3-local.keystore','work/heroes-lore-3-signing-password.txt','.env','dist/release.apk']:
        assert subprocess.run(['git','check-ignore','-q',private],cwd=ROOT).returncode==0
    if failures:
        for name,rule in failures:print(name+': '+rule)
        raise SystemExit('Public index audit failed')
    print(f'Public index audit passed: {len(paths)} files, {total:,} bytes; local imports and documentation links valid.')


if __name__=='__main__':main()
