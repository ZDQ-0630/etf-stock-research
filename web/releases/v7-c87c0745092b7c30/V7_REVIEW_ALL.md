# ETF V7 审阅起点

当前算法：declared-earnings-periods-v7。
v6_calc.js 保留兼容文件名，包含V7新增约束与事件编号；不是旧V6算法。
当前 v6_calc.js 原始字节 SHA256：b3a085a05abacd581ac4d09391a1b51e0826974f368945087f2d8124efa4840a
固定审阅快照：v7-c87c0745092b7c30。文件哈希核对原始下载字节，不要先转换换行或编码。

请先审阅 v6_calc.js、app.js、model.js、v7_episodes.py、v7_calendar_tilt.py。
两份 *_tests.py 可检查Python事件及EPS形状规格。reproduce.py 是纯标准库价格图复现。
data/ 包含本次冻结的事件计数、形状诊断和测试记录。
Python诊断脚本还依赖V6/V3模块及原始行情，完整离线重跑仍需要此前完整复现包；单文件文本不是完整运行环境。

图表复现：python reproduce.py --input data.json --symbol QQQM --horizon 3y
根网站data.json是冻结2026-10-26收盘的图表数据。不是当前报价，不含完整历史策略重跑输入。
V5/V6报告和原v6_calc_archived.js.txt是历史对照，不要当作当前实现。

当前修改：增长、倍数、目标年化、EPS默认留空；必须声明盈利分母和对应期间；浅回撤从峰值锚点编号并区分恢复状态；年度EPS保持年度总额的期内形状敏感性；主审阅表不突出条件均值差。
限制：标签与日期检查不能核实手填盈利的真实性。完整基金EPS、三年退出盈利、真实季度季节性、外部独立验证仍缺失。测试通过不代表投资有效。所有前瞻输出均为条件假设，不是底部信号。

请分别报告实际读过、运行过、外部核实过和未完成的部分。每个错误给出文件/函数、反例、影响和修复建议。不要把相同规格的交叉复算叫作外部独立审计。




## model.js
SHA256: 485b02211349c167d63b3b72d9c0e31c785c41ebe41cf1c428d8633f7e7c2b28

```javascript
(function(g){'use strict';
 const VERSION='price-close-running-peak-forward-window-v1';
 const CALENDAR={source:'https://www.nyse.com/markets/hours-calendars',verified_at:'2026-10-28',start:'2025-01-01',end:'2027-12-31',holidays:['2025-01-09','2025-01-01','2025-01-20','2025-02-17','2025-04-18','2025-05-26','2025-06-19','2025-07-04','2025-09-01','2025-11-27','2025-12-25','2026-01-01','2026-01-19','2026-02-16','2026-04-03','2026-05-25','2026-06-19','2026-07-03','2026-09-07','2026-11-26','2026-12-25','2027-01-01','2027-01-18','2027-02-15','2027-03-26','2027-05-31','2027-06-18','2027-07-05','2027-09-06','2027-11-25','2027-12-24'],early_closes:['2025-07-03','2025-11-28','2025-12-24','2026-11-27','2026-12-24','2027-11-26']};
 const bins=['0–5%','5–10%','10–15%','15–20%','20%+'];
 function bin(dd){const a=Math.round(-dd*1e12)/1e12;return bins[a<.05?0:a<.10?1:a<.15?2:a<.20?3:4]}
 function states(rows){let peak=0,sum=0;return rows.map((r,i)=>{peak=Math.max(peak,r[1]);sum+=r[1];if(i>=200)sum-=rows[i-200][1];return {date:r[0],close:r[1],dd:r[1]/peak-1,peak,ma200:i>=199?sum/200:null,bin:bin(r[1]/peak-1)}})}
 function q(a,p){if(!a.length)return null;const b=[...a].sort((x,y)=>x-y),x=(b.length-1)*p,i=Math.floor(x);return b[i]+(b[Math.min(i+1,b.length-1)]-b[i])*(x-i)}
 function distribution(rows,h=126){if(!Number.isInteger(h)||h<1)throw Error('Invalid horizon');const s=states(rows);if(!s.length)return null;const b=s.at(-1).bin,ids=[],lows=[],returns=[];let last=-1,nonoverlap=0,observed=0;for(let i=0;i<s.length;i++){if(s[i].bin!==b)continue;observed++;if(i+h>=s.length)continue;let min=Infinity;for(let j=i+1;j<=i+h;j++)min=Math.min(min,s[j].close);ids.push(i);lows.push(Math.min(0,min/s[i].close-1));returns.push(s[i+h].close/s[i].close-1);if(i>last){nonoverlap++;last=i+h}}return {bin:b,n:ids.length,observed,censored:observed-ids.length,nonoverlap,downside:[.1,.5,.9].map(p=>q(lows,p)),returns:[.1,.5,.9].map(p=>q(returns,p))}}
 function execution(v,integer=false){const {budget,entry,target,years,fx0,fx1,bps,fee,fx_bps,cash_rate,shock}=v;if(![budget,entry,target,years,fx0,fx1,bps,fee,fx_bps,cash_rate,shock].every(Number.isFinite)||Math.min(budget,entry,target,years,fx0,fx1)<=0||years>100||bps<0||bps>=10000||fx_bps<0||fx_bps>=10000||fee<0||cash_rate<=-1||shock<=-1||shock>0)throw Error('请检查价格、资金、年数、汇率和费用');const spread=fx_bps/10000,c=bps/10000,usd=budget*(1-spread)/fx0,affordable=Math.max(0,(usd-fee)/(entry*(1+c))),units=integer?Math.floor(affordable):affordable,cash=usd-units*entry*(1+c)-(units>0?fee:0),steps=Math.max(4,Math.ceil(years*4)),fractions=[...new Set([...Array(steps+1)].map((_,k)=>k/steps).concat([1/3]))].sort((a,b)=>a-b),path=[];let peak=budget,dd=0;for(const f of fractions){const t=years*f,p=f<=1/3?entry*(1+shock)**(f*3):entry*(1+shock)*(target/(entry*(1+shock)))**((f-1/3)*1.5),cashT=cash*(1+cash_rate)**t,fx=fx0*(fx1/fx0)**f;let value=(units*p+cashT)*fx;if(f===1)value=((units>0?units*target*(1-c)-fee:0)+cashT)*fx1*(1-spread);if(!Number.isFinite(value))throw Error('计算超出范围');path.push({year:t,price:p,wealth_sgd:value});peak=Math.max(peak,value);dd=Math.min(dd,value/peak-1)}const terminal=path.at(-1).wealth_sgd;return {units,cash_usd:cash,terminal_sgd:terminal,annualized:terminal>0?(terminal/budget)**(1/years)-1:null,path_max_drawdown:dd,path}}
 function scenario(x){if(![x.reference,x.entry,x.years,x.g1,x.growth,x.multiple,x.hurdle].every(Number.isFinite)||x.reference<=0||x.entry<=0||x.years<3||x.years>20||x.g1<=-1||x.growth<=-1||x.multiple<=0||x.hurdle<=-1)throw Error('请填写有效的正价格与倍数，年数3–20，增速大于−100%');const target=x.reference*(1+x.g1)*(1+x.growth)**(x.years-1)*x.multiple;const v={...x,target},fractional=execution(v,false),integer=execution(v,true),c=x.bps/10000,f=x.fx_bps/10000,required=x.budget*(1+x.hurdle)**x.years/(x.fx1*(1-f)),unitsNeeded=(required+x.fee)/(target*(1-c)),maxEntry=(x.budget*(1-f)/x.fx0-x.fee)/(unitsNeeded*(1+c));if(!Number.isFinite(maxEntry)||maxEntry<=0)throw Error('资金不足以支付假设费用，或参数超出范围');return {target,maxEntry,fractional,integer,scope:'Manual earnings/multiple scenario; maximum entry assumes fractional deployment, not a bottom forecast.'}}
 function validDate(d){return /^\d{4}-\d{2}-\d{2}$/.test(d)&&!isNaN(Date.parse(d+'T00:00:00Z'))&&new Date(d+'T00:00:00Z').toISOString().slice(0,10)===d}
 function closed(d){return [0,6].includes(new Date(d+'T00:00:00Z').getUTCDay())||CALENDAR.holidays.includes(d)}
 function lastComplete(now=new Date()){const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(now).filter(p=>p.type!=='literal').map(p=>[p.type,p.value]));let d=parts.year+'-'+parts.month+'-'+parts.day;const t=Number(parts.hour)*60+Number(parts.minute),close=(CALENDAR.early_closes.includes(d)?13:16)*60+15;if(t<close)d=new Date(Date.parse(d+'T00:00:00Z')-86400000).toISOString().slice(0,10);while(closed(d))d=new Date(Date.parse(d+'T00:00:00Z')-86400000).toISOString().slice(0,10);return d}
 function validateRows(rows,symbol,known,now=new Date()){if(!known.includes(symbol))throw Error('不支持的标的');if(!Array.isArray(rows)||rows.length===0||rows.length>50000)throw Error('请提供1–50,000行数据');const seen=new Set(),last=lastComplete(now);return rows.map(r=>{const date=Array.isArray(r)?r[0]:r.date,raw=Array.isArray(r)?r[1]:(r.close??r.price),price=typeof raw==='number'?raw:(typeof raw==='string'&&raw.trim()!==''?Number(raw):NaN);if(!validDate(date)||!Number.isFinite(price)||price<=0)throw Error('每行需要真实日期YYYY-MM-DD与正数close');if(date>last)throw Error('不能把未来或尚未完整收盘的日期导入历史');if([0,6].includes(new Date(date+'T00:00:00Z').getUTCDay()))throw Error('美股ETF周末数据请先核实');if(seen.has(date))throw Error('导入文件内日期重复：'+date);seen.add(date);return [date,price]}).sort((a,b)=>a[0].localeCompare(b[0]))}
 const baseValidateRows=validateRows;
 function calendarValidateRows(...args){const rows=baseValidateRows(...args);for(const r of rows)if(CALENDAR.holidays.includes(r[0]))throw Error('NYSE公告休市日不能作为ETF正常收盘：'+r[0]);return rows}
 g.ResearchMath={VERSION,CALENDAR,bins,bin,states,q,distribution,execution,scenario,validDate,lastComplete,validateRows:calendarValidateRows};
})(typeof window==='undefined'?globalThis:window);

```


## v6_calc.js
SHA256: b3a085a05abacd581ac4d09391a1b51e0826974f368945087f2d8124efa4840a

