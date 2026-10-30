"""Create immutable partial snapshot. External data is unverified; no execution or trading."""
import csv,hashlib,io,json,math,sys,urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
from pathlib import Path
from urllib.request import Request,urlopen
from zoneinfo import ZoneInfo

SYMS=['QQQM','SMH','SOXX','DRAM','NVDA','MSFT','GOOGL','AMZN','META','TSM','MU']
STOCKS=SYMS[4:]
FRED=['DGS10','DFII10','BAMLH0A0HYM2']
HOLIDAYS=set('2026-01-01 2026-01-19 2026-02-16 2026-04-03 2026-05-25 2026-06-19 2026-07-03 2026-09-07 2026-11-26 2026-12-25'.split())
EARLY={'2026-11-27','2026-12-24'}
def utc():return datetime.now(timezone.utc)
def latest_date(clock):
 d=clock.astimezone(ZoneInfo('America/New_York'))
 if d.year!=2026:raise ValueError('calendar not reviewed for this year')
 day=d.date()
 while True:
  if day.year!=2026:raise ValueError('calendar outside reviewed year')
  s=day.isoformat();close=13 if s in EARLY else 16
  if day.weekday()<5 and s not in HOLIDAYS and (day!=d.date() or d.hour>=close):return s
  day-=timedelta(days=1)
