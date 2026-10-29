"""Python standard-library reproduction of site historical chart/state outputs."""
import argparse,json,math,html,hashlib,datetime,bisect
from pathlib import Path
VERSION='price-close-running-peak-forward-window-v1'
BINS=['0–5%','5–10%','10–15%','15–20%','20%+']
def label(dd):
    a=round(-dd,12);return BINS[0 if a<.05 else 1 if a<.10 else 2 if a<.15 else 3 if a<.20 else 4]
def quantile(values,p):
    if not values:return None
    a=sorted(values);z=(len(a)-1)*p;i=int(z);return a[i]+(a[min(i+1,len(a)-1)]-a[i])*(z-i)
def compute(rows,horizon):
    if horizon!='3y'and(not isinstance(horizon,int)or horizon<1):raise ValueError('Invalid horizon')
    if not rows or len({r[0]for r in rows})!=len(rows)or any(not math.isfinite(r[1])or r[1]<=0 for r in rows):raise ValueError('Bad prices or duplicate dates')
    rows=sorted(rows);peak=0;states=[]
    for i,(date,price)in enumerate(rows):
        peak=max(peak,price);dd=price/peak-1
        states.append({'date':date,'close':price,'dd':dd,'peak':peak,'ma200':sum(r[1]for r in rows[i-199:i+1])/200 if i>=199 else None,'bin':label(dd)})
    current=states[-1]['bin'];lows=[];returns=[];observed=0;nonoverlap=0;last=-1;incomplete=[];episodes=[];episode=0;inside=False;supported=set();dates=[r[0]for r in rows]
    episodes=[-1]*len(rows);definitions=[];peak=rows[0][1];anchor=0;active=None;outside=0;inside_n=0
    for i,(_,value)in enumerate(rows):
        if active is None:
            if value>=peak:peak=value;anchor=i;continue
            active=len(definitions);definitions.append({'recovered':False})
            for j in range(anchor,i+1):episodes[j]=active
        elif value>=peak:definitions[active]['recovered']=True;active=None;peak=value;anchor=i
        else:episodes[i]=active
    for i,s in enumerate(states):
        if s['bin']!=current:continue
        observed+=1
        if horizon=='3y':
            date=datetime.date.fromisoformat(s['date'])
            try:target=date.replace(year=date.year+3)
            except ValueError:target=date.replace(year=date.year+3,day=28)
            end=bisect.bisect_left(dates,target.isoformat(),i+1)
        else:end=i+horizon
        stop=min(end,len(rows)-1);low=min(r[1]for r in rows[i:stop+1])
        if end>=len(states):
            incomplete.append({'date':rows[i][0],'observed_sessions':stop-i,'observed_loss_lower_bound':max(0,1-low/s['close'])if stop>i else None});continue
        lows.append(low/s['close']-1);returns.append(rows[end][1]/s['close']-1)
        if episodes[i]>=0:supported.add(episodes[i]);inside_n+=1
        else:outside+=1
        if i>last:nonoverlap+=1;last=end
    result={'bin':current,'n':len(lows),'observed':observed,'censored':len(incomplete),'nonoverlap':nonoverlap,'episode_count':len(supported),'recovered_episode_count':sum(definitions[i]['recovered']for i in supported),'open_episode_count':sum(not definitions[i]['recovered']for i in supported),'inside_episode_observations':inside_n,'outside_episode_observations':outside,'episode_policy':'Any strict decline; retrospective latest-peak anchor to recovery exclusive; counts are not independent samples','downside':[quantile(lows,p)for p in [.1,.5,.9]],'returns':[quantile(returns,p)for p in [.1,.5,.9]],'incomplete_recent':incomplete[-10:],'censored_loss_lower_bound':[quantile([r['observed_loss_lower_bound']for r in incomplete if r['observed_loss_lower_bound']is not None],p)for p in [.1,.5,.9]],'horizon':horizon,'scope':'price close basis; observed losses in incomplete windows are lower bounds of eventual loss magnitude, not lower bounds of signed return'}
    return states,result
def main():
    p=argparse.ArgumentParser();p.add_argument('--input',default='data.json');p.add_argument('--symbol',default='QQQM');p.add_argument('--horizon');a=p.parse_args()
    source=Path(a.input);d=json.loads(source.read_text(encoding='utf8'));a.horizon=a.horizon or d.get('params',{}).get('horizon',126);a.horizon='3y'if a.horizon=='3y'else int(a.horizon);rows=d['series'][a.symbol];states,result=compute(rows,a.horizon)
    output={'algorithm_version':VERSION,'distribution_algorithm_version':'any-decline-episodes-v7','symbol':a.symbol,'horizon':a.horizon,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'last_state':states[-1],'result':result,'scope':'Price-only descriptive history, not a bottom forecast'}
    target=Path(a.symbol+'_reproduced.json');target.write_text(json.dumps(output,ensure_ascii=False,indent=2),encoding='utf8')
    values=[s['close']for s in states];lo=min(values);hi=max(values);points=' '.join(f'{50+900*i/max(1,len(states)-1):.2f},{280-230*(x-lo)/(hi-lo or 1):.2f}'for i,x in enumerate(values))
    chart=f'<!doctype html><meta charset="utf-8"><title>{html.escape(a.symbol)} reproduced</title><main style="max-width:1100px;margin:40px auto;font:16px/1.8 sans-serif"><h1>{html.escape(a.symbol)} · 可复现价格图</h1><p>{states[0]["date"]}—{states[-1]["date"]}；价格口径，不含分红；固定前向{"3日历年"if a.horizon=="3y"else str(a.horizon)+"交易日"}窗口。</p><svg viewBox="0 0 1000 320" style="width:100%;background:#f2f6ef"><polyline fill="none" stroke="#206f5d" stroke-width="2" points="{points}"/></svg><pre>{html.escape(json.dumps(output,ensure_ascii=False,indent=2))}</pre></main>'
    Path(a.symbol+'_chart.html').write_text(chart,encoding='utf8');print(json.dumps(result,ensure_ascii=True))
if __name__=='__main__':main()
