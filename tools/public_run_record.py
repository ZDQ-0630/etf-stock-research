"""Generate a minimal public audit record, without account details or raw vendor data."""
from datetime import datetime,timezone
from pathlib import Path
import hashlib,json,os,sys
if len(sys.argv)!=3:raise SystemExit('usage: python tools/public_run_record.py partial-run/snapshot.json output.json')
src,dst=map(Path,sys.argv[1:]);run=os.environ.get('GITHUB_RUN_ID','');attempt=os.environ.get('GITHUB_RUN_ATTEMPT','');commit=os.environ.get('GITHUB_SHA','')
if not(run.isdigit() and attempt.isdigit() and len(commit)==40 and all(c in '0123456789abcdef' for c in commit)):raise SystemExit('missing trusted run context')
d=json.loads(src.read_text(encoding='utf8'))
r={'schema':'etf.cloud_validation.public_audit.v1','run_id':run,'run_attempt':attempt,'source_commit':commit,'recorded_at':datetime.now(timezone.utc).isoformat(),'snapshot_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'scope':'partial research snapshot, not a complete model review','snapshot_status':d['status'],'latest_scheduled_session':d['latest_scheduled_session'],'prices_checked':len(d['prices']),'price_pair_agreements':sum(x['agreement'] is True for x in d['prices']),'forecast_snapshots':sum(x['status']=='retrieved_unverified' for x in d['forecasts'].values()),'macro_status':{k:v['status'] for k,v in d['macro'].items()},'failed_sources':[{'name':x['key'],'error':x.get('error')} for x in d['sources'] if not x['ok']],'blocked':d['blocked'],'entry_conclusion':'unavailable'}
dst.parent.mkdir(parents=True,exist_ok=True)
with dst.open('x',encoding='utf8') as f:json.dump(r,f,ensure_ascii=False,indent=2,allow_nan=False)
print(json.dumps({'record':dst.as_posix(),'failed_sources':r['failed_sources'],'snapshot_status':r['snapshot_status']}))
