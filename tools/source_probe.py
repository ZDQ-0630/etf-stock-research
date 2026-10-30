"""Check selected public source endpoints in cloud; not a market-data adapter."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import hashlib,json,sys

def now(): return datetime.now(timezone.utc).isoformat()
jobs=[('nasdaq_'+s,'https://api.nasdaq.com/api/analyst/'+s+'/earnings-forecast','json') for s in ['NVDA','MSFT','GOOGL','AMZN','META','TSM','MU']]
jobs += [('fred_10y','https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10','csv'),('nyse_calendar','https://www.nyse.com/trade/hours-calendars','html')]
def probe(job):
 name,url,kind=job;out={'name':name,'url':url,'attempted_at':now(),'ok':False,'scope':'endpoint accessibility and limited shape only; no data validation or model run'}
 try:
  request=Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; research availability check)','Accept':'application/json,text/csv,text/html'})
  with urlopen(request,timeout=18) as response:
   body=response.read(2_000_001);out.update(http_status=response.status,content_type=response.headers.get('content-type'),final_url=response.geturl())
  if not body or len(body)>2_000_000: raise ValueError('empty or oversized response')
  out.update(source_sha256=hashlib.sha256(body).hexdigest(),bytes=len(body))
  if kind=='json':
   obj=json.loads(body);data=obj.get('data');out['shape_note']='JSON data object present' if isinstance(data,dict) and bool(data) else 'missing nonempty data object';out['ok']=isinstance(data,dict) and bool(data)
  elif kind=='csv':out['ok']=b'DGS10' in body[:300] and b'\n' in body;out['shape_note']='series header only; values not validated'
  else:out['ok']=b'NYSE' in body[:100000] and b'holiday' in body[:100000].lower();out['shape_note']='HTML markers only; calendar not validated'
 except HTTPError as e:out.update(http_status=e.code,error='HTTP '+str(e.code))
 except Exception as e:out['error']=type(e).__name__+': '+str(e)[:160]
 out['completed_at']=now();return out
if len(sys.argv)!=2:raise SystemExit('usage: python tools/source_probe.py <new-output.json>')
out=Path(sys.argv[1]);
if out.exists():raise SystemExit('refusing to overwrite')
with ThreadPoolExecutor(max_workers=5) as pool: results=list(pool.map(probe,jobs))
report={'schema':'etf.cloud_source_probe.v1','completed_at':now(),'scope':'availability/shape only; no research conclusions, no raw source redistribution','sources':results}
with out.open('x',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
print(json.dumps({'sources':len(results),'reachable_with_expected_shape':sum(r['ok'] for r in results),'failed':sum(not r['ok'] for r in results)}))
