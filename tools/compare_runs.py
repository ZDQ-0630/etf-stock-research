"""Compare recent versioned partial runs; missing or changed methodology blocks claims."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,sys
if len(sys.argv)!=4:raise SystemExit('usage: python tools/compare_runs.py current-dir previous-dir output.json')
current,previous,dest=map(Path,sys.argv[1:]);out={'schema':'etf.cloud.run_comparison.v1','created_at':datetime.now(timezone.utc).isoformat(),'status':'blocked','reason':None,'stocks':[],'fundamental':[],'risk':[]}
def load(dir,name):return json.loads((dir/name).read_text(encoding='utf8'))
try:
 c=load(current,'research-only.json');p=load(previous,'research-only.json');cs=load(current,'snapshot.json');ps=load(previous,'snapshot.json')
 if c.get('schema')!='etf.cloud.daily_research.v1' or p.get('schema')!=c.get('schema'):raise ValueError('research schemas differ')
 if c.get('stock_core_sha256')!=p.get('stock_core_sha256') or c.get('script_sha256')!=p.get('script_sha256'):raise ValueError('calculation code changed; replay a common input before comparison')
 if c.get('baseline_sha256')!=p.get('baseline_sha256'):raise ValueError('baseline changed; replay common assumptions')
 if c.get('computed_at','')<=p.get('computed_at',''):raise ValueError('previous result is not older than current')
 old={r['symbol']:r for r in p['rows']}
 for n in c['rows']:
  b=old.get(n['symbol']);row={'symbol':n['symbol'],'status':'blocked'}
  if b and b['status']==n['status']=='computed_for_research_only':
   one=lambda v:next((x for x in v['scenarios'] if x.get('id')=='reference' and x.get('hurdle')==.1 and x.get('current')),None)
   x,y=one(b),one(n)
   if x and y and all(x.get(k)==y.get(k) for k in ['terminal_eps','terminal_pe','years','hurdle']):
    row.update(status='comparable_price_only',previous_date=b['date'],current_date=n['date'],previous_price=b['price'],current_price=n['price'],previous_annualized=x['current']['annualized'],current_annualized=y['current']['annualized'],previous_conditional_cap=x['current']['max_entry'],current_conditional_cap=y['current']['max_entry'])
  out['stocks'].append(row)
 if c.get('history_core_sha256')==p.get('history_core_sha256') and c.get('risk_script_sha256')==p.get('risk_script_sha256') and c.get('frozen_history_sha256')==p.get('frozen_history_sha256'):
  prior={x['symbol']:x for x in p.get('risk',[])}
  for n in c.get('risk',[]):
   b=prior.get(n['symbol'])
   if b and b['status']==n['status']=='computed_for_research_only':out['risk'].append({'symbol':n['symbol'],'previous_date':b['current']['date'],'current_date':n['current']['date'],'previous_dd':b['current']['dd'],'current_dd':n['current']['dd']})
 for symbol,n in cs.get('forecasts',{}).items():
  before={x.get('fiscal_end'):x for x in ps.get('forecasts',{}).get(symbol,{}).get('rows',[])}
  for row in n.get('rows',[]):
   oldrow=before.get(row.get('fiscal_end'));a=oldrow.get('vendor_eps') if oldrow else None;b=row.get('vendor_eps')
   if isinstance(a,(int,float)) and isinstance(b,(int,float)) and a!=b:out['fundamental'].append({'symbol':symbol,'fiscal_end':row['fiscal_end'],'previous_eps':a,'current_eps':b,'vendor_asof':row.get('vendor_asof'),'status':'numeric_change_requires_accounting_basis_and_formation_time_verification'})
 out.update(status='partial_comparison_only',reason='Same calculation and scenarios; close-time, provider independence, company financial review and investment validity remain unverified',current_snapshot_sha256=hashlib.sha256((current/'snapshot.json').read_bytes()).hexdigest(),previous_snapshot_sha256=hashlib.sha256((previous/'snapshot.json').read_bytes()).hexdigest(),current_research_sha256=hashlib.sha256((current/'research-only.json').read_bytes()).hexdigest(),previous_research_sha256=hashlib.sha256((previous/'research-only.json').read_bytes()).hexdigest())
except (OSError,ValueError,KeyError,TypeError) as e:out['reason']=type(e).__name__+': '+str(e)
with dest.open('x',encoding='utf8') as f:json.dump(out,f,ensure_ascii=False,indent=2,allow_nan=False)
print(json.dumps({'status':out['status'],'reason':out['reason'],'comparable_stocks':sum(x['status']=='comparable_price_only' for x in out['stocks']),'risk_rows':len(out['risk']),'unverified_forecast_changes':len(out['fundamental'])}))