```javascript
/* V6 cash-flow specification: FX is SGD for one USD; all remaining cash is USD.
   Prices and growth are conditional assumptions, not an investment signal. */
(function(g){'use strict';
 const M=g.ResearchMath, SCENARIO_VERSION='declared-earnings-periods-v7';
 function finite(x){return typeof x==='number'&&Number.isFinite(x)}
 function couponValue(annual,tax,rate,years,at=years){
  let total=0;
  for(let k=1;k<=Math.floor(years);k++)if(k<=at+1e-10)total+=annual*(1-tax)*(1+rate)**(at-k);
  const stub=years-Math.floor(years);
  if(stub>1e-10&&at>=years-1e-10)total+=annual*stub*(1-tax);
  return total;
 }
 function validate(x){
  const keys=['budget','entry','target','years','fx0','fx1','bps','fee','fx_bps','cash_rate','shock','dividend'];
  if(!keys.every(k=>finite(x[k]))||Math.min(x.budget,x.entry,x.target,x.years,x.fx0,x.fx1)<=0||x.years>20||x.bps<0||x.bps>=10000||x.fx_bps<0||x.fx_bps>=10000||x.fee<0||x.cash_rate<=-1||x.shock<=-1||x.shock>0||x.dividend<0)throw Error('请检查价格、资金、年数、费用与分红；FX表示1美元对应的新元数');
  if(x.withholding!==null&&(!finite(x.withholding)||x.withholding<0||x.withholding>1))throw Error('分红预扣率须为0–100%，不清楚时留空');
  if(x.dividend>0&&x.withholding===null)throw Error('已加入现金分红，请先填写适用的假设预扣率；不能根据SGD计价推断税务居民');
 }
 function executionV6(input,integer=false){
  const x={dividend:0,withholding:null,...input};validate(x);
  const f=x.fx_bps/10000,c=x.bps/10000,usd=x.budget*(1-f)/x.fx0;
  const affordable=Math.max(0,(usd-x.fee)/(x.entry*(1+c))),units=integer?Math.floor(affordable):affordable;
  const cash=Math.max(0,usd-units*x.entry*(1+c)-(units>0?x.fee:0));
  const tax=x.withholding??0,dividendValue=couponValue(x.dividend,tax,x.cash_rate,x.years);
  const steps=Math.max(4,Math.ceil(x.years*4)),points=Array.from({length:steps+1},(_,k)=>k/steps);
  points.push(1/3);for(let k=1;k<=Math.floor(x.years);k++)points.push(k/x.years);
  let peak=x.budget,dd=0;
  const path=[...new Set(points)].sort((a,b)=>a-b).map(frac=>{
   const t=x.years*frac,price=frac<=1/3?x.entry*(1+x.shock)**(frac*3):x.entry*(1+x.shock)*(x.target/(x.entry*(1+x.shock)))**((frac-1/3)*1.5);
   const cashT=cash*(1+x.cash_rate)**t+units*couponValue(x.dividend,tax,x.cash_rate,x.years,t),fx=x.fx0*(x.fx1/x.fx0)**frac;
   let value=(units*price+cashT)*fx;
   if(frac===1)value=((units>0?units*x.target*(1-c)-x.fee:0)+cashT)*x.fx1*(1-f);
   peak=Math.max(peak,value);dd=Math.min(dd,value/peak-1);
   return {year:t,price,wealth_sgd:value,cash_usd:cashT};
  });
  const terminal=path.at(-1).wealth_sgd;
  if(!Number.isFinite(terminal))throw Error('参数使计算超出范围');
  return {units,cash_usd:cash,cash_currency:'USD',initial_usd:usd,dividend_per_unit_at_T_usd:dividendValue,terminal_sgd:terminal,annualized:terminal>0?(terminal/x.budget)**(1/x.years)-1:null,path_max_drawdown:dd,path,sale_fee_exceeds_stock_proceeds:units>0&&x.fee>units*x.target*(1-c)};
 }
 function scenarioV6(input){
  const x={dividend:0,withholding:null,fund_fee:0,fee_mode:'deduct',valuation_basis:'unverified',...input};
  if(!['reference','g1','growth','multiple','hurdle','fund_fee'].every(k=>finite(x[k]))||x.reference<=0||x.g1<=-1||x.growth<=-1||x.multiple<=0||x.hurdle<=-1||x.fund_fee<0||x.fund_fee>=1||x.years<3||x.years>20||!['deduct','embedded'].includes(x.fee_mode))throw Error('需要有效的基金年费率与3–20年情景；盈利增速须大于−100%');
  if(!['ttm','ntm','normalized'].includes(x.valuation_basis))throw Error('先声明TTM、NTM或归一化盈利分母；未确认时不输出买价');
  for(const k of ['valuation_date','base_start','base_end','terminal_start','terminal_end'])if(!M.validDate(x[k]))throw Error('需填写估值日及基准/退出盈利窗口，末日不含');
  if(!Number.isInteger(x.years))throw Error('V7盈利窗口目前要求整数持有年数');
  if(addYears(x.base_start,1)!==x.base_end||addYears(x.base_start,x.years)!==x.terminal_start||addYears(x.base_end,x.years)!==x.terminal_end)throw Error('盈利窗口须为一日历年，退出窗口须整体平移持有年数');
  if(x.valuation_basis==='ntm'&&x.base_start!==x.valuation_date)throw Error('NTM窗口必须从估值日开始');
  if(x.valuation_basis==='ttm'&&x.base_end!==x.valuation_date)throw Error('TTM窗口末日必须为估值日');
  if(!finite(x.base_eps)||x.base_eps<=0||typeof x.source_note!=='string'||!x.source_note.trim())throw Error('需填写同一基金份额口径的基准EPS及来源/假设说明；局部持仓EPS不可代填');
  if(x.valuation_basis==='normalized'&&x.source_note.trim().length<12)throw Error('归一化盈利需说明周期期间和调整方法');
  const earnings=(1+x.g1)*(1+x.growth)**(x.years-1),gross=x.reference*earnings*x.multiple,expense=x.fee_mode==='embedded'?1:(1-x.fund_fee)**x.years,target=gross*expense;
  const v={...x,target},fractional=executionV6(v,false),integer=executionV6(v,true),f=x.fx_bps/10000,c=x.bps/10000;
  const required=x.budget*(1+x.hurdle)**x.years/(x.fx1*(1-f)),dividend=fractional.dividend_per_unit_at_T_usd;
  if(!Number.isFinite(required)||required<=0)throw Error('目标回报或持有年数超出可计算范围');
  const requiredUnits=(required+x.fee)/(target*(1-c)+dividend),maxEntry=fractional.initial_usd>x.fee?(fractional.initial_usd-x.fee)/(requiredUnits*(1+c)):null;
  if(maxEntry!==null&&(!Number.isFinite(maxEntry)||maxEntry<=0))throw Error('参数使条件买价超出可计算范围');
  let reverse={status:'no_stock_exposure'};
  if(fractional.units>0){
   const q=fractional.units,net=Math.max(0,(required-fractional.cash_usd*(1+x.cash_rate)**x.years-q*dividend+x.fee)/(q*(1-c))),needFactor=(net/expense)/(x.reference*x.multiple);
   reverse={status:'conditional_breakpoint',required_net_target:net,required_gross_target:net/expense,required_earnings_factor:needFactor,required_uniform_growth:needFactor**(1/x.years)-1,required_later_growth:(needFactor/(1+x.g1))**(1/(x.years-1))-1,required_multiple:(net/expense)/(x.reference*earnings)};
  }
  return {base_eps:x.base_eps,base_pe:x.reference/x.base_eps,terminal_eps:x.base_eps*earnings,terminal_pe:x.reference/x.base_eps*x.multiple,valuation_basis:x.valuation_basis,base_window:[x.base_start,x.base_end],terminal_window:[x.terminal_start,x.terminal_end],target,gross_target:gross,expense_factor:expense,maxEntry,fractional,integer,reverse,earnings_factor:earnings,scope:x.dividend>0?'Conditional cash dividends and price, using user-assumed withholding':'Conditional capital-price return; distributions omitted',decision_status:'not_decision_ready',algorithm_version:SCENARIO_VERSION};
 }
 function addYears(date,n){const [y,m,d]=date.split('-').map(Number),year=y+n,last=new Date(Date.UTC(year,m,0)).getUTCDate();return `${year}-${String(m).padStart(2,'0')}-${String(Math.min(d,last)).padStart(2,'0')}`}
 function endIndex(rows,i,h){if(h!=='3y')return i+Number(h);const target=addYears(rows[i][0],3);let a=i+1,b=rows.length;while(a<b){const c=(a+b)>>1;if(rows[c][0]<target)a=c+1;else b=c}return a}
 function episodeLabels(prices){
  const assignments=prices.map(()=>-1),episodes=[];let peak=prices[0],anchor=0,active=null;
  prices.forEach((v,i)=>{if(active===null){if(v>=peak){peak=v;anchor=i;return}active=episodes.length;episodes.push({anchor,recovery:null,recovered:false});for(let j=anchor;j<=i;j++)assignments[j]=active}
   else if(v>=peak){Object.assign(episodes[active],{recovery:i,recovered:true});active=null;peak=v;anchor=i}else assignments[i]=active});
  return {assignments,episodes};
 }
 function distributionV6(rows,h=126){
  if(h!=='3y'&&(!Number.isInteger(h)||h<1))throw Error('前向窗口无效');
  const states=M.states(rows),current=states.at(-1)?.bin,down=[],returns=[],incomplete=[],supported=new Set();let observed=0,nonoverlap=0,last=-1,episode=0,inEpisode=false;
  const labels=episodeLabels(rows.map(r=>r[1])),episodes=labels.assignments;
  let inside=0,outside=0;

  for(let i=0;i<states.length;i++){
   if(states[i].bin!==current)continue;observed++;const end=endIndex(rows,i,h),observedEnd=Math.min(end,rows.length-1);let low=states[i].close;
   for(let j=i+1;j<=observedEnd;j++)low=Math.min(low,states[j].close);
   if(end>=rows.length){incomplete.push({date:rows[i][0],observed_sessions:observedEnd-i,observed_loss_lower_bound:observedEnd>i?Math.max(0,1-low/states[i].close):null});continue}
   down.push(low/states[i].close-1);returns.push(states[end].close/states[i].close-1);if(episodes[i]>=0){supported.add(episodes[i]);inside++}else outside++;if(i>last){nonoverlap++;last=end}
  }
  return {bin:current,n:returns.length,observed,censored:incomplete.length,nonoverlap,episode_count:supported.size,recovered_episode_count:[...supported].filter(k=>labels.episodes[k].recovered).length,open_episode_count:[...supported].filter(k=>!labels.episodes[k].recovered).length,inside_episode_observations:inside,outside_episode_observations:outside,episode_policy:'Any strict decline; retrospective latest-peak anchor to recovery exclusive; counts are not independent samples',downside:[.1,.5,.9].map(p=>M.q(down,p)),returns:[.1,.5,.9].map(p=>M.q(returns,p)),incomplete_recent:incomplete.slice(-10),censored_loss_lower_bound:[.1,.5,.9].map(p=>M.q(incomplete.map(v=>v.observed_loss_lower_bound).filter(v=>v!==null),p)),horizon:h,scope:'price close basis; observed losses in incomplete windows are lower bounds of eventual loss magnitude, not lower bounds of signed return'};
 }
 Object.assign(M,{HISTORY_VIEW_VERSION:'any-decline-episodes-v7',SCENARIO_VERSION,episodeLabels,couponValue,executionV6,scenarioV6,distributionV6,calendarEndIndex:endIndex});
})(typeof window==='undefined'?globalThis:window);

```


## app.js
SHA256: b625896b94d9d68d9061e368e7b90d415f9c585c2a74f9906e7e5aeb25d76a7d

