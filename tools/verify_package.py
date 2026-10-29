"""Integrity only, not an authenticity or investment-validity certificate."""
from pathlib import Path
import json,hashlib,sys
root=Path(__file__).resolve().parents[1];m=json.loads((root/'SHA256.json').read_text(encoding='utf8'));bad=[]
for name,digest in m['files'].items():
    p=(root/name).resolve()
    if not p.is_relative_to(root)or not p.is_file()or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:bad.append(name)
print(json.dumps({'checked':len(m['files']),'mismatches':bad,'scope':'file integrity only'}));sys.exit(1 if bad else 0)