def get(job):
 key,url=job;rec={'key':key,'source_url':url,'started_at':utc().isoformat(),'ok':False}
 try:
  req=Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/csv,*/*','Origin':'https://www.nasdaq.com'})
  with urlopen(req,timeout=20) as r:b=r.read(3_000_001);rec.update(http_status=r.status,content_type=r.headers.get('content-type'))
  if not b or len(b)>3_000_000:raise ValueError('empty or oversized response')
  rec.update(source_sha256=hashlib.sha256(b).hexdigest(),retrieved_at=utc().isoformat(),ok=True)
  return rec,b
 except Exception as e:rec.update(error=type(e).__name__+': '+str(e)[:150],retrieved_at=utc().isoformat());return rec,None
def number(v):
 try:
  n=float(str(v).replace('$','').replace(',','').strip())
  return n if math.isfinite(n) else None
 except (TypeError,ValueError):return None
def parse_nasdaq(raw,symbol,date):
 j=json.loads(raw);d=j.get('data') or {};rows=(d.get('tradesTable') or {}).get('rows') or []
 if str(d.get('symbol','')).upper()!=symbol:return None
 for r in rows:
  try:day=datetime.strptime(r['date'],'%m/%d/%Y').date().isoformat()
  except (KeyError,ValueError):continue
  if day==date:return number(r.get('close'))
 return None
def parse_yahoo(raw,symbol,date):
 d=json.loads(raw)['chart']['result'][0]
 if d['meta'].get('symbol')!=symbol or d['meta'].get('currency')!='USD':return None
 prices=d['indicators']['quote'][0]['close']
 for t,v in zip(d.get('timestamp',[]),prices):
  day=datetime.fromtimestamp(t,timezone.utc).astimezone(ZoneInfo('America/New_York')).date().isoformat()
  if day==date:return number(v)
 return None
def forecasts(raw,symbol,baseline):
 d=json.loads(raw).get('data') or {}
 if str(d.get('symbol','')).upper()!=symbol:return {'status':'symbol_mismatch'}
 fy=d.get('yearlyForecast') or {};rows=fy.get('rows') or [];old={v['end']:v for v in baseline.get('forecasts',[])};out=[]
 for r in rows:
  period=r.get('fiscalEnd');before=old.get(period);value=number(r.get('consensusEPSForecast'));count=number(r.get('noOfEstimates'))
  out.append({'fiscal_end':period,'vendor_eps':value,'analyst_count':count,'vendor_asof':fy.get('asOf'),'previous_vendor_eps':before.get('eps_mean') if before else None,'difference':value-before['eps_mean'] if value is not None and before and isinstance(before.get('eps_mean'),(int,float)) else None,'comparability':'fiscal labels match; GAAP/adjusted basis and forecast formation time unverified'})
 return {'status':'retrieved_unverified','rows':out,'scenario_updates':'none; no automatic adoption'}
def fred(raw,series):
 rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))));out=[]
 for r in rows:
  v=number(r.get(series));d=r.get('observation_date') or r.get('DATE')
  if v is not None and d:out.append({'date':d,'value_pct':v})
 return out[-2:]
def main():
 if len(sys.argv)!=2:raise SystemExit('usage: python tools/cloud_snapshot.py <new-output-dir>')
 dest=Path(sys.argv[1]);dest.mkdir(parents=True,exist_ok=False);started=utc();date=latest_date(started);end=started.date().isoformat();start=(started.date()-timedelta(days=16)).isoformat()
 jobs=[]
 for s in SYMS:
  assetclass='etf' if s in SYMS[:4] else 'stocks'
  jobs += [('nasdaq_'+s,'https://api.nasdaq.com/api/quote/'+s+'/historical?assetclass='+assetclass+'&fromdate='+start+'&todate='+end+'&limit=50'),('yahoo_'+s,'https://query1.finance.yahoo.com/v8/finance/chart/'+s+'?range=1mo&interval=1d')]
 jobs += [('forecast_'+s,'https://api.nasdaq.com/api/analyst/'+s+'/earnings-forecast') for s in STOCKS]
 fred_start=(started.date()-timedelta(days=45)).isoformat()
 jobs += [('fred_'+s,'https://fred.stlouisfed.org/graph/fredgraph.csv?id='+s+'&cosd='+fred_start) for s in FRED]
 with ThreadPoolExecutor(max_workers=6) as pool:responses=list(pool.map(get,jobs))
 records={r['key']:r for r,b in responses};bodies={r['key']:b for r,b in responses if b is not None}
 for key in list(bodies):
  if key.startswith(('nasdaq_','forecast_','yahoo_')):
   try:json.loads(bodies[key])
   except Exception:records[key].update(ok=False,error='not valid JSON');bodies.pop(key)
 base={x['symbol']:x for x in json.loads(Path('web/stock-data-monitor-20261029.json').read_text(encoding='utf8'))['companies']}
 prices=[]
 for s in SYMS:
  row={'symbol':s,'session_date':date,'status':'blocked','price_basis':'daily close/last, unadjusted claim not independently verified','sources':{}}
  for prefix,parser in [('nasdaq_',parse_nasdaq),('yahoo_',parse_yahoo)]:
   key=prefix+s
   try:val=parser(bodies[key],s,date)
   except Exception:val=None
   row['sources'][prefix[:-1]]={'value':val,'retrieved_at':records[key].get('retrieved_at'),'sha256':records[key].get('source_sha256'),'url':records[key]['source_url']}
  a=row['sources']['nasdaq']['value'];b=row['sources']['yahoo']['value'];row['agreement']=abs(a-b)<=max(.01,a*.001) if a is not None and b is not None and a>0 and b>0 else None
  row['reason']='Date-only upstream data cannot establish official close timestamps or extraordinary closures; requires independent source and calendar review.'
  prices.append(row)
 estimates={}
 for s in STOCKS:
  try:estimates[s]=forecasts(bodies['forecast_'+s],s,base[s])
  except Exception as e:estimates[s]={'status':'blocked','reason':type(e).__name__}
 macro={}
 for s in FRED:
  try:macro[s]={'observations':fred(bodies['fred_'+s],s),'source':records['fred_'+s]['source_url'],'status':'retrieved_requires_review'}
  except Exception as e:macro[s]={'status':'blocked','reason':type(e).__name__}
 result={'schema':'etf.cloud.partial_snapshot.v1','started_at':started.isoformat(),'completed_at':utc().isoformat(),'latest_scheduled_session':date,'baseline_sha256':hashlib.sha256(Path('web/stock-data-monitor-20261029.json').read_bytes()).hexdigest(),'calendar_note':'Scheduled US exchange calendar only; unplanned closures not independently verified.','prices':prices,'forecasts':estimates,'macro':macro,'sources':list(records.values()),'blocked':['independent close timestamps and source rights','company results and management guidance content review','ETF and stock model risk/valuation refresh','cost, FX and exposures','persisted previous run comparison','website sync and notifications'],'status':'partial_no_entry_conclusion','scope':'Data retrieval and vendor snapshot comparison only; not a complete model run or buy signal.'}
 file=dest/'snapshot.json'
 with file.open('x',encoding='utf8') as f:json.dump(result,f,ensure_ascii=False,indent=2,allow_nan=False)
 # Do not relabel date-only observations as timestamped official closes. The core gate blocks them.
 model={'run_id':'snapshot_'+started.strftime('%Y%m%dT%H%M%SZ'),'baseline_stocks':{'companies':list(base.values())},'quotes':{'observations':[]},'calendar':None}
 with (dest/'model-input.json').open('x',encoding='utf8') as f:json.dump(model,f,ensure_ascii=False,indent=2,allow_nan=False)
 digest=hashlib.sha256(file.read_bytes()).hexdigest();(dest/'SHA256.txt').write_text(digest+'  snapshot.json\n',encoding='ascii')
 print(json.dumps({'prices':len(prices),'pair_agreements':sum(p['agreement'] is True for p in prices),'forecast_snapshots':sum(v['status']=='retrieved_unverified' for v in estimates.values()),'source_errors':sum(not x['ok'] for x in records.values()),'status':result['status'],'snapshot_sha256':digest}))
if __name__=='__main__':main()