```javascript
(()=>{'use strict';
const DATA=window.RESEARCH_DATA,M=window.ResearchMath,$=id=>document.getElementById(id),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),fmt=(x,n=2)=>x==null||!Number.isFinite(x)?'—':x.toLocaleString('en-US',{minimumFractionDigits:n,maximumFractionDigits:n}),pct=x=>x==null?'—':fmt(x*100,1)+'%',money=x=>x==null?'—':(x<0?'−':'')+'S$'+fmt(Math.abs(x),0);
const known=Object.keys(DATA.series),KEY='etf_research_local_rows_v1';let local={};const savedRowWarnings={};try{const cache=JSON.parse(localStorage.getItem(KEY)||'{}');for(const [s,v]of Object.entries(cache))if(known.includes(s)){try{local[s]={...v,rows:M.validateRows(v.rows,s,known)}}catch(e){savedRowWarnings[s]=e.message}}}catch(e){savedRowWarnings.all='无法读取浏览器历史缓存：'+e.message}
function rowsFor(s){const map=new Map(DATA.series[s].map(r=>[r[0],r[1]]));for(const r of local[s]?.rows??[])map.set(r[0],r[1]);return [...map].sort((a,b)=>a[0].localeCompare(b[0]))}
function save(){try{localStorage.setItem(KEY,JSON.stringify(local));return true}catch{return false}}
function download(name,obj){const blob=new Blob([typeof obj==='string'?obj:JSON.stringify(obj,null,2)],{type:typeof obj==='string'?'text/csv':'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),800)}
function options(select){if(!select)return;select.innerHTML=known.map(s=>`<option value="${s}">${s==='QQQ'?'QQQ · 长历史代理':s}</option>`).join('');select.value='QQQM'}
function gate(){const e=DATA.evidence,now=Date.now(),due=e.events.some(v=>v.scheduled_at&&Date.parse(v.scheduled_at)<=now&&!v.actual&&v.event_status_at_snapshot!=='already_reported'),expired=!e.last_review||Date.parse(e.last_review.payload.valid_until)<=now;return e.active_conclusion_allowed&&!due&&!expired}
function renderHome(){if($('homeView')){const active=gate();$('homeStatus').textContent=active?'有条件的研究判断':'结论已到复核时点';$('homeStatus').classList.toggle('warn',!active);$('homeHeadline').textContent=active?'关键信息落地后，再评估入场。':'先更新证据，再使用入场结论。';$('homeView').textContent=active?'SK hynix新结果已记录；仍需核对议息、云厂商财报与通胀。10月30日早上是集体复核窗口，不是预测的底部日期。':'历史图和情景计算仍可使用。旧入场判断已过期或事件结果尚未记录，请先核对新事实。';$('reviewDate').textContent='历史完整收盘截至 '+DATA.price_cutoff+' · 最近经营更新：SK hynix 10/28；其他来源各有日期。';const notes={QQQM:'关注云增长能否转成每股现金回报。',SMH:'关注AI订单兑现与行业集中风险。',SOXX:'区分AI需求与工业、汽车等周期。',DRAM:'关注存储正常化利润与新增产能。'};$('homeFunds').innerHTML=['QQQM','SMH','SOXX','DRAM'].map(s=>{const a=M.states(rowsFor(s)).at(-1);return `<a class="fund" href="history.html?symbol=${s}"><strong>${s}</strong><span class="value">回撤 ${pct(a.dd)}</span><p>${notes[s]}</p></a>`}).join('')}
}
renderHome();setInterval(renderHome,60000);
let chart={symbol:'QQQM',range:'3',mode:'price',horizon:126},shown=[],allStates=[];
function svgPlot(svg,lines,{percent=false,labels=[],baseline=null}={}){const values=lines.flatMap(l=>l.points.map(p=>p.y)).filter(Number.isFinite);if(!values.length){svg.innerHTML='<text x="60" y="120">数据不足</text>';return}let lo=Math.min(...values),hi=Math.max(...values);if(baseline!==null){lo=Math.min(lo,baseline);hi=Math.max(hi,baseline)}const pad=(hi-lo||Math.abs(hi)*.05||1)*.12;lo-=pad;hi+=pad;const width=Math.max(300,svg.clientWidth||1000),plotWidth=width-82;svg.setAttribute('viewBox','0 0 '+width+' 300');const X=f=>62+plotWidth*f,Y=y=>254-222*(y-lo)/(hi-lo);let markup='';for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4,y=Y(v);markup+=`<line x1="62" x2="${width-20}" y1="${y}" y2="${y}" stroke="#e7ece6"/><text x="49" y="${y+4}" text-anchor="end">${percent?pct(v):fmt(v,Math.abs(v)<20?2:0)}</text>`}if(baseline!==null)markup+=`<line x1="62" x2="${width-20}" y1="${Y(baseline)}" y2="${Y(baseline)}" stroke="#adc4b0" stroke-dasharray="4 4"/>`;lines.forEach((l,i)=>{const p=l.points.filter(p=>Number.isFinite(p.y));const points=p.map(p=>X(p.x).toFixed(2)+','+Y(p.y).toFixed(2)).join(' ');if(i===0&&p.length)markup+=`<polygon points="${X(p[0].x)},254 ${points} ${X(p.at(-1).x)},254" fill="#edf4ed" opacity=".8"/>`;markup+=`<polyline fill="none" stroke="${l.color}" stroke-width="2.2" points="${points}"/>`});labels.forEach(([x,label])=>markup+=`<text x="${X(x)}" y="283" text-anchor="${x===0?'start':x===1?'end':'middle'}">${esc(label)}</text>`);markup+='<line id="chartCross" x1="0" x2="0" y1="20" y2="254" stroke="#7e9f8d" stroke-dasharray="3 3" visibility="hidden"/>';svg.innerHTML=markup}
function renderChart(){if(!$('historyChart'))return;const rows=rowsFor(chart.symbol);allStates=M.states(rows);const end=new Date(rows.at(-1)[0]+'T00:00:00Z'),start=new Date(end);if(chart.range!=='all')start.setUTCFullYear(end.getUTCFullYear()-Number(chart.range));shown=allStates.filter(s=>chart.range==='all'||s.date>=start.toISOString().slice(0,10));if(!shown.length)shown=allStates.slice(-1);const pts=shown.map((s,i)=>({x:i/(shown.length-1||1),y:chart.mode==='dd'?s.dd:s.close}));const lines=[{points:pts,color:'#206f5d'}];if(chart.mode==='price')lines.push({points:shown.map((s,i)=>({x:i/(shown.length-1||1),y:s.ma200})).filter(p=>p.y!==null),color:'#91aab6'});svgPlot($('historyChart'),lines,{percent:chart.mode==='dd',baseline:chart.mode==='dd'?0:null,labels:[[0,shown[0].date],[1,shown.at(-1).date]]});const a=allStates.at(-1);$('lastPrice').textContent='$'+fmt(a.close);$('lastDate').textContent=a.date;$('lastDD').textContent=pct(a.dd);$('lastMA').textContent=a.ma200===null?'—':'$'+fmt(a.ma200);$('lastReturn').textContent=rows.length>252?pct(a.close/rows[rows.length-253][1]-1):'—';const localTag=local[chart.symbol]?' · 含未独立核实的本地更新':'';$('chartDate').textContent=`${chart.symbol} · ${allStates[0].date}—${a.date}${localTag} · ${chart.mode==='price'?'细蓝线：200日均价':'峰值取完整可用历史，非仅可见区间'}`;if($('riskRows'))renderRisk();if($('importStatus')){const l=local[chart.symbol];$('importStatus').textContent=l?`本浏览器保留${l.rows.length}行更新，最后导入于${l.imported_at}。原始数据仍可恢复。`:'该标的尚未导入手动数据。';$('dataHash').textContent='算法 '+M.VERSION+'；原始SHA256 '+DATA.manifest.find(m=>m.symbol===chart.symbol).raw_sha256.slice(0,20)+'…';if(savedRowWarnings[chart.symbol]||savedRowWarnings.all){$('importStatus').classList.add('error');$('importStatus').textContent+=' 原缓存未通过当前规则，未用于计算：'+(savedRowWarnings[chart.symbol]??savedRowWarnings.all)}if(l&&l.base_hash!==DATA.manifest.find(m=>m.symbol===chart.symbol).raw_sha256)$('importStatus').textContent+=' 本地更新基于旧版来源，请核对与当前原始快照的差异。'}}
function renderRisk(){const r=M.distributionV6(rowsFor(chart.symbol),chart.horizon);window.lastHistoricalDistribution=r;$('riskScope').textContent=`当前桶 ${r.bin}；成熟日度观察 ${r.n}，未成熟 ${r.censored}，不重叠窗口 ${r.nonoverlap}，支持事件 ${r.episode_count}（已恢复 ${r.recovered_episode_count}、未恢复 ${r.open_episode_count}）；事件外成熟观察 ${r.outside_episode_observations}。这些都不等于独立危机数。`;$('riskRows').innerHTML=[['窗口内进一步下跌',r.downside],['窗口末价格收益',r.returns]].map(([name,vals])=>`<tr><td>${name}</td>${vals.map(v=>`<td class="num">${pct(v)}</td>`).join('')}</tr>`).join('');if($('censoredRows'))$('censoredRows').innerHTML=r.incomplete_recent.map(v=>`<tr><td>${v.date}</td><td>${v.observed_sessions}</td><td>${v.observed_loss_lower_bound===null?'尚无后续观察':pct(v.observed_loss_lower_bound)}</td></tr>`).join('');}

if($('chartAsset')){options($('chartAsset'));const query=new URLSearchParams(location.search).get('symbol');if(known.includes(query))chart.symbol=query;$('chartAsset').value=chart.symbol;$('chartAsset').onchange=e=>{chart.symbol=e.target.value;renderChart()};$('chartRange').onchange=e=>{chart.range=e.target.value;renderChart()};document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{chart.mode=b.dataset.mode;document.querySelectorAll('[data-mode]').forEach(x=>x.classList.toggle('active',x===b));renderChart()});if($('riskHorizon'))$('riskHorizon').onchange=e=>{chart.horizon=e.target.value==='3y'?'3y':Number(e.target.value);renderRisk()};const svg=$('historyChart');svg.onpointermove=e=>{const rect=svg.getBoundingClientRect(),f=Math.max(0,Math.min(1,(e.clientX-rect.left-62)/(rect.width-82))),i=Math.round(f*(shown.length-1)),s=shown[i];const tip=$('historyTip');tip.style.display='block';tip.style.left=Math.min(Math.max(10,e.clientX-rect.left+12),rect.width-170)+'px';tip.innerHTML=`${s.date}<br>${chart.symbol} $${fmt(s.close)}<br>回撤 ${pct(s.dd)}`;const line=svg.querySelector('#chartCross');line.setAttribute('x1',62+(rect.width-82)*i/(shown.length-1||1));line.setAttribute('x2',62+(rect.width-82)*i/(shown.length-1||1));line.setAttribute('visibility','visible')};svg.onpointerleave=()=>{$('historyTip').style.display='none';svg.querySelector('#chartCross')?.setAttribute('visibility','hidden')};renderChart()}
if($('priceFile')){$('priceFile').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>8e6)throw Error('文件太大，请限制在8MB以内');const text=await file.text();let symbol=chart.symbol,rows;if(file.name.toLowerCase().endsWith('.json')){const x=JSON.parse(text);if(Array.isArray(x))rows=x;else if(x.series){symbol=x.params?.symbol??x.symbol??symbol;rows=x.series[symbol]}else{symbol=x.symbol??symbol;rows=x.rows}}else{const lines=text.replace(/^\uFEFF/,'').trim().split(/\r?\n/),header=lines.shift().split(',').map(s=>s.trim().toLowerCase()),di=header.indexOf('date'),pi=header.indexOf('close')>=0?header.indexOf('close'):header.indexOf('price');if(di<0||pi<0)throw Error('CSV需要date,close列');rows=lines.filter(s=>s.trim()).map(s=>{const z=s.split(',');return [z[di]?.trim(),z[pi]?.trim()]})}rows=M.validateRows(rows,symbol,known);const existing=rowsFor(symbol),dates=new Set(existing.map(r=>r[0])),added=rows.filter(r=>!dates.has(r[0])).length,map=new Map((local[symbol]?.rows??[]).map(r=>[r[0],r[1]]));rows.forEach(r=>map.set(r[0],r[1]));local[symbol]={rows:[...map].sort((a,b)=>a[0].localeCompare(b[0])),base_hash:DATA.manifest.find(m=>m.symbol===symbol).raw_sha256,imported_at:new Date().toISOString()};delete savedRowWarnings[symbol];const persisted=save();chart.symbol=symbol;$('chartAsset').value=symbol;renderChart();$('importStatus').textContent=`已处理${rows.length}行：新增${added}行，更正/覆盖${rows.length-added}行。图与历史分布已重算。${persisted?'已保存到本浏览器。':'本浏览器存储不可用，请导出保存。'} 这些输入未独立核实。`;$('importStatus').classList.remove('error')}catch(err){$('importStatus').classList.add('error');$('importStatus').textContent='未导入：'+err.message}};$('resetHistory').onclick=()=>{delete local[chart.symbol];delete savedRowWarnings[chart.symbol];save();renderChart()};$('exportHistory').onclick=()=>{const rows=rowsFor(chart.symbol);download(chart.symbol+'_历史快照.json',{schema:DATA.schema,algorithm_version:M.VERSION,exported_at:new Date().toISOString(),distribution_algorithm_version:M.HISTORY_VIEW_VERSION,params:chart,series:{[chart.symbol]:rows},result:M.distributionV6(rows,chart.horizon),source_manifest:DATA.manifest.find(m=>m.symbol===chart.symbol),input_status:local[chart.symbol]?'contains_unverified_browser_updates':'saved_provider_snapshot'})}}
const fields=[['budget','资金SGD',3000],['reference','估值锚USD（固定）',0],['entry','拟买价USD',0],['years','持有年数',3],['g1','首年每股盈利变化%',null],['growth','此后每年盈利变化%',null],['multiple','终值/基准倍数',null],['hurdle','目标年化%',null],['fx0','起始：1 USD = … SGD',DATA.fx_reference],['fx1','退出：1 USD = … SGD',DATA.fx_reference],['bps','每边交易摩擦bp',5],['fee','每笔费用USD',1],['fx_bps','每次换汇摩擦bp',10],['cash_rate','现金有效年利率%',0],['shock','前1/3期压力跌幅%',-30],['fund_fee','基金年费率%',0],['dividend','每股每年现金分红USD',0],['base_eps','基准EPS：USD/同一基金份额',null],['withholding','分红预扣率%（未知留空）',null]];
const META_FIELDS=['valuation_date','base_start','base_end','terminal_start','terminal_end','source_note'];
let scenarioAsset='QQQM',scenarioLast=null;const presets={neutral:[0,0,1],stress:[-25,5,.75],middle:[10,10,.9],strong:[20,15,1.1],memory:[-30,0,1]};
const SCENARIO_SCHEMA='etf.scenario.v3',SCENARIO_KEY='etf_research_scenarios_v7',PERCENT_FIELDS=['g1','growth','hurdle','cash_rate','shock','fund_fee','withholding'];
let scenarioRecords={},scenarioSelected='QQQM',scenarioSource=null,scenarioStorageFailed=false,scenarioLoadWarning='';
function fundFee(symbol){return DATA.fund_costs?.funds?.[symbol]?.expense_ratio??null}
function sourceBasis(symbol){const original=DATA.series[symbol].at(-1),manifest=DATA.manifest.find(x=>x.symbol===symbol),ref=DATA.expectations?.reference_inputs_by_symbol?.[symbol];return {anchor_date:original[0],anchor_price:original[1],price_source_sha256:manifest?.raw_sha256??null,data_built_at:DATA.built_at,expectation_version:DATA.expectations?.version??null,expectation_label:ref?.label??'原演示假设（尚未提供有来源参考值）',expectation_asof:ref?.asof??null,expectation_source_ids:Array.isArray(ref?.source_ids)?ref.source_ids:[],reference_parameters:{g1:ref?.g1??.1,growth:ref?.growth??.1,multiple:ref?.multiple??.9},origin:'analyst_sensitivity_unverified',valuation_basis:'unverified',fee_source:DATA.fund_costs?.funds?.[symbol]??null,entry_mode:'latest_close',entry_date:rowsFor(symbol).at(-1)[0]}}
function referenceInputs(symbol){const original=DATA.series[symbol].at(-1),current=rowsFor(symbol).at(-1),x=Object.fromEntries(fields.map(([id,,value])=>[id,value]));PERCENT_FIELDS.forEach(k=>{if(x[k]!==null)x[k]/=100});x.fund_fee=fundFee(symbol);x.fee_mode='deduct';x.valuation_basis='unverified';x.fx0=Number(x.fx0.toFixed(6));x.fx1=Number(x.fx1.toFixed(6));x.reference=Number(original[1].toFixed(4));x.entry=Number(current[1].toFixed(4));for(const k of ['g1','growth','multiple','hurdle','base_eps'])x[k]=null;for(const k of META_FIELDS)x[k]='';return x}
function validateScenarioRecord(input,{allowLegacy=false}={}){
 if(!input||typeof input!=='object'||Array.isArray(input))throw Error('情景文件必须为JSON对象');
 const old=input.schema==='etf.scenario.v1'||(allowLegacy&&!input.schema&&input.type==='manual_scenario_not_forecast');
 if(input.schema!==SCENARIO_SCHEMA&&!old)throw Error('不支持的情景文件版本');
 if(input.algorithm_version!==M.VERSION||(!old&&input.scenario_algorithm_version!==M.SCENARIO_VERSION))throw Error('情景算法版本不匹配');
 if(!known.includes(input.symbol))throw Error('不支持的情景标的');
 const raw=input.inputs;if(!raw||typeof raw!=='object'||Array.isArray(raw))throw Error('情景缺少inputs对象');
 const keys=fields.map(([id])=>id),oldKeys=keys.filter(k=>!['fund_fee','dividend','withholding'].includes(k)),allowed=old?oldKeys:[...keys,...META_FIELDS,'fee_mode','valuation_basis'];
 if(Object.keys(raw).some(k=>!allowed.includes(k))||(old?oldKeys:keys).some(k=>!(k==='withholding'&&raw[k]===null)&&(typeof raw[k]!=='number'||!Number.isFinite(raw[k]))))throw Error('情景输入字段缺失、未知或不是有限数字');
 const x={...Object.fromEntries(keys.map(k=>[k,raw[k]])),fee_mode:raw.fee_mode??'deduct',valuation_basis:raw.valuation_basis??'unverified',...Object.fromEntries(META_FIELDS.map(k=>[k,raw[k]]))};
 if(old){x.fund_fee=fundFee(input.symbol);x.dividend=0;x.withholding=null;scenarioLoadWarning='V5情景已迁移：新增基金费率；分红仍未纳入，旧结果已重新计算。'}
 if(!['unverified','ttm','ntm','normalized'].includes(x.valuation_basis))throw Error('盈利基准定义无效');
 M.scenarioV6(x);const basis=input.source_basis;if(basis!=null&&(typeof basis!=='object'||Array.isArray(basis)))throw Error('source_basis必须是对象');
 if(basis?.anchor_date&&!M.validDate(basis.anchor_date))throw Error('估值锚参考日期无效');if(basis?.price_source_sha256&&!/^[a-f0-9]{64}$/i.test(basis.price_source_sha256))throw Error('来源哈希格式无效');
 return {schema:SCENARIO_SCHEMA,algorithm_version:M.VERSION,scenario_algorithm_version:M.SCENARIO_VERSION,symbol:input.symbol,inputs:x,source_basis:basis?JSON.parse(JSON.stringify(basis)):sourceBasis(input.symbol),saved_at:typeof input.saved_at==='string'?input.saved_at:null};
}
try{const store=JSON.parse(localStorage.getItem(SCENARIO_KEY)||'null');if(store){if(store.schema!=='etf.scenario_store.v1'||!store.records||typeof store.records!=='object')throw Error('情景缓存版本不匹配');for(const [symbol,record]of Object.entries(store.records)){try{const valid=validateScenarioRecord(record);if(valid.symbol!==symbol)throw Error('标的键不匹配');scenarioRecords[symbol]=valid}catch{scenarioLoadWarning='部分旧情景未通过校验，未载入；可从导出文件恢复。'}}if(known.includes(store.selected_symbol))scenarioSelected=store.selected_symbol}}catch{scenarioLoadWarning='情景存储不可读，未载入旧值；请导入已导出的情景。'}
function readScenario(){const x=Object.fromEntries(fields.map(([id])=>[id,$('s_'+id).value.trim()===''?(id==='withholding'?null:NaN):Number($('s_'+id).value)]));for(const k of PERCENT_FIELDS)if(x[k]!==null)x[k]/=100;x.fee_mode=$('feeTreatment').value;x.valuation_basis=$('earningsBasis').value;for(const k of META_FIELDS)x[k]=$('s_'+k).value.trim();return x}
function putScenario(x){META_FIELDS.forEach(k=>$('s_'+k).value=x[k]??'');fields.forEach(([id])=>$('s_'+id).value=x[id]==null?'':PERCENT_FIELDS.includes(id)?x[id]*100:x[id]);$('feeTreatment').value=x.fee_mode??'deduct';$('earningsBasis').value=x.valuation_basis??'unverified'}
function scenarioStatus(message=''){const node=$('scenarioSaveStatus');if(!node)return;const basis=scenarioSource??sourceBasis(scenarioAsset),current=DATA.manifest.find(x=>x.symbol===scenarioAsset)?.raw_sha256,old=basis.price_source_sha256&&current!==basis.price_source_sha256,oldForecast=basis.expectation_version!==DATA.expectations?.version;node.classList.toggle('good',!scenarioStorageFailed);node.classList.toggle('error',scenarioStorageFailed);node.textContent=[message||'有效情景已按标的保存在本浏览器。',scenarioStorageFailed?'浏览器保存失败；请导出JSON备份。':'',old?'官方价格快照已更新，保留原估值锚与假设。':'',oldForecast?'盈利参考已更新；保留你的旧情景，点击恢复参考值可采用本轮参数。':'',scenarioLoadWarning].filter(Boolean).join(' ');if($('scenarioReferenceSummary'))$('scenarioReferenceSummary').textContent='完整基金三年盈利未核实。增长、倍数和EPS默认留空；局部持仓观测见研究页。旧版情景保留在原浏览器存储键，V7不自动激活。'}
function updateScenarioBasis(x){const basis=scenarioSource??sourceBasis(scenarioAsset);const manual=Math.abs(x.reference-(basis.anchor_price??x.reference))>1e-4;const current=rowsFor(scenarioAsset).at(-1);$('scenarioBasis').textContent=`估值锚 $${fmt(x.reference)}（${manual?'手动/导入值；':'固定参考；'}参考日期${basis.anchor_date??'未知'}）；所选历史最后收盘${current[0]} $${fmt(current[1])}${local[scenarioAsset]?'，含本地输入':''}。${'V7手填条件，未独立核实'}。拟买价${basis.entry_mode==='latest_close'?'跟随最新历史收盘':'为保留的手动计划价'}；估值锚不自动移动。`;const posture=$('scenarioInputPosture');if(posture){const ref=DATA.expectations?.reference_inputs_by_symbol?.[scenarioAsset],changed=ref&&['g1','growth','multiple'].some(k=>typeof ref[k]==='number'&&Math.abs(x[k]-ref[k])>1e-12);posture.textContent=basis.origin==='imported_unverified'?'导入情景；来源元数据待核实':!ref?'该标的暂无参考值，当前为演示假设':changed?'含手动调整；来源参考另列':'分析情景，盈利基准尚未验证'}}
function persistScenario(x){const record={schema:SCENARIO_SCHEMA,algorithm_version:M.VERSION,scenario_algorithm_version:M.SCENARIO_VERSION,symbol:scenarioAsset,inputs:{...x},source_basis:JSON.parse(JSON.stringify(scenarioSource??sourceBasis(scenarioAsset))),saved_at:new Date().toISOString()};record.source_basis.anchor_kind=Math.abs(x.reference-(record.source_basis.anchor_price??x.reference))>1e-4?'manual_override':'fixed_source_reference';const ref=record.source_basis.reference_parameters??{};record.parameter_posture=Object.fromEntries(['g1','growth','multiple'].map(k=>[k,record.source_basis.origin==='imported_unverified'?'imported_unverified':typeof ref[k]==='number'&&Math.abs(x[k]-ref[k])<1e-12?'reference_value':'manual_override']));const old=scenarioRecords[scenarioAsset];if(old&&JSON.stringify(old.inputs)===JSON.stringify(record.inputs)&&JSON.stringify(old.source_basis)===JSON.stringify(record.source_basis))record.saved_at=old.saved_at;scenarioRecords[scenarioAsset]=record;try{localStorage.setItem(SCENARIO_KEY,JSON.stringify({schema:'etf.scenario_store.v1',selected_symbol:scenarioAsset,records:scenarioRecords}));scenarioStorageFailed=false}catch{scenarioStorageFailed=true}return record}
function calcScenario(settings={}){if(settings.target?.id==='s_entry'&&scenarioSource)scenarioSource.entry_mode='manual';try{const x=readScenario(),r=M.scenarioV6(x);scenarioLast={symbol:scenarioAsset,inputs:x,result:r};window.lastScenarioSite=scenarioLast;$('scenarioError').classList.add('hidden');$('scenarioMax').textContent=r.maxEntry===null?'未建股票仓位':'US$'+fmt(r.maxEntry);$('scenarioGap').textContent=`相对参考价 ${r.maxEntry===null?'不可计算':pct(r.maxEntry/x.reference-1)}。这是给定情景的算术门槛，不产生买卖信号。`;renderV6Scenario(x,r);$('scenarioTarget').textContent='US$'+fmt(r.target);svgPlot($('scenarioChart'),[{points:r.integer.path.map(p=>({x:p.year/x.years,y:p.wealth_sgd})),color:'#206f5d'},{points:r.fractional.path.map(p=>({x:p.year/x.years,y:p.wealth_sgd})),color:'#5a7f9f'}],{labels:[[0,'现在'],[1,x.years+'年后']],baseline:x.budget});$('scenarioResults').innerHTML=[['整股',r.integer],['碎股',r.fractional]].map(([label,v])=>`<tr><td>${label}</td><td class="num">${fmt(v.units,3)}</td><td class="num">${fmt(v.cash_usd)}</td><td class="num">${money(v.terminal_sgd)}</td><td class="num">${pct(v.annualized)}</td><td class="num">手工路径，非风险估计</td></tr>`).join('');updateScenarioBasis(x);if(settings.persist!==false)persistScenario(x);scenarioStatus(settings.message??'')}catch(e){scenarioLast=null;window.lastScenarioSite=null;$('scenarioError').classList.remove('hidden');$('scenarioError').textContent=e.message;$('scenarioMax').textContent='—';$('scenarioGap').textContent='缺少已声明的盈利/期间假设，未生成条件买价。';if($('sensitivityRows'))$('sensitivityRows').innerHTML='';if($('sensitivityHead'))$('sensitivityHead').innerHTML='';$('scenarioTarget').textContent='—';$('scenarioResults').innerHTML='';$('scenarioChart').innerHTML='';if($('reverseStress'))$('reverseStress').textContent='参数未就绪，未计算反向门槛。';scenarioStatus('当前输入无效，未覆盖上次保存的有效情景。')}}
function scenarioSymbol(){scenarioAsset=$('scenarioAsset').value;const saved=scenarioRecords[scenarioAsset];if(saved){scenarioSource=JSON.parse(JSON.stringify(saved.source_basis));const x={...saved.inputs};if(scenarioSource.entry_mode==='latest_close'){const latest=rowsFor(scenarioAsset).at(-1);x.entry=Number(latest[1].toFixed(4));scenarioSource.entry_date=latest[0]}putScenario(x);calcScenario({message:scenarioSource.entry_mode==='latest_close'?'已恢复情景；拟买价跟随最新历史收盘，估值锚与假设保留。':'已恢复该标的上次有效情景；保留手动拟买价、估值锚与假设。'})}else{scenarioSource=sourceBasis(scenarioAsset);putScenario(referenceInputs(scenarioAsset));calcScenario({message:'已载入参考起点；有效修改会自动保存在本浏览器。'})}}
if($('scenarioInputs')){options($('scenarioAsset'));$('scenarioAsset').value=scenarioSelected;$('scenarioInputs').innerHTML=fields.map(([id,label,value])=>`<div class="field"><label for="s_${id}">${label}</label><input id="s_${id}" type="number" step="any" value="${value===null?'':Number(value.toFixed(6))}"></div>`).join('');$('scenarioInputs').insertAdjacentHTML('beforeend',META_FIELDS.map(k=>`<div class="field"><label for="s_${k}">${({valuation_date:'估值日',base_start:'基准盈利窗口开始',base_end:'基准盈利窗口末日（不含）',terminal_start:'退出盈利窗口开始',terminal_end:'退出盈利窗口末日（不含）',source_note:'EPS来源/假设与口径说明'})[k]}</label><input id="s_${k}" type="${k==='source_note'?'text':'date'}"></div>`).join(''));[...fields.map(([id])=>id),...META_FIELDS].forEach(id=>$('s_'+id).oninput=calcScenario);$('feeTreatment').onchange=calcScenario;$('earningsBasis').onchange=calcScenario;$('scenarioAsset').onchange=scenarioSymbol;document.querySelectorAll('[data-case]').forEach(b=>b.onclick=()=>{const a=presets[b.dataset.case];['g1','growth','multiple'].forEach((k,i)=>$('s_'+k).value=a[i]);calcScenario({message:'已应用演示压力情景，并自动保存；不是市场一致预期。'})});$('exportScenarioSite').onclick=()=>{if(!scenarioLast){scenarioStatus('请先修正无效输入，再导出。');return}const record=persistScenario(scenarioLast.inputs);download(scenarioAsset+'_情景.json',{...record,result:scenarioLast.result,exported_at:new Date().toISOString(),type:'manual_scenario_not_forecast'});scenarioStatus('已导出含输入、来源和算法版本的情景；可在另一设备导入并重新计算。')};$('resetScenarioReference').onclick=()=>{const x=readScenario(),reference=referenceInputs(scenarioAsset);for(const k of ['reference','g1','growth','multiple','hurdle','base_eps'])x[k]=reference[k];scenarioSource={...sourceBasis(scenarioAsset),entry_mode:scenarioSource?.entry_mode??'manual'};putScenario(x);calcScenario({message:'已主动恢复当前参考增长、倍数和估值锚；拟买价、资金、费用及FX等个人输入保留。'})};$('latestScenarioEntry').onclick=()=>{scenarioSource.entry_mode='latest_close';scenarioSource.entry_date=rowsFor(scenarioAsset).at(-1)[0];$('s_entry').value=Number(rowsFor(scenarioAsset).at(-1)[1].toFixed(4));calcScenario({message:'仅将拟买价更新为所选历史最后收盘，原估值锚与盈利假设保留。'})};$('importScenarioSite').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>2e6)throw Error('情景文件请限制在2MB以内');const record=validateScenarioRecord(JSON.parse(await file.text()),{allowLegacy:true});scenarioAsset=record.symbol;$('scenarioAsset').value=scenarioAsset;scenarioSource={...record.source_basis,origin:'imported_unverified',entry_mode:'manual'};putScenario(record.inputs);calcScenario({message:'已导入参数并重新计算。文件内结果未被采用，来源元数据未经独立核实。'})}catch(err){scenarioStatus('未导入：'+err.message+'；原有效情景保留。')}finally{e.target.value=''}};scenarioSymbol()}
window.ScenarioPersistence={schema:SCENARIO_SCHEMA,storage_key:SCENARIO_KEY,validateRecord:validateScenarioRecord,referenceInputs,sourceBasis};
if($('robustSite')){$('robustSite').innerHTML=DATA.robustness.filter(r=>r.scope==='current_bin_only').map(r=>`<tr><td>${r.symbol}</td><td class="num">${money(r.min_mean_sgd)} 至 ${money(r.max_mean_sgd)}</td><td>${r.sign_changes_across_variants?'方向翻转，依赖样本选择':'本组未翻转，仍非稳定预测'}<br><small>每组${r.min_cohort_n}–${r.max_cohort_n}个起点</small></td></tr>`).join('');$('coverageSite').innerHTML=DATA.bridge.fund_scenarios.filter(r=>r.scenario_id==='unchanged').map(r=>`<tr><td>${r.fund}</td><td class="num">${pct(r.covered_weight)}</td><td>残差${pct(r.uncovered_weight)}，不默认为已验证的盈利或零回报</td></tr>`).join('');$('evidenceFreshness').textContent=`价格/历史主分析截至${DATA.price_cutoff}；SK hynix Q3于10/28单独更新，其他公司保留各自来源日期；网页构建时间${DATA.built_at}不代表所有事实已更新。`;$('sourceList').innerHTML=DATA.evidence.snapshot.sources.map(s=>`<p><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a><br>${esc(s.published??'见原页')} · 取回 ${esc(s.retrieved_at??'见原记录')}</p>`).join('');$('manifestList').innerHTML=DATA.manifest.map(s=>`<p><b>${s.symbol}</b> · ${s.start}—${s.end} · ${s.rows}行<br><span style="word-break:break-all">SHA256 ${s.raw_sha256}</span></p>`).join('')}
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if($('historyChart'))renderChart();if($('scenarioChart'))calcScenario()},100)});

function renderMonitor(){if(!$('monitorStatus'))return;const m=DATA.monitor;if(!m){$('monitorStatus').textContent='尚未配置持续任务。';return}const never=!m.last_success_at,stale=m.stale_after&&Date.parse(m.stale_after)<Date.now();$('monitorStatus').textContent=`每${m.cadence_minutes}分钟的本地任务已配置；电脑和桌面应用须保持运行。${never?'尚未完成首次成功市场内容扫描。':stale?'上次完整扫描已超过有效期。':'最近完整内容扫描：'+m.last_success_at} 最近内容检查：${m.last_market_check_at??'尚未执行'}（${m.runtime_status==='degraded'?'部分完成，存在来源缺口':m.runtime_status??'未知'}）。 最近访问探测：${m.last_source_probe_at??'未执行'}（可访问性检查不等于新闻核实）。`;$('monitorStatus').className=never||stale?'notice error':'notice good';$('monitorUpdates').innerHTML=(m.failed_sources?.length?'<p><b>本轮未能完整审阅的来源：</b>'+m.failed_sources.map(x=>esc(x.name)+' '+esc(x.http_status??x.error)).join('；')+'。其他浏览渠道可能仍可用，不能将失败解释为没有新消息。</p>':'')+(m.last_market_review_summary?'<details><summary>本次检查覆盖与限制</summary><p>'+esc(m.last_market_review_summary)+'</p></details>':'')+(m.confirmed_updates??[]).map(x=>`<p><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a><br>发布日期 ${esc(x.published_date)} · 记录于${esc(x.recorded_at)} · 已有审阅台账记录</p>`).join('')}
renderMonitor();setInterval(renderMonitor,60000);
if(location.protocol.startsWith('http'))setInterval(async()=>{try{const s=await fetch('status.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.json());if(s.built_at!==DATA.built_at&&!$('newVersion')){const p=document.createElement('p');p.id='newVersion';p.className='notice good';p.innerHTML='网站有新版本。<button class="button inline" id="reloadVersion">刷新查看</button>　导出的假设可保留；未导出内容请先保存。';document.querySelector('main .shell').prepend(p);$('reloadVersion').onclick=()=>location.reload()}}catch{}},60000);


function renderV6Scenario(x,r){

 $('valuationDefinition').textContent=`${x.valuation_basis.toUpperCase()}：估值日 ${x.valuation_date}；基准 ${x.base_start}—${x.base_end}；退出 ${x.terminal_start}—${x.terminal_end}（末日不含）。基准EPS ${fmt(r.base_eps)} USD/同一基金份额，M₀ ${fmt(r.base_pe)}，退出EPS ${fmt(r.terminal_eps)}，M_T ${fmt(r.terminal_pe)}。均为声明的条件输入，来源尚需独立核实。`;
 const a=r.reverse;$('reverseStress').textContent=a.status==='no_stock_exposure'?'未能建立股票仓位；请先检查资金与固定费用。':`在当前拟买价、费用与倍数假设下，要达到${pct(x.hurdle)}年化，需要净退出价US$${fmt(a.required_net_target)}；等效盈利年增${pct(a.required_uniform_growth)}，或在当前盈利路径下终值倍数比例${fmt(a.required_multiple,3)}。这是目标回报的反解，不是市场隐含预期。`;
 const fee=DATA.fund_costs?.funds?.[scenarioAsset],feeOverride=fee&&Math.abs(x.fund_fee-fee.expense_ratio)>1e-12;$('fundCostBasis').innerHTML=`基金年费率${fmt(x.fund_fee*100,2)+'%'}${feeOverride?'（手动覆盖；官方披露'+fmt(fee.expense_ratio*100,2)+'%'+'）':''}（${x.fee_mode==='deduct'?'从成分盈利毛情景补扣':'终值已包含，不重复扣'}）。${fee?'<a href="'+esc(fee.url)+'" target="_blank" rel="noopener">官方来源</a>':''} 费用可能变化，DRAM互换融资及交易成本未完整覆盖。${x.dividend===0?'当前分红未纳入，只显示资本价格回报情景。':'分红按每股固定USD、持有周年支付留美元现金；预扣率为用户假设，未核实个人税务身份。'}`;
 const gs=[-.10,0,.10,.20,.30],ms=[.5,.65,.8,1,1.2];$('sensitivityHead').innerHTML='<tr><th>后续盈利增速 / 终值倍数</th>'+ms.map(m=>'<th>'+fmt(m,2)+'×</th>').join('')+'</tr>';
 $('sensitivityRows').innerHTML=gs.map(g=>'<tr><th>'+pct(g)+'</th>'+ms.map(m=>{const v=M.scenarioV6({...x,growth:g,multiple:m}),ratio=v.maxEntry===null?null:v.maxEntry/x.entry;return '<td class="num">'+(ratio===null?'—':fmt(ratio,2)+'×')+'</td>'}).join('')+'</tr>').join('');
}

// V5 EXPECTATION VIEWS
function renderReferenceSummary(symbol){const el=$('scenarioReferenceSummary'),r=DATA.expectations?.reference_inputs_by_symbol?.[symbol];if(!el)return;if(!r){el.innerHTML='<p class="tiny">该标的暂无有来源参考值；输入仅为演示假设。</p>';return}el.innerHTML=`<details><summary>原V5敏感性参数：首年盈利 ${pct(r.g1)}，后续 ${pct(r.growth)} / 年 · 查看理由与证据</summary><p class="note">${esc(r.rationale)}</p><p class="tiny">${esc(r.period_caveat)} ${esc(r.valuation_rationale)}</p><p class="tiny">分析敏感性：首年 ${(r.first_year_range??[]).map(v=>pct(v)).join(' 至 ')}；后续 ${(r.later_year_range??[]).map(v=>pct(v)).join(' 至 ')}。这些不是置信区间。参考取回截止 ${esc(r.asof)}；行情仍以价格快照日期为准。</p><a href="research.html#expectations">查看28家公司原始预测、营收与口径限制 →</a></details>`}
function expectationViews(){const x=DATA.expectations;if(!x)return;const d=x.source_data;if($('expectationDate'))$('expectationDate').textContent=`本轮取回${d.companies.length}家公司预测；截止${d.information_cutoff}。Nasdaq预测asOf为空，取回日期不能证明每笔估计何时更新。公司EPS调整口径未完全勾稽，所有聚合均为暂定分析参考。`;
if($('referenceRows'))$('referenceRows').innerHTML=Object.entries(x.reference_inputs_by_symbol).map(([symbol,r])=>`<tr><td><b>${symbol}</b></td><td class="num">${pct(r.g1)}</td><td class="num">${pct(r.growth)}</td><td>${esc(r.rationale)}<br><b>保留作原V5敏感性，非已验证基准。</b></td></tr>`).join('');
if($('revenueRows'))$('revenueRows').innerHTML=['MSFT','AMZN','GOOGL','META','NVDA','TSM','MU'].map(symbol=>{const c=d.companies.find(c=>c.symbol===symbol),r=c?.revenue_reference,p=x.company_inputs_by_symbol[symbol];return `<tr><td><b>${symbol}</b></td><td>${r?esc(r.quarters.map(q=>q.forecast_period).join(' / ')):'未验证'}</td><td class="num">${r?pct(r.aggregate_matched_yoy_growth):'未验证'}</td><td class="num">${pct(p.revenue_growth)} / ${pct(p.later_revenue_growth)}</td><td>${esc(p.rationale)}</td></tr>`}).join('');
if($('consensusRows'))$('consensusRows').innerHTML=d.companies.map(c=>`<tr><td><a href="${esc(c.public_page_url)}" target="_blank" rel="noopener">${esc(c.symbol)}</a></td><td>${c.annual_forecasts.slice(0,3).map(a=>`${esc(a.period)}: ${fmt(a.eps_mean)} (${fmt(a.estimate_count,0)}份)`).join('<br>')}</td><td>${c.annual_forecasts.slice(1,3).map(a=>pct(a.growth_from_previous_forecast_fy)).join(' / ')}</td><td>${['GOOGL','AMZN'].includes(c.symbol)?'<b>一次性收益/口径疑点，已排除聚合</b>':'预测EPS*口径未完全核实'}<br>取回 ${esc(c.retrieved_at)}；源asOf未提供</td></tr>`).join('');
if($('guidanceRows'))$('guidanceRows').innerHTML=(d.annual_revenue_primary_anchors??[]).map(g=>`<p><a href="${esc(g.source)}" target="_blank" rel="noopener">${esc(g.symbol)} 管理层年度展望</a> · ${esc(g.period)}：${g.revenue_yoy_growth!=null?pct(g.revenue_yoy_growth):esc(g.management_text)}。<span class="tiny">${esc(g.note)}</span></p>`).join('')+(x.extra_sources??[]).map(g=>`<p><a href="${esc(g.url)}" target="_blank" rel="noopener">${esc(g.title)}</a>；单一机构预测。</p>`).join('');
}
expectationViews();
window.ResearchApp={rowsFor,renderChart,renderRisk,chart,DATA,localUpdates:()=>local};
})();

```


