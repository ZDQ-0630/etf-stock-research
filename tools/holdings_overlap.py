"""Direct equity overlaps of a dated public holding snapshot; never sum swaps as NAV."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,itertools,json,sys
if len(sys.argv)!=2:raise SystemExit('usage: python tools/holdings_overlap.py new-output.json')
dest=Path(sys.argv[1]);src=Path('web/full-holdings.json');raw=src.read_bytes();data=json.loads(raw);funds=[]
for f in data['funds']:
 by={}
 for r in f['records']:
  if str(r.get('type','')).lower() not in {'common stock','stock','equity'}:continue
  sym=r.get('symbol');weight=r.get('weight')
  if not isinstance(sym,str) or not sym or not isinstance(weight,(int,float)) or weight<0:continue
  by[sym]=by.get(sym,0)+weight
 funds.append({'fund':f['fund'],'date':f.get('date'),'direct_equity':by,'scope':'Frozen snapshot; exact ticker matches only, unverified currency/share-class aliases. Derivatives/cash/collateral are excluded.'})
pairs=[]
for a,b in itertools.combinations(funds,2):
 shared=set(a['direct_equity'])&set(b['direct_equity']);value=sum(min(a['direct_equity'][s],b['direct_equity'][s]) for s in shared)
 pairs.append({'funds':[a['fund'],b['fund']],'dates':[a['date'],b['date']],'common_tickers':sorted(shared),'observed_direct_equity_overlap':value,'status':'partial_lower_bound_not_full_economic_overlap' if 'DRAM' in [a['fund'],b['fund']] else 'exact_ticker_direct_equity_only'})
result={'schema':'etf.cloud.holdings_overlap.v1','created_at':datetime.now(timezone.utc).isoformat(),'snapshot_sha256':hashlib.sha256(raw).hexdigest(),'source':'web/full-holdings.json','funds':funds,'pairs':pairs,'status':'frozen_data_not_current','limitations':['Latest holdings not refreshed','Swaps and derivatives excluded','Ticker aliases and share classes not reconciled','Not an account portfolio']}
with dest.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
print(json.dumps({'funds':len(funds),'pairs':len(pairs),'status':result['status']}))
