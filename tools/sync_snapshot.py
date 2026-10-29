"""Validate and synchronize editable public snapshots. Standard library only."""
import argparse,datetime,hashlib,json,math,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def finite(x):return isinstance(x,(int,float))and not isinstance(x,bool)and math.isfinite(x)
def validate(kind,x):
    if not isinstance(x,dict):raise ValueError('Snapshot must be an object')
    if kind=='history':
        for symbol,rows in x['series'].items():
            if not rows:raise ValueError(f'{symbol}: empty history')
            dates=[]
            for date,price in rows:
                datetime.date.fromisoformat(date);dates.append(date)
                if not finite(price)or price<=0:raise ValueError(f'{symbol}: invalid price')
            if dates!=sorted(set(dates)):raise ValueError(f'{symbol}: dates must be unique and ascending')
    elif kind=='stock':
        seen=set()
        for c in x['companies']:
            symbol=c['symbol']
            if not isinstance(symbol,str)or not symbol or symbol in seen:raise ValueError('Duplicate or missing symbol')
            seen.add(symbol);q=c['quote'];datetime.date.fromisoformat(q['date'])
            if not finite(q['price'])or q['price']<=0:raise ValueError('Invalid regular-session price')
            if not q.get('source'):raise ValueError('Quote source required')
            for f in c.get('forecasts',[]):
                if f.get('eps_mean')is not None and not finite(f['eps_mean']):raise ValueError('Invalid EPS')
                # Null means unknown: do not manufacture a formation date.
                if f.get('asof')is not None:datetime.date.fromisoformat(f['asof'][:10])
    else:raise ValueError('Unsupported snapshot kind')
def write_snapshot(web,kind,x):
    x['local_snapshot_update']={'kind':kind,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'verification':'manual_unverified','static_reports_recomputed':False}
    name,var=('data','RESEARCH_DATA')if kind=='history'else('stock-data','STOCK_DATA')
    plain=json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)
    script='window.'+var+'='+json.dumps(x,ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('<','\\u003c')+';'
    for suffix,content in [('.json',plain),('.js',script)]:
        p=web/(name+suffix);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(content,encoding='utf8');os.replace(tmp,p)
    if kind=='stock'and(web/'hub-data.json').exists():
        h=json.loads((web/'hub-data.json').read_text(encoding='utf8'))
        for c in x['companies']:h.setdefault('latest_quotes',{})[c['symbol']]=c['quote']
        (web/'hub-data.json').write_text(json.dumps(h,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
        (web/'hub-data.js').write_text('window.HUB_DATA='+json.dumps(h,ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('<','\\u003c')+';',encoding='utf8')
    # A manual update must never silently inherit the published snapshot's authority.
    banner="(()=>{const p=document.createElement('p');p.textContent='此本地副本已手动更新快照，未经独立核实。数据来源/静态研究表仍属于原发布版本，未重跑；请记录新输入、期间和来源，不把原报告当成更新后的验证。';p.style.cssText='padding:16px;background:#fff0cf;color:#694d21;margin:0';document.body.prepend(p)})();"
    (web/'snapshot-update.js').write_text(banner,encoding='utf8')
    for p in web.glob('*.html'):
        t=p.read_text(encoding='utf8')
        if 'src="snapshot-update.js"'not in t:p.write_text(t.replace('</body>','<script src="snapshot-update.js"></script></body>'),encoding='utf8')
def main():
    p=argparse.ArgumentParser();p.add_argument('--kind',choices=['history','stock'],required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--write',action='store_true');p.add_argument('--web',type=Path,default=ROOT/'web');a=p.parse_args()
    raw=a.input.read_bytes();x=json.loads(raw);validate(a.kind,x)
    if a.write:write_snapshot(a.web,a.kind,x)
    print(json.dumps({'validation':'passed','written':a.write,'kind':a.kind,'input_sha256':hashlib.sha256(raw).hexdigest(),'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'note':'Syntax and basic schema only; no external data verification. Static reports are not recomputed.'}))
if __name__=='__main__':main()