## reproduce.py
SHA256: 389f292bbedb6a5699e6cd87f15de35a2c9348a0b8e3c9011787e6a402b28c60

```python
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

```


## v7_episodes.py
SHA256: 6028f62e15cb3f9834aaaa97206b65e91835bbef7368da409bee344a52fdb467

```python
"""V7 retrospective drawdown-episode labels; frozen price distributions unchanged.

Every strict fall below the running peak may define an episode. Its interval is
[latest_peak_anchor, first_recovery), so the recovery observation is never owned
by the preceding episode. Peak anchors are back-labelled after a drawdown occurs;
these are descriptive statistical labels, never information for a live signal.
"""
from pathlib import Path
from datetime import datetime,timezone
import json,math
import numpy as np
import pandas as pd
from v6_history import SYMBOLS,LABELS,load_close,bucket,endpoints,greedy_nonoverlap

ROOT=Path(__file__).resolve().parent


def _date(dates,i):
    return str(pd.Timestamp(dates[i]).date())if dates is not None else None


def label_episodes(prices,dates=None):
    """Return one episode ID per observation, or -1 if outside all episodes.

    Equal peak observations update the anchor to the latest such observation.
    An anchor is assigned only after a subsequent strict drawdown actually occurs.
    An open episode has null recovery fields; observed_stop_exclusive is merely
    the boundary of data currently available, not a predicted recovery.
    """
    p=[float(x)for x in prices]
    if not p or any(not math.isfinite(x)or x<=0 for x in p):raise ValueError('Positive finite prices required')
    if dates is not None and len(dates)!=len(p):raise ValueError('Date/price length mismatch')
    n=len(p);owners=[-1]*n;eps=[];peak=p[0];anchor=0;active=None
    for i,value in enumerate(p):
        if active is None:
            if value>=peak:
                peak=value;anchor=i
                continue
            active=len(eps)
            eps.append({'id':active,'peak_anchor_index':anchor,'peak_anchor_date':_date(dates,anchor),
                'peak_price':peak,'first_drawdown_index':i,'first_drawdown_date':_date(dates,i),
                'recovery_index':None,'recovery_date':None,'observed_stop_exclusive':n,'status':'open'})
            for j in range(anchor,i+1):
                if owners[j]!=-1:raise AssertionError('Episode intervals must not overlap')
                owners[j]=active
        elif value>=peak:
            eps[active].update(recovery_index=i,recovery_date=_date(dates,i),observed_stop_exclusive=i,status='recovered')
            # i remains outside the old interval. A later strict fall may make i
            # the next episode's anchor; a later equal/higher peak supersedes it.
            active=None;peak=value;anchor=i
        else:
            owners[i]=active
    return {'assignments':owners,'episodes':eps,
        'episode_count':len(eps),'recovered_episode_count':sum(e['status']=='recovered'for e in eps),
        'open_episode_count':sum(e['status']=='open'for e in eps),
        'outside_episode_observations':sum(i<0 for i in owners)}


def support_counts(positions,assignments,episodes):
    ids=[int(i)for i in positions];owners=[assignments[i]for i in ids]
    support=sorted(set(e for e in owners if e>=0))
    recovered=[e for e in support if episodes[e]['recovery_index']is not None]
    opened=[e for e in support if episodes[e]['recovery_index']is None]
    outside=sum(e<0 for e in owners);inside=len(ids)-outside
    return {'episode_count':len(support),'recovered_episode_count':len(recovered),'open_episode_count':len(opened),
        'inside_episode_observations':inside,'outside_episode_observations':outside,
        'episode_ids':support,'recovered_episode_ids':recovered,'open_episode_ids':opened,
        'coverage_identity_holds':inside+outside==len(ids),
        'count_identity_holds':len(recovered)+len(opened)==len(support)}


def quantiles(values):
    x=np.asarray(values,dtype=float);x=x[np.isfinite(x)]
    if not len(x):return {'n':0,'p10':None,'median':None,'p90':None,'min':None,'max':None}
    return {'n':int(len(x)),'p10':float(np.quantile(x,.1)),'median':float(np.quantile(x,.5)),
        'p90':float(np.quantile(x,.9)),'min':float(x.min()),'max':float(x.max())}


def diagnose(symbol,config):
    close,source=load_close(symbol,config);prices=close.to_numpy();index=close.index;n=len(prices)
    source={**source,'basis':'saved_close_price_only_not_adjclose_no_cash_distributions',
        'corporate_action_note':'Vendor split/corporate-action treatment was not independently reverified; no claim that close is unadjusted for every corporate action.'}
    dd=prices/np.maximum.accumulate(prices)-1;bins=np.array([bucket(x)for x in dd]);current=int(bins[-1])
    labels=label_episodes(prices,index);out={'symbol':symbol,'source':source,
        'current':{'date':str(index[-1].date()),'close':float(prices[-1]),'drawdown':float(dd[-1]),'bin':LABELS[current],'running_peak':float(np.max(prices))},
        'all_history_episode_counts':{k:labels[k]for k in ['episode_count','recovered_episode_count','open_episode_count','outside_episode_observations']},
        'episodes':labels['episodes'],'horizons':[]}
    for h in [63,126,252,'3calendar']:
        ends=endpoints(index,h);ids=np.flatnonzero((ends<n)&(bins==current));nonoverlap=greedy_nonoverlap(ids,ends)
        returns=[float(prices[ends[i]]/prices[i]-1)for i in ids]
        minimum=[min(0.,float(prices[i+1:ends[i]+1].min()/prices[i]-1))for i in ids]
        counts=support_counts(ids,labels['assignments'],labels['episodes'])
        if not counts['coverage_identity_holds']or not counts['count_identity_holds']:raise AssertionError('Episode count coverage failed')
        out['horizons'].append({'horizon':h,'mature_n':len(ids),'nonoverlap_n':len(nonoverlap),
            'endpoint_rule':'First available session on or after third calendar anniversary'if h=='3calendar'else f'{h} subsequent available close observations',
            'first_mature_start':str(index[ids[0]].date())if len(ids)else None,
            'last_mature_start':str(index[ids[-1]].date())if len(ids)else None,
            **counts,'price_return_quantiles':quantiles(returns),
            'minimum_signed_return_quantiles':quantiles(minimum),
            'maximum_positive_loss_quantiles':quantiles([-x for x in minimum]),
            'episode_count_interpretation':'Distinct retrospective episodes containing at least one mature current-bin start; includes recovered and open episodes. Not an independent sample count.'})
    return out


def build(write=True):
    config=json.loads((ROOT/'v3_config.json').read_text(encoding='utf8'));series=[diagnose(s,config)for s in SYMBOLS]
    result={'schema':'v7.episodes_summary.v1','built_at':datetime.now(timezone.utc).isoformat(),'price_cutoff':config['asof'],
        'protocol':{'episode_definition':'Any strict drawdown from a running high; [latest equal-or-higher peak anchor, first recovery), half-open',
            'recovery_boundary':'Recovery observation is excluded from the preceding episode. It can become a later episode anchor only if a subsequent strict decline occurs.',
            'flat_peaks':'Each equal peak supersedes the anchor until a strict decline; earlier equal-peak observations are not forced into an episode.',
            'outside_coverage':'Every mature current-bin observation is counted either inside one episode or outside episodes; totals must equal mature_n.',
            'open_episodes':'Recovery index/date are null. observed_stop_exclusive only describes available observations, not an episode recovery.',
            'information_time':'Peak anchors are back-labelled after a later decline; episode boundaries are retrospective evaluation labels and must not enter historical signals.',
            'counts':'episode_count includes recovered and open supported episodes. Neither episodes nor nonoverlap windows are claimed IID independent samples.',
            'price_basis':'Own ETF saved close, not adjclose, for both current buckets and outcomes; frozen source hashes retained. No proxy splice, cash dividends, fees or FX. Vendor corporate-action treatment not independently reverified.',
            'unchanged_statistics':'Episode relabelling does not change mature starts, nonoverlap window count or forward price/loss quantiles from V6.',
            'main_output':'No conditional/unconditional mean difference, p-value, confidence interval or bottom probability is included.'},'series':series}
    if write:
        path=ROOT/'v7/episodes_summary.json';path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf8')
    return result


GOLDEN_CASES=[
    {'name':'shallow_recovered','prices':[100,99,100],'assignments':[0,0,-1],'anchors':[0],'recoveries':[2]},
    {'name':'unrecovered','prices':[100,99,98],'assignments':[0,0,0],'anchors':[0],'recoveries':[None]},
    {'name':'flat_peaks_latest_anchor','prices':[100,100,99,100,100,99],'assignments':[-1,0,0,-1,1,1],'anchors':[1,4],'recoveries':[3,None]},
    {'name':'continuous_ATH','prices':[100,101,102,103],'assignments':[-1,-1,-1,-1],'anchors':[],'recoveries':[]},
    {'name':'recovery_is_next_anchor','prices':[100,99,100,99,101],'assignments':[0,0,1,1,-1],'anchors':[0,2],'recoveries':[2,4]},
    {'name':'last_equal_high_only','prices':[100,101,101,100,101],'assignments':[-1,-1,0,0,-1],'anchors':[2],'recoveries':[4]},
]

if __name__=='__main__':
    r=build();print(json.dumps({'series':len(r['series']),'horizons':sum(len(s['horizons'])for s in r['series']),'price_cutoff':r['price_cutoff']}))

```


