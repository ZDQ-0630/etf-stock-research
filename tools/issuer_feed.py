"""Discover candidates in two official issuer RSS feeds; never interpret financial facts."""
from datetime import datetime,timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import hashlib,json,sys
FEEDS={'NVDA':('https://nvidianews.nvidia.com/cats/press_release.xml',{'nvidianews.nvidia.com','investor.nvidia.com'}),'META':('https://investor.atmeta.com/rss/pressrelease.aspx',{'investor.atmeta.com'})}
def clock():return datetime.now(timezone.utc).isoformat()
def parse(raw,issuer,hosts):
 if len(raw)>2_000_000 or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():raise ValueError('Unsafe or oversized XML')
 root=ET.fromstring(raw);items=[]
 for item in root.findall('./channel/item')[:40]:
  title=(item.findtext('title') or '').strip();link=(item.findtext('link') or '').strip();identifier=(item.findtext('guid') or link).strip();parsed=urlparse(link)
  if not title or not identifier or parsed.scheme!='https' or parsed.hostname not in hosts:continue
  date=item.findtext('pubDate');published=None
  try:
   d=parsedate_to_datetime(date)
   if d.tzinfo is not None:published=d.astimezone(timezone.utc).isoformat()
  except (TypeError,ValueError,OverflowError):pass
  items.append({'issuer':issuer,'id_sha256':hashlib.sha256(identifier.encode()).hexdigest(),'title':title,'url':link,'published_at':published,'published_date_unverified':None if published else date,'status':'candidate_metadata_only_full_release_not_reviewed'})
 return items
def fetch(pair):
 issuer,(url,hosts)=pair;result={'issuer':issuer,'source_url':url,'retrieved_at':None,'status':'blocked','items':[]}
 try:
  with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 ETF research feed reader','Accept':'application/rss+xml,application/xml,text/xml'}),timeout=15) as r:raw=r.read(2_000_001)
  result.update(retrieved_at=clock(),source_sha256=hashlib.sha256(raw).hexdigest());result['items']=parse(raw,issuer,hosts)
  result['status']='retrieved_candidates_unreviewed' if result['items'] else 'blocked_empty_or_unexpected_feed'
 except Exception as e:result.update(retrieved_at=clock(),error=type(e).__name__+': '+str(e)[:150])
 return result
def main():
 if len(sys.argv)!=3:raise SystemExit('usage: python tools/issuer_feed.py prior-issuer-feed.json new-output.json')
 prior,dest=map(Path,sys.argv[1:]);previous={}
 if prior.exists():
  d=json.loads(prior.read_text(encoding='utf8'));previous={x['issuer']:{i['id_sha256'] for i in x['items']} for x in d['feeds'] if x['status']=='retrieved_candidates_unreviewed'}
 with ThreadPoolExecutor(max_workers=2) as pool:feeds=list(pool.map(fetch,FEEDS.items()))
 for f in feeds:
  old=previous.get(f['issuer'])
  for item in f['items']:item['previously_seen']=item['id_sha256'] in old if old is not None else None
 output={'schema':'etf.cloud.issuer_feed.v1','checked_at':clock(),'feeds':feeds,'uncovered':['MSFT','GOOGL','AMZN','TSM','MU','other industry and macro sources'],'scope':'Issuer feed metadata discovery only. New or changed items require full original-source, period and accounting review; no scenario update and no signal.'}
 with dest.open('x',encoding='utf8') as f:json.dump(output,f,ensure_ascii=False,indent=2,allow_nan=False)
 print(json.dumps({'feeds_checked':len(feeds),'feeds_retrieved':sum(f['status']=='retrieved_candidates_unreviewed' for f in feeds),'new_unreviewed_candidates':sum(item['previously_seen'] is False for f in feeds for item in f['items'])}))
if __name__=='__main__':main()
