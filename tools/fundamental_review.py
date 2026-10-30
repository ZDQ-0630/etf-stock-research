"""Flag changes; unknown forecast asOf and accounting basis prevent automatic adoption."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
if len(sys.argv)!=3:raise SystemExit('usage: python tools/fundamental_review.py snapshot.json new-output.json')
src,dst=map(Path,sys.argv[1:]);snapshot=json.loads(src.read_text(encoding='utf8'))
if snapshot.get('schema')!='etf.cloud.partial_snapshot.v1':raise ValueError('Unexpected snapshot schema')
companies=[]
for symbol,block in snapshot['forecasts'].items():
 changes=[]
 for r in block.get('rows',[]):
  previous,current=r.get('previous_vendor_eps'),r.get('vendor_eps')
  if isinstance(previous,(int,float)) and isinstance(current,(int,float)) and previous!=current:
   changes.append({'fiscal_end':r.get('fiscal_end'),'previous':previous,'current':current,'absolute_change':current-previous,'relative_change':current/previous-1 if previous else None,'analysts':r.get('analyst_count'),'vendor_asof':r.get('vendor_asof'),'basis':r.get('comparability'),'status':'requires_verification_before_scenario_change'})
 companies.append({'symbol':symbol,'vendor_snapshot_status':block.get('status'),'fiscal_changes':changes,'status':'changed_requires_review' if changes else 'formation_date_and_basis_unverified',
  'official_actuals_review':'not_automatically_obtained_or_compared','scenario_status':'unchanged','limitation':'Compared to frozen Oct 29 public snapshot, not necessarily the immediately preceding run; no claim on current EPS basis or timing.'})
macro=[]
for k,v in snapshot['macro'].items():
 obs=v.get('observations',[])
 if len(obs)>=2 and obs[-1]['date']>obs[-2]['date']:
  item={'series':k,'before':obs[-2],'after':obs[-1],'difference_pct_points':obs[-1]['value_pct']-obs[-2]['value_pct'],'source':v.get('source'),'status':'retrieved_requires_review','application':'discount-rate sensitivity only; no automatic earnings or PE change'}
  if k=='treasury_nominal':
   a,b=obs[-2]['value_pct']/100,obs[-1]['value_pct']/100;erp,g,payout=.05,.03,.5
   if a+erp-g>0 and b+erp-g>0:item['illustrative_steady_state']={'erp':erp,'growth':g,'payout':payout,'pe_before':payout/(a+erp-g),'pe_after':payout/(b+erp-g),'assumption_status':'illustrative only, not a justified fund PE or automatic scenario update'}
  macro.append(item)
result={'schema':'etf.cloud.fundamental_review.v1','created_at':datetime.now(timezone.utc).isoformat(),'snapshot_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'companies':companies,'macro':macro,'blockers':['Current management guidance and full official financial statements not yet automatically reviewed','EPS accounting basis and forecast formation dates unverified','Annual fiscal period is not a verified three-year exit NTM','Credit spread may be unavailable','No automatic scenario or buy-price revision'],'status':'partial_review_no_entry_conclusion'}
with dst.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
print(json.dumps({'companies':len(companies),'changed_requires_review':[c['symbol'] for c in companies if c['fiscal_changes']],'macro_series_compared':len(macro),'status':result['status']}))