## v7_episodes_tests.py
SHA256: 403741c2a4514820e5891066ab7698ffecebec7e68acaef4cdc15efbf42a5062

```python
"""Boundary and coverage checks for V7 retrospective episode labels."""
from pathlib import Path
import json,unittest
from v7_episodes import ROOT,GOLDEN_CASES,label_episodes,support_counts,build

class EpisodeBoundaries(unittest.TestCase):
    def test_small_sequence_oracles(self):
        for case in GOLDEN_CASES:
            with self.subTest(case=case['name']):
                r=label_episodes(case['prices']);self.assertEqual(r['assignments'],case['assignments'])
                self.assertEqual([e['peak_anchor_index']for e in r['episodes']],case['anchors'])
                self.assertEqual([e['recovery_index']for e in r['episodes']],case['recoveries'])
    def test_any_strict_drawdown_not_five_percent(self):
        r=label_episodes([100,100-1e-10,100]);self.assertEqual(r['episode_count'],1)
        self.assertEqual(r['assignments'],[0,0,-1])
    def test_no_episode_for_flat_or_increasing_peaks(self):
        r=label_episodes([100,100,101,101,102]);self.assertEqual(r['episode_count'],0)
        self.assertEqual(r['outside_episode_observations'],5)
    def test_recovery_half_open_no_double_ownership(self):
        r=label_episodes([100,99,100,99,101]);first,second=r['episodes']
        self.assertEqual(first['recovery_index'],second['peak_anchor_index'])
        self.assertEqual(r['assignments'][2],second['id'])
        for e in r['episodes']:
            stop=e['recovery_index']if e['recovery_index']is not None else len(r['assignments'])
            self.assertTrue(all(r['assignments'][i]==e['id']for i in range(e['peak_anchor_index'],stop)))
    def test_open_recovery_fields_remain_null(self):
        e=label_episodes([100,99])['episodes'][0]
        self.assertIsNone(e['recovery_index']);self.assertIsNone(e['recovery_date'])
        self.assertEqual(e['observed_stop_exclusive'],2)
    def test_mature_positions_covered_inside_plus_outside(self):
        r=label_episodes([100,101,100,102]);counts=support_counts([0,1,2],r['assignments'],r['episodes'])
        self.assertEqual(counts['inside_episode_observations'],2);self.assertEqual(counts['outside_episode_observations'],1)
        self.assertEqual(counts['episode_count'],1);self.assertEqual(counts['recovered_episode_count'],1)
    def test_recovered_and_open_counts_distinct(self):
        r=label_episodes([100,99,100,99]);counts=support_counts([0,1,2,3],r['assignments'],r['episodes'])
        self.assertEqual(counts['episode_count'],2);self.assertEqual(counts['recovered_episode_count'],1)
        self.assertEqual(counts['open_episode_count'],1)


class FrozenIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=build(write=False)
        cls.v6=json.loads((ROOT/'v6/history_diagnostics.json').read_text(encoding='utf8'))
    def test_all_eight_assets_four_horizons(self):
        self.assertEqual(len(self.result['series']),8)
        self.assertEqual(sum(len(s['horizons'])for s in self.result['series']),32)
    def test_v6_mature_counts_and_quantiles_unchanged(self):
        for s in self.result['series']:
            old=next(o for o in self.v6['series']if o['symbol']==s['symbol'])
            self.assertEqual(s['current'],old['current'])
            for r in s['horizons']:
                a=next(o for o in old['horizons']if o['horizon']==r['horizon'])['conditional_current_bin']
                self.assertEqual(r['mature_n'],a['mature_observations']);self.assertEqual(r['nonoverlap_n'],a['greedy_nonoverlap_windows'])
                for newkey,oldkey in [('price_return_quantiles','window_price_return'),('minimum_signed_return_quantiles','window_minimum_signed_return'),('maximum_positive_loss_quantiles','window_maximum_positive_loss')]:
                    for k,v in r[newkey].items():self.assertEqual(v,a[oldkey][k])
    def test_every_current_bucket_mature_observation_accounted_for(self):
        for s in self.result['series']:
            for r in s['horizons']:
                self.assertEqual(r['inside_episode_observations']+r['outside_episode_observations'],r['mature_n'])
                self.assertEqual(r['recovered_episode_count']+r['open_episode_count'],r['episode_count'])
                self.assertTrue(r['coverage_identity_holds']);self.assertTrue(r['count_identity_holds'])
    def test_no_mean_difference_in_main_payload(self):
        for s in self.result['series']:
            for r in s['horizons']:
                self.assertFalse(any('mean' in k for k in r))
                self.assertFalse(any('mean' in k for k in r['price_return_quantiles']))

if __name__=='__main__':unittest.main(verbosity=2)

```


