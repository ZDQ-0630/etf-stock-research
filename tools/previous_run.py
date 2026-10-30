"""Select last published validation run, never a fixed historical ID."""
import json,os
from pathlib import Path
p=Path('validation-state/cloud-runs/latest.json');value=''
if p.exists():
 try:
  d=json.loads(p.read_text(encoding='utf8'));candidate=d.get('run_id','')
  if d.get('schema')=='etf.cloud_validation.public_audit.v1' and isinstance(candidate,str) and candidate.isdigit():value=candidate
 except (OSError,ValueError,TypeError):pass
with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf8') as f:f.write('run_id='+value+'\n')
print('Previous run available' if value else 'No usable previous run; comparison will be blocked')