## v7_calendar_tilt.py
SHA256: 4f36ca73ddd702e39f256effd8368a9e7646176e3104ab1f913d4788893b6278

```python
"""Annual-EPS-mass-preserving shape sensitivity around V6 calendar proxies.

No network, no forecasting fit, no missing-year extrapolation and no writes on
import.  Inputs inherit V6's source, count, currency and accounting exclusions.
"""
from pathlib import Path
from datetime import date, datetime, timezone
import hashlib
import json
import math

ROOT = Path(__file__).resolve().parent
SHAPES = [('front_loaded', -.5), ('uniform', 0.), ('back_loaded', .5)]


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def linear_density(u, s):
    if not all(_finite(x) for x in [u, s]) or not 0 <= u <= 1 or not -1 <= s <= 1:
        raise ValueError('Density requires u in [0,1] and s in [-1,1]')
    return 1+s*(2*u-1)


def linear_mass(a, b, s):
    """Stable form of (b-a)+s*((b*b-b)-(a*a-a))."""
    if not all(_finite(x) for x in [a, b, s]) or not 0 <= a <= b <= 1 or not -1 <= s <= 1:
        raise ValueError('Mass interval requires 0<=a<=b<=1 and s in [-1,1]')
    return (b-a)*(1+s*(a+b-1))


def exponential_mass(a, b, k):
    """Integral of exp(k*u)/Z, preserving a whole year's EPS total."""
    if not all(_finite(x) for x in [a, b, k]) or not 0 <= a <= b <= 1:
        raise ValueError('Exponential mass interval invalid')
    if abs(k) < 1e-10:
        return b-a
    if k > 50:
        return math.exp(k*(b-1)) * (-math.expm1(-k*(b-a))) / (-math.expm1(-k))
    return math.exp(k*a)*math.expm1(k*(b-a))/math.expm1(k)


def bounds(component):
    start = date.fromisoformat(component['fiscal_start'])
    end = date.fromisoformat(component['fiscal_end_exclusive'])
    a = date.fromisoformat(component['overlap_start'])
    b = date.fromisoformat(component['overlap_end_exclusive'])
    days = (end-start).days
    if days != component['fiscal_days'] or not start <= a < b <= end:
        raise ValueError('V6 component interval/date denominator is inconsistent')
    return (a-start).days/days, (b-start).days/days


def annual_index(company):
    result = {}
    for window in company['windows']:
        for part in window['components']:
            key = part['fiscal_start']
            value = {k: part[k] for k in ['period', 'fiscal_start', 'fiscal_end_exclusive', 'fiscal_days', 'eps_mean', 'estimate_count']}
            if key in result and result[key] != value:
                raise ValueError('Same fiscal-year forecast differs across V6 windows')
            result[key] = value
    return result


def _blocking(window):
    reasons = []
    if not window['complete_calendar_coverage']:
        reasons.append('Missing FY/date coverage; shape sensitivity cannot fill missing EPS')
    if not window['analyst_count_screen_pass']:
        reasons.append('An annual component fails the inherited minimum-analyst-count rule')
    return reasons


def shape_window(window, index=None):
    reasons = _blocking(window)
    eligible = not reasons
    scenarios = []
    for shape, s in SHAPES:
        parts = []
        if eligible:
            for row in window['components']:
                a, b = bounds(row)
                mass = linear_mass(a, b, s)
                parts.append({'period': row['period'], 'a': a, 'b': b,
                              'annual_eps_unchanged': row['eps_mean'], 'annual_shape_mass': 1.,
                              'overlap_mass_fraction': mass,
                              'eps_contribution': row['eps_mean']*mass,
                              'estimate_count': row['estimate_count']})
        scenarios.append({'id': shape, 's': s,
                          'eps_proxy': sum(p['eps_contribution'] for p in parts) if eligible else None,
                          'components': parts})
    values = [s['eps_proxy'] for s in scenarios if s['eps_proxy'] is not None]
    uniform = next(s['eps_proxy'] for s in scenarios if s['id'] == 'uniform')
    if eligible and (window['eps_proxy'] is None or abs(uniform-window['eps_proxy']) > 1e-10):
        raise ValueError('s=0 does not reproduce the V6 uniform-window proxy')
    exp_parts, exp_blockers = [], list(reasons)
    if eligible:
        for row in window['components']:
            nxt = (index or {}).get(row['fiscal_end_exclusive'])
            if (nxt is None or not _finite(nxt['eps_mean']) or nxt['eps_mean'] <= 0
                    or row['eps_mean'] <= 0
                    or not _finite(nxt['estimate_count'])
                    or nxt['estimate_count'] < window['analyst_count_threshold']):
                exp_blockers.append(row['period']+': adjacent positive, count-qualified FY EPS unavailable')
                continue
            k = math.log(nxt['eps_mean']/row['eps_mean'])
            a, b = bounds(row)
            mass = exponential_mass(a, b, k)
            exp_parts.append({'period': row['period'], 'k': k, 'a': a, 'b': b,
                              'annual_eps_unchanged': row['eps_mean'],
                              'adjacent_period': nxt['period'], 'adjacent_eps': nxt['eps_mean'],
                              'overlap_mass_fraction': mass, 'eps_contribution': row['eps_mean']*mass})
    return {
        'label': window['label'], 'offset_years': window['offset_years'],
        'start': window['start'], 'end_exclusive': window['end_exclusive'],
        'window_days': window['window_days'],
        'source_v6_uniform_eps': window['eps_proxy'],
        'eligible_for_shape_diagnostics': eligible,
        'eligible_for_provisional_fund_aggregation': window['eligible_for_provisional_aggregate'],
        'blocking_reasons': reasons,
        'missing_annual_periods': window.get('missing_annual_periods', []),
        'sparse_or_unknown_annual_periods': window['sparse_or_unknown_annual_periods'],
        'linear_scenarios': scenarios,
        'eps_range': [min(values), max(values)] if values else None,
        'range_span_fraction_of_uniform': (max(values)-min(values))/abs(uniform) if values and uniform else None,
        'uniform_difference_from_v6': uniform-window['eps_proxy'] if eligible else None,
        'exponential_scenario': {
            'id': 'adjacent_annual_ratio_exponential',
            'status': 'provisional_shape_only' if not exp_blockers else 'blocked_no_complete_adjacent_year_path',
            'eps_proxy': sum(p['eps_contribution'] for p in exp_parts) if not exp_blockers else None,
            'components': exp_parts,
            'blocking_reasons': exp_blockers,
            'interpretation': 'Adjacent annual EPS ratio only selects an illustrative normalized within-year density; it is not a fitted or actual quarterly path',
        },
        'range_interpretation': 'Bounds across three stipulated shapes, not confidence limits, probabilities or forecasts',
    }


def company_shapes(company):
    index = annual_index(company)
    return {'symbol': company['symbol'], 'currency': company['currency'],
            'eps_basis': company['eps_basis'], 'aggregate_exclusion_reasons': company['aggregate_exclusion_reasons'],
            'individual_diagnostic_only': True, 'reliable_verified_forecast': False,
            'windows': [shape_window(w, index) for w in company['windows']]}


def fund_shapes(pair, panels):
    members = pair['members']
    offset = pair['terminal_offset_years']
    all_scenarios = []
    fixed = []
    for member in members:
        company = panels[member['symbol']]
        if company['aggregate_exclusion_reasons']:
            raise ValueError('V6 excluded accounting/currency basis slipped into fund members')
        for j in [0, offset]:
            w = company['windows'][j]
            if not w['eligible_for_shape_diagnostics'] or not w['eligible_for_provisional_fund_aggregation']:
                raise ValueError('V6 unusable window slipped into a fixed subset')
        fixed.append({k: member[k] for k in ['symbol', 'nav_weight', 'price_USD', 'price_asof']})
    for shape, s in SHAPES:
        components = []
        for m in fixed:
            c = panels[m['symbol']]
            e0 = next(r['eps_proxy'] for r in c['windows'][0]['linear_scenarios'] if r['id'] == shape)
            et = next(r['eps_proxy'] for r in c['windows'][offset]['linear_scenarios'] if r['id'] == shape)
            components.append({'symbol': m['symbol'], 'base_eps_proxy': e0, 'terminal_eps_proxy': et,
                               'base_earnings_per_nav': m['nav_weight']*e0/m['price_USD'],
                               'terminal_earnings_per_nav': m['nav_weight']*et/m['price_USD']})
        base = sum(r['base_earnings_per_nav'] for r in components)
        terminal = sum(r['terminal_earnings_per_nav'] for r in components)
        g = terminal/base-1 if members and base > 0 else None
        all_scenarios.append({'id': shape, 's': s,
                              'growth_of_fixed_covered_subset': g,
                              'base_earnings_per_nav': base if members else None,
                              'terminal_earnings_per_nav': terminal if members else None,
                              'components': components})
    values = [s['growth_of_fixed_covered_subset'] for s in all_scenarios if s['growth_of_fixed_covered_subset'] is not None]
    uniform = next(s['growth_of_fixed_covered_subset'] for s in all_scenarios if s['id'] == 'uniform')
    if members and abs(uniform-pair['growth_of_same_covered_subset']) > 1e-10:
        raise ValueError('s=0 does not reproduce V6 same-subset fund growth')
    exp_components, exp_blocked = [], []
    for m in fixed:
        c = panels[m['symbol']]
        a, b = c['windows'][0]['exponential_scenario'], c['windows'][offset]['exponential_scenario']
        if a['eps_proxy'] is None or b['eps_proxy'] is None:
            exp_blocked.append(m['symbol'])
        else:
            exp_components.append({'symbol': m['symbol'],
                                   'base_earnings_per_nav': m['nav_weight']*a['eps_proxy']/m['price_USD'],
                                   'terminal_earnings_per_nav': m['nav_weight']*b['eps_proxy']/m['price_USD']})
    eb = sum(m['base_earnings_per_nav'] for m in exp_components)
    et = sum(m['terminal_earnings_per_nav'] for m in exp_components)
    return {
        'fund': pair['fund'], 'terminal_offset_years': offset,
        'holdings_date': pair['holdings_date'], 'base_window': pair['base_window'], 'terminal_window': pair['terminal_window'],
        'coverage_nav_weight': pair['coverage_nav_weight'],
        'uncovered_nav_weight_not_assigned_growth': pair['uncovered_nav_weight_not_assigned_growth'],
        'status': 'provisional_fixed_subset_shape_sensitivity' if members else 'blocked_inherited_v6_missing_or_sparse_forecasts',
        'members_fixed_across_linear_shapes': fixed,
        'excluded_holdings': pair['excluded_holdings'],
        'linear_scenarios': all_scenarios,
        'growth_range': [min(values), max(values)] if values else None,
        'range_span_percentage_points': (max(values)-min(values))*100 if values else None,
        'uniform_difference_from_v6': uniform-pair['growth_of_same_covered_subset'] if members else None,
        'exponential_pair': {'status': 'provisional_fixed_subset_shape_only' if members and not exp_blocked else 'blocked_do_not_change_subset_to_make_it_fit',
                             'growth_of_same_subset': et/eb-1 if members and not exp_blocked and eb > 0 else None,
                             'members_without_complete_adjacent_year_shapes': exp_blocked,
                             'components': exp_components},
        'complete_fund_growth': None, 'expected_return': None, 'probability': None,
        'use_as_default_growth': False,
        'range_interpretation': 'Three deterministic annual-shape scenarios using the exact V6 eligible subset; not a full ETF forecast or confidence interval',
    }


def build():
    path = ROOT/'v6/calendar_eps.json'
    source = json.loads(path.read_text(encoding='utf8'))
    companies = [company_shapes(c) for c in source['companies']]
    panels = {c['symbol']: c for c in companies}
    funds = [fund_shapes(f, panels) for f in source['funds']]
    focus = []
    for symbol in ['MRVL', 'NVDA']:
        c = panels[symbol]
        individual_pairs = []
        for shape, s in SHAPES:
            a = next(x['eps_proxy'] for x in c['windows'][0]['linear_scenarios'] if x['id'] == shape)
            b = next(x['eps_proxy'] for x in c['windows'][1]['linear_scenarios'] if x['id'] == shape)
            individual_pairs.append({'id': shape, 's': s,
                                     'ntm0_to_ntm1_growth_proxy': b/a-1 if a is not None and b is not None and a > 0 else None})
        individual_values = [x['ntm0_to_ntm1_growth_proxy'] for x in individual_pairs if x['ntm0_to_ntm1_growth_proxy'] is not None]
        focus.append({'symbol': symbol, 'currency': c['currency'],
                      'remains_excluded_from_fund_aggregation': bool(c['aggregate_exclusion_reasons']),
                      'aggregate_exclusion_reasons': c['aggregate_exclusion_reasons'],
                      'individual_ntm0_to_ntm1_linear_scenarios': individual_pairs,
                      'individual_ntm0_to_ntm1_growth_range': [min(individual_values), max(individual_values)] if individual_values else None,
                      'individual_pair_interpretation': 'Source-unit diagnostic only; currency/accounting exclusions remain and no ETF/default growth is inferred',
                      'windows': [{k: w[k] for k in ['label', 'start', 'end_exclusive', 'source_v6_uniform_eps', 'eps_range', 'range_span_fraction_of_uniform', 'exponential_scenario', 'blocking_reasons']} for w in c['windows']]})
    result = {
        'schema': 'etf.calendar_eps_shape_sensitivity.v1',
        'built_utc': datetime.now(timezone.utc).isoformat(),
        'asof': source['asof'], 'source_information_cutoff': source['source_information_cutoff'],
        'v6_input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'source_annual_forecast_sha256': source['source_sha256'],
        'same_v6_common_price_asof': source['common_price_asof'],
        'shapes': [{'id': k, 's': s, 'density': '1+s*(2*u-1)', 'full_year_mass': linear_mass(0, 1, s)} for k, s in SHAPES],
        'formulas': {'linear_mass': '(b-a)+s*((b^2-b)-(a^2-a)) = (b-a)*(1+s*(a+b-1))',
                     'eps_contribution': 'FY annual EPS unchanged × normalized density mass over the overlap',
                     'exponential_density': 'exp(k*u)/Z with k=log(next_FY_EPS/current_FY_EPS), only adjacent positive, count-qualified known forecasts',
                     'same_subset_growth': 'sum(w_i*EPS_T_i/P_i)/sum(w_i*EPS_0_i/P_i)-1 using identical members for all three linear s'},
        'companies': companies, 'funds': funds, 'focus_companies': focus,
        'controls': {'annual_eps_total_unchanged': True, 'density_nonnegative_for_presets': True,
                     'v6_count_currency_accounting_exclusions_retained': True,
                     'linear_subset_fixed_across_shapes': True, 'no_missing_year_extrapolation': True,
                     'no_model_default_growth_written': True},
        'limits': [
            'These stipulated shapes are not estimated seasonality or realized earnings timing',
            'Annual total forecasts, EPS/share definitions and month-end fiscal proxies remain as uncertain as V6',
            'Each fiscal year resets its shape; continuity across fiscal boundaries is not imposed or claimed',
            'Exponential k uses another uncertain annual forecast; absent/sparse adjacent years block that optional scenario without fallback',
            'Individual MRVL/NVDA diagnostics do not cure currency or accounting exclusions; neither is added to fund aggregates',
            'Three-year exit NTM gaps remain blocked; shape sensitivity does not invent FY2030/FY2031 data',
            'Ranges describe deterministic scenario variation, not confidence bounds, probability distributions or full ETF expected growth',
            'Eligible subsets may differ by horizon in V6; growth from different horizons cannot be spliced into a path',
        ],
    }
    out = ROOT/'v7';out.mkdir(exist_ok=True)
    (out/'calendar_tilt.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf8')
    return result


if __name__ == '__main__':
    x = build()
    print(json.dumps({'funds': [{'fund': f['fund'], 'T': f['terminal_offset_years'],
                               'coverage': f['coverage_nav_weight'], 'growth_range': f['growth_range']}
                              for f in x['funds']],
                      'focus': [{'symbol': c['symbol'], 'windows': [{'label': w['label'], 'range': w['eps_range']} for w in c['windows']]} for c in x['focus_companies']]}, ensure_ascii=False))

```


## v7_calendar_tilt_tests.py
SHA256: d1c7f27053cdc7baa4572e38e945671fec275308a7103025a5779e60996ffb0a

```python
"""Specifications for mass-preserving within-year EPS shape sensitivity."""
from copy import deepcopy
from datetime import date
import math
import unittest
from v6_calendar import calendarize, company_panel, aggregate_pair
from v7_calendar_tilt import linear_density, linear_mass, exponential_mass, shape_window, company_shapes, fund_shapes


def annual(month, year, eps, count=5):
    return {'period': f'{month} {year}', 'eps_mean': eps, 'estimate_count': count}


def company(symbol='ABC', currency='USD'):
    return {'symbol': symbol, 'currency': currency,
            'annual_forecasts': [annual('Dec', y, (y-2025)*12) for y in range(2026, 2032)],
            'price_reference': {'value': 100, 'asof': '2026-10-26_close'}}


class TiltTests(unittest.TestCase):
    def test_linear_full_year_mass_and_partition_conservation(self):
        cuts = [0, .03, .2, .45, .9, 1]
        for s in [-.5, 0., .5]:
            self.assertEqual(linear_mass(0, 1, s), 1)
            self.assertAlmostEqual(sum(linear_mass(a, b, s) for a, b in zip(cuts, cuts[1:])), 1)
            self.assertAlmostEqual(sum(27*linear_mass(a, b, s) for a, b in zip(cuts, cuts[1:])), 27)

    def test_density_nonnegative(self):
        for s in [-1, -.5, 0, .5, 1]:
            self.assertTrue(all(linear_density(i/100, s) >= 0 for i in range(101)))
        with self.assertRaises(ValueError):
            linear_density(.2, 1.01)

    def test_stable_mass_equals_requested_integral(self):
        a, b, s = .2, .7, .5
        self.assertAlmostEqual(linear_mass(a, b, s), (b-a)+s*((b*b-b)-(a*a-a)))

    def test_uniform_reproduces_v6_cross_year_window(self):
        c = company_panel(company())
        out = company_shapes(c)
        for old, new in zip(c['windows'], out['windows']):
            self.assertAlmostEqual(new['uniform_difference_from_v6'], 0)
            self.assertAlmostEqual(next(s['eps_proxy'] for s in new['linear_scenarios'] if s['s'] == 0), old['eps_proxy'])

    def test_front_and_back_tilt_move_in_opposite_directions(self):
        c = company_shapes(company_panel(company()))['windows'][0]
        vals = [s['eps_proxy'] for s in c['linear_scenarios']]
        self.assertGreater(vals[0], vals[1])
        self.assertLess(vals[2], vals[1])
        self.assertAlmostEqual((vals[0]+vals[2])/2, vals[1])

    def test_missing_fy_blocks_all_three_shapes(self):
        raw = company();raw['annual_forecasts'] = raw['annual_forecasts'][:1]
        w = company_shapes(company_panel(raw))['windows'][0]
        self.assertIsNone(w['eps_range'])
        self.assertTrue(all(s['eps_proxy'] is None for s in w['linear_scenarios']))

    def test_sparse_fy_does_not_become_reliable_by_tilting(self):
        for count in [1, 2]:
            raw = company();raw['annual_forecasts'][1]['estimate_count'] = count
            w = company_shapes(company_panel(raw))['windows'][0]
            self.assertFalse(w['eligible_for_shape_diagnostics'])
            self.assertIsNone(w['eps_range'])

    def test_nvda_and_mrvl_units_remain_excluded_from_aggregate(self):
        for symbol, currency in [('NVDA', 'USD'), ('MRVL', 'USD_assumed_US_listing_not_independently_reconciled')]:
            v6 = company_panel(company(symbol, currency));v7 = company_shapes(v6)
            self.assertTrue(v7['windows'][0]['eligible_for_shape_diagnostics'])
            self.assertFalse(v7['windows'][0]['eligible_for_provisional_fund_aggregation'])
            self.assertTrue(v7['aggregate_exclusion_reasons'])

    def test_same_fund_members_for_every_shape(self):
        a, b = company_panel(company('AAA')), company_panel(company('BBB'))
        holdings = [{'fund': 'F', 'date': '2026-10-26', 'symbol': 'AAA', 'weight': .2},
                    {'fund': 'F', 'date': '2026-10-26', 'symbol': 'BBB', 'weight': .3}]
        pair = aggregate_pair('F', holdings, {'AAA': a, 'BBB': b}, 1, '2026-10-26_close')
        x = fund_shapes(pair, {'AAA': company_shapes(a), 'BBB': company_shapes(b)})
        sets = [{r['symbol'] for r in s['components']} for s in x['linear_scenarios']]
        self.assertEqual(sets, [{'AAA', 'BBB'}]*3)
        self.assertAlmostEqual(x['uniform_difference_from_v6'], 0)

    def test_inherited_three_year_gap_keeps_empty_subset(self):
        raw = company();raw['annual_forecasts'] = raw['annual_forecasts'][:4]
        c = company_panel(raw)
        p = aggregate_pair('F', [{'fund': 'F', 'date': '2026-10-26', 'symbol': 'ABC', 'weight': .3}], {'ABC': c}, 3, '2026-10-26_close')
        x = fund_shapes(p, {'ABC': company_shapes(c)})
        self.assertEqual(x['members_fixed_across_linear_shapes'], [])
        self.assertIsNone(x['growth_range'])
        self.assertTrue(all(s['growth_of_fixed_covered_subset'] is None for s in x['linear_scenarios']))

    def test_exponential_full_mass_and_uniform_limit(self):
        for k in [-100, -.7, 0, .7, 100]:
            self.assertAlmostEqual(exponential_mass(0, 1, k), 1)
            self.assertAlmostEqual(sum(exponential_mass(i/10, (i+1)/10, k) for i in range(10)), 1)
        self.assertAlmostEqual(exponential_mass(.2, .7, 0), .5)

    def test_optional_exponential_needs_adjacent_qualified_year(self):
        raw = company();raw['annual_forecasts'] = raw['annual_forecasts'][:2]
        c = company_shapes(company_panel(raw))
        self.assertTrue(c['windows'][0]['eligible_for_shape_diagnostics'])
        self.assertIsNone(c['windows'][0]['exponential_scenario']['eps_proxy'])

    def test_source_component_dates_must_match_denominator(self):
        old = company_panel(company())['windows'][0]
        old['components'][0]['fiscal_days'] = 100
        with self.assertRaises(ValueError):
            shape_window(old)


if __name__ == '__main__':
    unittest.main(verbosity=1)

```


## V7_READ_FIRST.md
SHA256: 0012e85781eb225e572b5bf9fb3ba57e209ca960ed67462b4d3507168c8cdbc4

```text
# ETF V7 审阅起点

当前算法：declared-earnings-periods-v7。
v6_calc.js 保留兼容文件名，包含V7新增约束与事件编号；不是旧V6算法。
当前 v6_calc.js 原始字节 SHA256：b3a085a05abacd581ac4d09391a1b51e0826974f368945087f2d8124efa4840a
固定审阅快照：v7-c87c0745092b7c30。文件哈希核对原始下载字节，不要先转换换行或编码。

请先审阅 v6_calc.js、app.js、model.js、v7_episodes.py、v7_calendar_tilt.py。
两份 *_tests.py 可检查Python事件及EPS形状规格。reproduce.py 是纯标准库价格图复现。
data/ 包含本次冻结的事件计数、形状诊断和测试记录。
Python诊断脚本还依赖V6/V3模块及原始行情，完整离线重跑仍需要此前完整复现包；单文件文本不是完整运行环境。

图表复现：python reproduce.py --input data.json --symbol QQQM --horizon 3y
根网站data.json是冻结2026-10-26收盘的图表数据。不是当前报价，不含完整历史策略重跑输入。
V5/V6报告和原v6_calc_archived.js.txt是历史对照，不要当作当前实现。

当前修改：增长、倍数、目标年化、EPS默认留空；必须声明盈利分母和对应期间；浅回撤从峰值锚点编号并区分恢复状态；年度EPS保持年度总额的期内形状敏感性；主审阅表不突出条件均值差。
限制：标签与日期检查不能核实手填盈利的真实性。完整基金EPS、三年退出盈利、真实季度季节性、外部独立验证仍缺失。测试通过不代表投资有效。所有前瞻输出均为条件假设，不是底部信号。

请分别报告实际读过、运行过、外部核实过和未完成的部分。每个错误给出文件/函数、反例、影响和修复建议。不要把相同规格的交叉复算叫作外部独立审计。

```


## manifest.json
SHA256: 413b17df53d056d2b9affe9677ecda11aa0cc1de934791bcf57904bd6a9ec0fd

```text
{
  "release": "v7-c87c0745092b7c30",
  "algorithm_version": "declared-earnings-periods-v7",
  "main_source_sha256": "b3a085a05abacd581ac4d09391a1b51e0826974f368945087f2d8124efa4840a",
  "hash_scope": "raw file bytes; UTF-8; preserve line endings",
  "files": {
    "model.js": {
      "sha256": "485b02211349c167d63b3b72d9c0e31c785c41ebe41cf1c428d8633f7e7c2b28",
      "bytes": 6548
    },
    "v6_calc.js": {
      "sha256": "b3a085a05abacd581ac4d09391a1b51e0826974f368945087f2d8124efa4840a",
      "bytes": 9812
    },
    "app.js": {
      "sha256": "b625896b94d9d68d9061e368e7b90d415f9c585c2a74f9906e7e5aeb25d76a7d",
      "bytes": 37166
    },
    "reproduce.py": {
      "sha256": "389f292bbedb6a5699e6cd87f15de35a2c9348a0b8e3c9011787e6a402b28c60",
      "bytes": 5466
    },
    "v7_episodes.py": {
      "sha256": "6028f62e15cb3f9834aaaa97206b65e91835bbef7368da409bee344a52fdb467",
      "bytes": 9380
    },
    "v7_episodes_tests.py": {
      "sha256": "403741c2a4514820e5891066ab7698ffecebec7e68acaef4cdc15efbf42a5062",
      "bytes": 4584
    },
    "v7_calendar_tilt.py": {
      "sha256": "4f36ca73ddd702e39f256effd8368a9e7646176e3104ab1f913d4788893b6278",
      "bytes": 16754
    },
    "v7_calendar_tilt_tests.py": {
      "sha256": "d1c7f27053cdc7baa4572e38e945671fec275308a7103025a5779e60996ffb0a",
      "bytes": 5743
    },
    "data/episodes_summary.json": {
      "sha256": "3f4790ca4ebd6fc400708b9cc0aa0cf44fca5bfa4f55178206586401dce283e0",
      "bytes": 797149
    },
    "data/calendar_tilt.json": {
      "sha256": "39ff8af68f456906d2449d6f5e506f74b26ef0c9476ad5fa2c6b0dac25baa97c",
      "bytes": 522715
    },
    "data/checks.json": {
      "sha256": "7d4dc8123c8d192b00d7c5f3fb243ab14dbb5686ffd92283a07c6885fd2d3792",
      "bytes": 2602
    },
    "V7_READ_FIRST.md": {
      "sha256": "0012e85781eb225e572b5bf9fb3ba57e209ca960ed67462b4d3507168c8cdbc4",
      "bytes": 1820
    }
  }
}
```
