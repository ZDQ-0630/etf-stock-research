# V8 审阅文件

V8当前版本：核心文件保留v6_calc.js名称。先读review-response.html，再读v6_calc.js、v8_app.js、app.js与测试。所有前瞻值仍是条件假设；资料映射为参考，完整ETF三年预测未核实。相对情景与绝对估值分别标记。V7固定快照保留，不能代替当前版本。


## model.js
SHA256 485b02211349c167d63b3b72d9c0e31c785c41ebe41cf1c428d8633f7e7c2b28
```
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
SHA256 3513ffe1ead974a5a508ce0b0bdac1c7008493587325844cbb7e245a2d8a1bb0
```
/* V8 conditional arithmetic. FX is SGD per one USD; cash is USD.
   Scenarios and operating inputs are assumptions, never constructed market facts. */
(function(g){'use strict';
 const M=g.ResearchMath||(g.ResearchMath={}),SCENARIO_VERSION='absolute-earnings-periods-v8';
 function finite(x){return typeof x==='number'&&Number.isFinite(x)}
 function checkFinite(values,message='参数使派生数值超出有限范围'){if(!values.every(finite))throw Error(message)}
 function finiteOutput(value){if(typeof value==='number'&&!Number.isFinite(value))throw Error('派生EPS、PE或回报不是有限数值');if(value&&typeof value==='object')Object.values(value).forEach(finiteOutput);return value}
 function validISO(value){return typeof value==='string'&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&Number.isFinite(Date.parse(value+'T00:00:00Z'))&&new Date(value+'T00:00:00Z').toISOString().slice(0,10)===value}
 function couponValue(annual,tax,rate,years,at=years){
  checkFinite([annual,tax,rate,years,at]);if(annual<0||tax<0||tax>1||rate<=-1||years<=0||years>20||at<0||at>years+1e-10)throw Error('分红、税率、现金利率或支付期间无效');
  let total=0;for(let k=1;k<=Math.floor(years);k++)if(k<=at+1e-10)total+=annual*(1-tax)*(1+rate)**(at-k);
  const stub=years-Math.floor(years);if(stub>1e-10&&at>=years-1e-10)total+=annual*stub*(1-tax);
  checkFinite([total]);return total;
 }
 function validateExecution(x){
  const keys=['budget','entry','target','years','fx0','fx1','bps','fee','fx_bps','cash_rate','shock','dividend'];
  if(!keys.every(k=>finite(x[k]))||Math.min(x.budget,x.entry,x.target,x.years,x.fx0,x.fx1)<=0||x.years>20||x.bps<0||x.bps>=10000||x.fx_bps<0||x.fx_bps>=10000||x.fee<0||x.cash_rate<=-1||x.shock<=-1||x.shock>0||x.dividend<0)throw Error('请检查价格、资金、年数、费用与分红；FX表示1美元对应的新元数');
  if(x.withholding!==null&&(!finite(x.withholding)||x.withholding<0||x.withholding>1))throw Error('分红预扣率须为0–100%，不清楚时留空');
  if(x.dividend>0&&x.withholding===null)throw Error('已加入分红，请填写假设预扣率；SGD计价不能推断税务居民');
 }
 function executionV6(input,integer=false){
  if(typeof integer!=='boolean')throw Error('整股标志须为布尔值');const x={dividend:0,withholding:null,...input};validateExecution(x);
  const f=x.fx_bps/10000,c=x.bps/10000,usd=x.budget*(1-f)/x.fx0,unitCost=x.entry*(1+c);checkFinite([usd,unitCost]);
  const affordable=Math.max(0,(usd-x.fee)/unitCost),units=integer?Math.floor(affordable):affordable;checkFinite([affordable,units]);
  let cash=usd-units*unitCost-(units>0?x.fee:0);checkFinite([cash]);if(cash< -1e-10*Math.max(1,usd))throw Error('交易份额超过可用资金');if(cash<0)cash=0;
  const tax=x.withholding??0,dividendValue=couponValue(x.dividend,tax,x.cash_rate,x.years),steps=Math.max(4,Math.ceil(x.years*4)),points=Array.from({length:steps+1},(_,k)=>k/steps);points.push(1/3);for(let k=1;k<=Math.floor(x.years);k++)points.push(k/x.years);
  let peak=x.budget,dd=0;
  const path=[...new Set(points)].sort((a,b)=>a-b).map(frac=>{
   const t=x.years*frac,price=frac===1?x.target:frac<=1/3?x.entry*(1+x.shock)**(frac*3):Math.exp(Math.log(x.entry)+Math.log1p(x.shock)+(frac-1/3)*1.5*(Math.log(x.target)-Math.log(x.entry)-Math.log1p(x.shock)));
   const cashT=cash*(1+x.cash_rate)**t+units*couponValue(x.dividend,tax,x.cash_rate,x.years,t),fx=frac===1?x.fx1:Math.exp(Math.log(x.fx0)+frac*(Math.log(x.fx1)-Math.log(x.fx0)));
   let value=(units*price+cashT)*fx;if(frac===1)value=((units>0?units*x.target*(1-c)-x.fee:0)+cashT)*x.fx1*(1-f);
   checkFinite([t,price,cashT,fx,value]);if(price<=0||fx<=0)throw Error('压力路径发生数值下溢');peak=Math.max(peak,value);dd=Math.min(dd,value/peak-1);checkFinite([dd]);return {year:t,price,wealth_sgd:value,cash_usd:cashT};
  });
  const terminal=path.at(-1).wealth_sgd,annualized=terminal>0?Math.expm1((Math.log(terminal)-Math.log(x.budget))/x.years):null;
  return finiteOutput({units,cash_usd:cash,cash_currency:'USD',initial_usd:usd,dividend_per_unit_at_T_usd:dividendValue,terminal_sgd:terminal,annualized,path_max_drawdown:dd,path,sale_fee_exceeds_stock_proceeds:units>0&&x.fee>units*x.target*(1-c)});
 }
 function validateScenario(input){
  if(!input||!Object.prototype.hasOwnProperty.call(input,'fund_fee')||!finite(input.fund_fee))throw Error('必须显式提供基金年费率fund_fee，未知不得默认0');
  const x={dividend:0,withholding:null,fee_mode:'deduct',valuation_basis:'unverified',context_mode:'current',...input};
  if(!['reference','base_eps','hurdle','fund_fee','years'].every(k=>finite(x[k]))||x.reference<=0||x.base_eps<=0||x.hurdle<=-1||x.fund_fee<0||x.fund_fee>=1||x.years<3||x.years>20||!Number.isInteger(x.years)||!['deduct','embedded'].includes(x.fee_mode))throw Error('需正参考价/基准EPS、显式费率及整数3–20年情景');
  if(!['ttm','ntm','normalized'].includes(x.valuation_basis))throw Error('先声明TTM、NTM或归一化盈利分母');
  for(const k of ['valuation_date','price_date','base_start','base_end','terminal_start','terminal_end'])if(!validISO(x[k]))throw Error('需真实价格日期、估值日及基准/退出盈利窗口，末日不含');
  if(!['current','historical'].includes(x.context_mode))throw Error('context_mode须为current或historical');
  const age=(Date.parse(x.valuation_date+'T00:00:00Z')-Date.parse(x.price_date+'T00:00:00Z'))/86400000;
  if(age<0||(x.context_mode==='current'?age!==0:age>7))throw Error('价格须与估值日同日；historical模式仅允许过去7天内价格，不得用未来价格');
  let evidenceStatus='unverified',evidenceDate=null;
  if(x.evidence_date!==null&&x.evidence_date!==undefined&&x.evidence_date!==''){
   if(!validISO(x.evidence_date))throw Error('证据日期无效');if(x.evidence_date>x.valuation_date)throw Error('证据日期不得晚于估值日');evidenceDate=x.evidence_date;evidenceStatus='declared_date_not_independently_verified';
  }
  if(addYears(x.base_start,1)!==x.base_end||addYears(x.base_start,x.years)!==x.terminal_start||addYears(x.base_end,x.years)!==x.terminal_end)throw Error('盈利窗口须为一日历年，退出窗口须整体平移持有年数');
  if(x.valuation_basis==='ntm'&&x.base_start!==x.valuation_date)throw Error('NTM窗口必须从估值日开始');
  if(x.valuation_basis==='ttm'&&x.base_end!==x.valuation_date)throw Error('TTM窗口末日必须为估值日');
  if(x.valuation_basis==='normalized'&&x.base_end!==x.valuation_date)throw Error('归一化EPS须声明为估值日对应的年度化基准，窗口末日须等于估值日；历史周期调整期间另在来源说明中列出');
  if(typeof x.source_note!=='string'||!x.source_note.trim())throw Error('需基准和退出EPS同基金份额口径的来源/假设说明，局部持仓EPS不可代填');
  if(x.valuation_basis==='normalized'&&x.source_note.trim().length<12)throw Error('归一化盈利需说明周期期间和调整方法');
  const basePE=x.reference/x.base_eps;checkFinite([basePE]);if(basePE<=0)throw Error('基准PE不可用');
  return {x,basePE,dateAlignment:{price_date:x.price_date,valuation_date:x.valuation_date,price_age_days:age,context_mode:x.context_mode},evidenceDate,evidenceStatus};
 }
 function evaluateTarget(x,gross,earnings,terminalEPS,terminalPE,model){
  const expense=x.fee_mode==='embedded'?1:(1-x.fund_fee)**x.years,target=gross*expense;
  checkFinite([gross,expense,target,earnings,terminalEPS,terminalPE]);if(Math.min(gross,expense,target,earnings,terminalEPS,terminalPE)<=0)throw Error('正盈利PE估值不可用或终值发生数值下溢');
  const fractional=executionV6({...x,target},false),integer=executionV6({...x,target},true),f=x.fx_bps/10000,c=x.bps/10000,required=x.budget*(1+x.hurdle)**x.years/(x.fx1*(1-f)),dividend=fractional.dividend_per_unit_at_T_usd;
  checkFinite([required]);if(required<=0)throw Error('目标财富发生数值下溢');
  const unitPayoff=target*(1-c)+dividend,requiredUnits=(required+x.fee)/unitPayoff;checkFinite([unitPayoff,requiredUnits]);if(unitPayoff<=0||requiredUnits<=0)throw Error('每份额终值或所需份额无效');
  const maxEntry=fractional.initial_usd>x.fee?(fractional.initial_usd-x.fee)/(requiredUnits*(1+c)):null;
  if(maxEntry!==null&&(!finite(maxEntry)||maxEntry<=0))throw Error('条件买价上限不是有限正数');
  let reverse={status:'no_stock_exposure',required_net_target:null,required_gross_target:null};
  if(fractional.units>0){
   const q=fractional.units,rawNet=(required-fractional.cash_usd*(1+x.cash_rate)**x.years-q*dividend+x.fee)/(q*(1-c)),net=Math.max(0,rawNet),needGross=net/expense,needEPS=needGross/terminalPE,needFactor=needEPS/x.base_eps;
   checkFinite([rawNet,net,needGross,needEPS,needFactor]);
   reverse={status:'conditional_breakpoint',required_net_target:net,required_gross_target:needGross,required_terminal_eps:needEPS,required_terminal_pe:needGross/terminalEPS,required_earnings_factor:needFactor,required_uniform_growth:needFactor**(1/x.years)-1,income_and_cash_alone_cover_hurdle:rawNet<=0};
   if(model==='relative_sensitivity_compatibility')Object.assign(reverse,{required_later_growth:(needFactor/(1+x.g1))**(1/(x.years-1))-1,required_multiple:needGross/(x.reference*earnings)});
  }
  return finiteOutput({target,gross_target:gross,expense_factor:expense,fund_fee:x.fund_fee,fee_mode:x.fee_mode,maxEntry,max_entry_status:maxEntry===null?'no_stock_purchase_affordable':'full_fractional_deployment_bound',fractional,integer,reverse,earnings_factor:earnings,terminal_eps:terminalEPS,terminal_pe:terminalPE,valuation_model:model,scope:x.dividend>0?'Conditional price and user-assumed cash dividends/withholding':'Conditional capital-price return; distributions omitted',decision_status:'not_decision_ready',algorithm_version:SCENARIO_VERSION});
 }
 function scenarioV6(input){
  const v=validateScenario(input),x=v.x;if(!['g1','growth','multiple'].every(k=>finite(x[k]))||x.g1<=-1||x.growth<=-1||x.multiple<=0)throw Error('相对敏感性须有效盈利增长和倍数比例');
  const earnings=(1+x.g1)*(1+x.growth)**(x.years-1),terminalEPS=x.base_eps*earnings,terminalPE=v.basePE*x.multiple,gross=x.reference*earnings*x.multiple;
  const r=evaluateTarget(x,gross,earnings,terminalEPS,terminalPE,'relative_sensitivity_compatibility');
  return finiteOutput({...r,base_eps:x.base_eps,base_pe:v.basePE,multiple_ratio_vs_base:x.multiple,valuation_basis:x.valuation_basis,base_window:[x.base_start,x.base_end],terminal_window:[x.terminal_start,x.terminal_end],date_alignment:v.dateAlignment,evidence_date:v.evidenceDate,evidence_status:v.evidenceStatus,compatibility_function:'scenarioV6',interpretation:'Relative sensitivity only; terminal PE is linked to the reference PE by assumption, not an independent market valuation.'});
 }
 function scenarioAbsolute(input){
  const v=validateScenario(input),x=v.x;if(!finite(x.terminal_eps)||x.terminal_eps<=0||!finite(x.terminal_pe)||x.terminal_pe<=0)throw Error('绝对PE情景需独立的正退出EPS及正退出PE；亏损/非正EPS不可用PE估值');
  const gross=x.terminal_eps*x.terminal_pe,earnings=x.terminal_eps/x.base_eps,multiple=x.terminal_pe/v.basePE;checkFinite([gross,earnings,multiple]);
  const r=evaluateTarget(x,gross,earnings,x.terminal_eps,x.terminal_pe,'absolute_terminal_eps_pe');
  return finiteOutput({...r,base_eps:x.base_eps,base_pe:v.basePE,multiple_ratio_vs_base:multiple,valuation_basis:x.valuation_basis,base_window:[x.base_start,x.base_end],terminal_window:[x.terminal_start,x.terminal_end],date_alignment:v.dateAlignment,evidence_date:v.evidenceDate,evidence_status:v.evidenceStatus,interpretation:'Exit price is independently supplied terminal EPS times terminal PE; reference price only defines the displayed base PE. All forward inputs remain scenarios.'});
 }
 function operatingBridgeV8(input){
  const x=input||{},growth=x.revenue_growth_path,margins=x.operating_margin_path,shares=x.share_factor_path;
  if(!finite(x.R0)||x.R0<=0||!Array.isArray(growth)||!growth.length||growth.length>20||!Array.isArray(margins)||!Array.isArray(shares)||margins.length!==growth.length||shares.length!==growth.length)throw Error('需R0美元/基准份额，及同长度逐年收入增长、经营利润率、累计股数因子');
  const n=growth.length;
  function path(value,name){const a=Array.isArray(value)?value:Array(n).fill(value);if(a.length!==n||!a.every(finite))throw Error(name+'须显式为有限数或同长度逐年数组');return a}
  const interest=path(x.interest_per_share,'利息/基准份额'),tax=path(x.tax_rate,'税率'),other=path(x.other_recurring_per_share,'其他经常项/基准份额');
  if(!growth.every(v=>finite(v)&&v>=-1)||!margins.every(finite)||!shares.every(v=>finite(v)&&v>0)||interest.some(v=>v<0)||tax.some(v=>v<0||v>1))throw Error('经营路径需有限数，收入增长不得低于−100%，股数因子正、利息非负、税率0–100%');
  let revenue=x.R0;const years=growth.map((rate,i)=>{revenue*=1+rate;const operating=revenue*margins[i],pretax=operating-interest[i]+other[i],taxExpense=pretax>0?pretax*tax[i]:0,afterTax=pretax-taxExpense,eps=afterTax/shares[i];checkFinite([revenue,operating,pretax,taxExpense,afterTax,eps]);return {year:i+1,revenue_per_base_share_usd:revenue,operating_margin:margins[i],operating_profit_per_base_share_usd:operating,interest_per_base_share_usd:interest[i],other_recurring_per_base_share_usd:other[i],pretax_per_base_share_usd:pretax,tax_rate:tax[i],tax_per_base_share_usd:taxExpense,share_factor:shares[i],eps_usd:eps,pe_valuation_available:eps>0}});
  const terminal=years.at(-1).eps_usd,available=terminal>0;
  return finiteOutput({years,terminal_eps:terminal,valuation_eps:available?terminal:null,pe_valuation_available:available,status:available?'conditional_positive_terminal_eps':'unavailable_for_pe_nonpositive_terminal_eps',eps_type:'conditional_common_eps_proxy',assumption_status:'user_assumptions_not_market_facts',share_factor_basis:'Cumulative total shares divided by base-date shares; revenue and other per-share items are USD per base-date share before dilution.',tax_policy:'Tax only positive pretax income; no automatic loss tax benefit.',attribution_assumption:'Assumes modeled profit belongs to common shareholders; no separate noncontrolling interest or preferred-dividend deduction supplied.',algorithm_version:SCENARIO_VERSION});
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
 Object.assign(M,{scenarioAbsolute,scenarioRelativeV8:scenarioV6,operatingBridgeV8,executionV8:executionV6,HISTORY_VIEW_VERSION:'any-decline-episodes-v7',SCENARIO_VERSION,episodeLabels,couponValue,executionV6,scenarioV6,distributionV6,calendarEndIndex:endIndex});
})(typeof window==='undefined'?globalThis:window);

```

## app.js
SHA256 b2a8dc44716443be34d45954b8ca72fea07db9ad53174a9c1b78cca294c75392
```
(()=>{'use strict';
const DATA=window.RESEARCH_DATA,M=window.ResearchMath,$=id=>document.getElementById(id),esc=x=>String(x??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),fmt=(x,n=2)=>x==null||!Number.isFinite(x)?'—':x.toLocaleString('en-US',{minimumFractionDigits:n,maximumFractionDigits:n}),pct=x=>x==null?'—':fmt(x*100,1)+'%',money=x=>x==null?'—':(x<0?'−':'')+'S$'+fmt(Math.abs(x),0);
const known=Object.keys(DATA.series),KEY='etf_research_local_rows_v1';let local={};const savedRowWarnings={};try{const cache=JSON.parse(localStorage.getItem(KEY)||'{}');for(const [s,v]of Object.entries(cache))if(known.includes(s)){try{local[s]={...v,rows:M.validateRows(v.rows,s,known)}}catch(e){savedRowWarnings[s]=e.message}}}catch(e){savedRowWarnings.all='无法读取浏览器历史缓存：'+e.message}
function rowsFor(s){const map=new Map(DATA.series[s].map(r=>[r[0],r[1]]));for(const r of local[s]?.rows??[])map.set(r[0],r[1]);return [...map].sort((a,b)=>a[0].localeCompare(b[0]))}
function save(){try{localStorage.setItem(KEY,JSON.stringify(local));return true}catch{return false}}
function download(name,obj){const blob=new Blob([typeof obj==='string'?obj:JSON.stringify(obj,null,2)],{type:typeof obj==='string'?'text/csv':'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),800)}
function options(select){if(!select)return;select.innerHTML=known.map(s=>`<option value="${s}">${s==='QQQ'?'QQQ · 长历史代理':s}</option>`).join('');select.value='QQQM'}
function gate(){const e=DATA.evidence,now=Date.now(),due=e.events.some(v=>v.scheduled_at&&Date.parse(v.scheduled_at)<=now&&!v.actual&&v.event_status_at_snapshot!=='already_reported'),expired=!e.last_review||Date.parse(e.last_review.payload.valid_until)<=now;return e.active_conclusion_allowed&&!due&&!expired}
function renderHome(){if($('homeView')){
 const review=DATA.evidence?.last_review,conclusion=review?.payload?.conclusion,hasConclusion=typeof conclusion==='string'&&conclusion.trim()!=='',active=gate()&&hasConclusion;
 $('homeStatus').textContent=active?'有条件的研究判断':'历史结论待复核';$('homeStatus').classList.toggle('warn',!active);
 $('homeHeadline').textContent=active?'依据最新复核记录，评估入场条件。':'先更新证据，再使用入场结论。';
 $('homeView').textContent=hasConclusion?(active?conclusion:'【已过期或待复核的历史记录】'+conclusion+' 当前请先核对新事实；此段不代表已更新的入场判断。'):'尚无有效的分析复核摘要。历史图和手填情景可用于研究，不能据此判断当前入场。';
 $('reviewDate').textContent='冻结研究的原始价格截至 '+DATA.price_cutoff+' · 最近分析复核记录：'+(review?.recorded_at??'尚无')+'（不是所有财报或预测的更新时间）。各基金卡显示实际使用的价格日期与来源。';
 const notes={QQQM:'关注云增长能否转成每股现金回报。',SMH:'关注AI订单兑现与行业集中风险。',SOXX:'区分AI需求与工业、汽车等周期。',DRAM:'关注存储正常化利润与新增产能。'};
 $('homeFunds').innerHTML=['QQQM','SMH','SOXX','DRAM'].map(s=>{const a=M.states(rowsFor(s)).at(-1),updated=Boolean(local[s]?.rows?.length),source=updated?'含浏览器本地输入，未独立核实':'冻结行情快照';return `<a class="fund" href="history.html?symbol=${s}"><strong>${s}</strong><span class="value">回撤 ${pct(a.dd)}</span><small>价格日期 ${esc(a.date)} · ${esc(source)}</small><p>${notes[s]}</p></a>`}).join('')
}}
renderHome();setInterval(renderHome,60000);
let chart={symbol:'QQQM',range:'3',mode:'price',horizon:126},shown=[],allStates=[];
function svgPlot(svg,lines,{percent=false,labels=[],baseline=null}={}){const values=lines.flatMap(l=>l.points.map(p=>p.y)).filter(Number.isFinite);if(!values.length){svg.innerHTML='<text x="60" y="120">数据不足</text>';return}let lo=Math.min(...values),hi=Math.max(...values);if(baseline!==null){lo=Math.min(lo,baseline);hi=Math.max(hi,baseline)}const pad=(hi-lo||Math.abs(hi)*.05||1)*.12;lo-=pad;hi+=pad;const width=Math.max(300,svg.clientWidth||1000),plotWidth=width-82;svg.setAttribute('viewBox','0 0 '+width+' 300');const X=f=>62+plotWidth*f,Y=y=>254-222*(y-lo)/(hi-lo);let markup='';for(let i=0;i<=4;i++){const v=lo+(hi-lo)*i/4,y=Y(v);markup+=`<line x1="62" x2="${width-20}" y1="${y}" y2="${y}" stroke="#e7ece6"/><text x="49" y="${y+4}" text-anchor="end">${percent?pct(v):fmt(v,Math.abs(v)<20?2:0)}</text>`}if(baseline!==null)markup+=`<line x1="62" x2="${width-20}" y1="${Y(baseline)}" y2="${Y(baseline)}" stroke="#adc4b0" stroke-dasharray="4 4"/>`;lines.forEach((l,i)=>{const p=l.points.filter(p=>Number.isFinite(p.y));const points=p.map(p=>X(p.x).toFixed(2)+','+Y(p.y).toFixed(2)).join(' ');if(i===0&&p.length)markup+=`<polygon points="${X(p[0].x)},254 ${points} ${X(p.at(-1).x)},254" fill="#edf4ed" opacity=".8"/>`;markup+=`<polyline fill="none" stroke="${l.color}" stroke-width="2.2" points="${points}"/>`});labels.forEach(([x,label])=>markup+=`<text x="${X(x)}" y="283" text-anchor="${x===0?'start':x===1?'end':'middle'}">${esc(label)}</text>`);markup+='<line id="chartCross" x1="0" x2="0" y1="20" y2="254" stroke="#7e9f8d" stroke-dasharray="3 3" visibility="hidden"/>';svg.innerHTML=markup}
function renderChart(){if(!$('historyChart'))return;const rows=rowsFor(chart.symbol);allStates=M.states(rows);const end=new Date(rows.at(-1)[0]+'T00:00:00Z'),start=new Date(end);if(chart.range!=='all')start.setUTCFullYear(end.getUTCFullYear()-Number(chart.range));shown=allStates.filter(s=>chart.range==='all'||s.date>=start.toISOString().slice(0,10));if(!shown.length)shown=allStates.slice(-1);const pts=shown.map((s,i)=>({x:i/(shown.length-1||1),y:chart.mode==='dd'?s.dd:s.close}));const lines=[{points:pts,color:'#206f5d'}];if(chart.mode==='price')lines.push({points:shown.map((s,i)=>({x:i/(shown.length-1||1),y:s.ma200})).filter(p=>p.y!==null),color:'#91aab6'});svgPlot($('historyChart'),lines,{percent:chart.mode==='dd',baseline:chart.mode==='dd'?0:null,labels:[[0,shown[0].date],[1,shown.at(-1).date]]});const a=allStates.at(-1);$('lastPrice').textContent='$'+fmt(a.close);$('lastDate').textContent=a.date;$('lastDD').textContent=pct(a.dd);$('lastMA').textContent=a.ma200===null?'—':'$'+fmt(a.ma200);$('lastReturn').textContent=rows.length>252?pct(a.close/rows[rows.length-253][1]-1):'—';const localTag=local[chart.symbol]?' · 含未独立核实的本地更新':'';$('chartDate').textContent=`${chart.symbol} · ${allStates[0].date}—${a.date}${localTag} · ${chart.mode==='price'?'细蓝线：200日均价':'峰值取完整可用历史，非仅可见区间'}`;if($('riskRows'))renderRisk();if($('importStatus')){const l=local[chart.symbol];$('importStatus').textContent=l?`本浏览器保留${l.rows.length}行更新，最后导入于${l.imported_at}。原始数据仍可恢复。`:'该标的尚未导入手动数据。';$('dataHash').textContent='算法 '+M.VERSION+'；原始SHA256 '+DATA.manifest.find(m=>m.symbol===chart.symbol).raw_sha256.slice(0,20)+'…';if(savedRowWarnings[chart.symbol]||savedRowWarnings.all){$('importStatus').classList.add('error');$('importStatus').textContent+=' 原缓存未通过当前规则，未用于计算：'+(savedRowWarnings[chart.symbol]??savedRowWarnings.all)}if(l&&l.base_hash!==DATA.manifest.find(m=>m.symbol===chart.symbol).raw_sha256)$('importStatus').textContent+=' 本地更新基于旧版来源，请核对与当前原始快照的差异。'}}
function renderRisk(){const r=M.distributionV6(rowsFor(chart.symbol),chart.horizon);window.lastHistoricalDistribution=r;$('riskScope').textContent=`当前桶 ${r.bin}；成熟日度观察 ${r.n}，未成熟 ${r.censored}，不重叠窗口 ${r.nonoverlap}，支持事件 ${r.episode_count}（已恢复 ${r.recovered_episode_count}、未恢复 ${r.open_episode_count}）；事件外成熟观察 ${r.outside_episode_observations}。这些都不等于独立危机数。`;$('riskRows').innerHTML=[['窗口内进一步下跌',r.downside],['窗口末价格收益',r.returns]].map(([name,vals])=>`<tr><td>${name}</td>${vals.map(v=>`<td class="num">${pct(v)}</td>`).join('')}</tr>`).join('');if($('censoredRows'))$('censoredRows').innerHTML=r.incomplete_recent.map(v=>`<tr><td>${v.date}</td><td>${v.observed_sessions}</td><td>${v.observed_loss_lower_bound===null?'尚无后续观察':pct(v.observed_loss_lower_bound)}</td></tr>`).join('');}

if($('chartAsset')){options($('chartAsset'));const query=new URLSearchParams(location.search).get('symbol');if(known.includes(query))chart.symbol=query;$('chartAsset').value=chart.symbol;$('chartAsset').onchange=e=>{chart.symbol=e.target.value;renderChart()};$('chartRange').onchange=e=>{chart.range=e.target.value;renderChart()};document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{chart.mode=b.dataset.mode;document.querySelectorAll('[data-mode]').forEach(x=>x.classList.toggle('active',x===b));renderChart()});if($('riskHorizon'))$('riskHorizon').onchange=e=>{chart.horizon=e.target.value==='3y'?'3y':Number(e.target.value);renderRisk()};const svg=$('historyChart');svg.onpointermove=e=>{const rect=svg.getBoundingClientRect(),f=Math.max(0,Math.min(1,(e.clientX-rect.left-62)/(rect.width-82))),i=Math.round(f*(shown.length-1)),s=shown[i];const tip=$('historyTip');tip.style.display='block';tip.style.left=Math.min(Math.max(10,e.clientX-rect.left+12),rect.width-170)+'px';tip.innerHTML=`${s.date}<br>${chart.symbol} $${fmt(s.close)}<br>回撤 ${pct(s.dd)}`;const line=svg.querySelector('#chartCross');line.setAttribute('x1',62+(rect.width-82)*i/(shown.length-1||1));line.setAttribute('x2',62+(rect.width-82)*i/(shown.length-1||1));line.setAttribute('visibility','visible')};svg.onpointerleave=()=>{$('historyTip').style.display='none';svg.querySelector('#chartCross')?.setAttribute('visibility','hidden')};renderChart()}
if($('priceFile')){$('priceFile').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>8e6)throw Error('文件太大，请限制在8MB以内');const text=await file.text();let symbol=chart.symbol,rows;if(file.name.toLowerCase().endsWith('.json')){const x=JSON.parse(text);if(Array.isArray(x))rows=x;else if(x.series){symbol=x.params?.symbol??x.symbol??symbol;rows=x.series[symbol]}else{symbol=x.symbol??symbol;rows=x.rows}}else{const lines=text.replace(/^\uFEFF/,'').trim().split(/\r?\n/),header=lines.shift().split(',').map(s=>s.trim().toLowerCase()),di=header.indexOf('date'),pi=header.indexOf('close')>=0?header.indexOf('close'):header.indexOf('price');if(di<0||pi<0)throw Error('CSV需要date,close列');rows=lines.filter(s=>s.trim()).map(s=>{const z=s.split(',');return [z[di]?.trim(),z[pi]?.trim()]})}rows=M.validateRows(rows,symbol,known);const existing=rowsFor(symbol),dates=new Set(existing.map(r=>r[0])),added=rows.filter(r=>!dates.has(r[0])).length,map=new Map((local[symbol]?.rows??[]).map(r=>[r[0],r[1]]));rows.forEach(r=>map.set(r[0],r[1]));local[symbol]={rows:[...map].sort((a,b)=>a[0].localeCompare(b[0])),base_hash:DATA.manifest.find(m=>m.symbol===symbol).raw_sha256,imported_at:new Date().toISOString()};delete savedRowWarnings[symbol];const persisted=save();chart.symbol=symbol;$('chartAsset').value=symbol;renderChart();$('importStatus').textContent=`已处理${rows.length}行：新增${added}行，更正/覆盖${rows.length-added}行。图与历史分布已重算。${persisted?'已保存到本浏览器。':'本浏览器存储不可用，请导出保存。'} 这些输入未独立核实。`;$('importStatus').classList.remove('error')}catch(err){$('importStatus').classList.add('error');$('importStatus').textContent='未导入：'+err.message}};$('resetHistory').onclick=()=>{delete local[chart.symbol];delete savedRowWarnings[chart.symbol];save();renderChart()};$('exportHistory').onclick=()=>{const rows=rowsFor(chart.symbol);download(chart.symbol+'_历史快照.json',{schema:DATA.schema,algorithm_version:M.VERSION,exported_at:new Date().toISOString(),distribution_algorithm_version:M.HISTORY_VIEW_VERSION,params:chart,series:{[chart.symbol]:rows},result:M.distributionV6(rows,chart.horizon),source_manifest:DATA.manifest.find(m=>m.symbol===chart.symbol),input_status:local[chart.symbol]?'contains_unverified_browser_updates':'saved_provider_snapshot'})}}
const fields=[['budget','资金SGD',3000],['reference','估值锚USD（固定）',0],['entry','拟买价USD',0],['years','持有年数',3],['g1','首年每股盈利变化%',null],['growth','此后每年盈利变化%',null],['multiple','终值/基准倍数',null],['hurdle','目标年化%',null],['fx0','起始：1 USD = … SGD',DATA.fx_reference],['fx1','退出：1 USD = … SGD',DATA.fx_reference],['bps','每边交易摩擦bp',5],['fee','每笔费用USD',1],['fx_bps','每次换汇摩擦bp',10],['cash_rate','现金有效年利率%',0],['shock','前1/3期压力跌幅%',-30],['fund_fee','基金年费率%',0],['dividend','每股每年现金分红USD',0],['base_eps','基准EPS：USD/同一基金份额',null],['withholding','分红预扣率%（未知留空）',null]];
const META_FIELDS=['valuation_date','base_start','base_end','terminal_start','terminal_end','source_note'];
const CONTEXT_FIELDS=['price_date','context_mode','evidence_date','evidence_date_status'];
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
 const keys=fields.map(([id])=>id),oldKeys=keys.filter(k=>!['fund_fee','dividend','withholding'].includes(k)),allowed=old?oldKeys:[...keys,...META_FIELDS,...CONTEXT_FIELDS,'fee_mode','valuation_basis'];
 if(Object.keys(raw).some(k=>!allowed.includes(k))||(old?oldKeys:keys).some(k=>!(k==='withholding'&&raw[k]===null)&&(typeof raw[k]!=='number'||!Number.isFinite(raw[k]))))throw Error('情景输入字段缺失、未知或不是有限数字');
 const x={...Object.fromEntries(keys.map(k=>[k,raw[k]])),fee_mode:raw.fee_mode??'deduct',valuation_basis:raw.valuation_basis??'unverified',...Object.fromEntries([...META_FIELDS,...CONTEXT_FIELDS].map(k=>[k,raw[k]]))};
 if(old){x.fund_fee=fundFee(input.symbol);x.dividend=0;x.withholding=null;scenarioLoadWarning='V5情景已迁移：新增基金费率；分红仍未纳入，旧结果已重新计算。'}
 if(!['unverified','ttm','ntm','normalized'].includes(x.valuation_basis))throw Error('盈利基准定义无效');
 M.scenarioV6(x);const basis=input.source_basis;if(basis!=null&&(typeof basis!=='object'||Array.isArray(basis)))throw Error('source_basis必须是对象');
 if(basis?.anchor_date&&!M.validDate(basis.anchor_date))throw Error('估值锚参考日期无效');if(basis?.price_source_sha256&&!/^[a-f0-9]{64}$/i.test(basis.price_source_sha256))throw Error('来源哈希格式无效');
 return {schema:SCENARIO_SCHEMA,algorithm_version:M.VERSION,scenario_algorithm_version:M.SCENARIO_VERSION,symbol:input.symbol,inputs:x,source_basis:basis?JSON.parse(JSON.stringify(basis)):sourceBasis(input.symbol),saved_at:typeof input.saved_at==='string'?input.saved_at:null};
}
try{const store=JSON.parse(localStorage.getItem(SCENARIO_KEY)||'null');if(store){if(store.schema!=='etf.scenario_store.v1'||!store.records||typeof store.records!=='object')throw Error('情景缓存版本不匹配');for(const [symbol,record]of Object.entries(store.records)){try{const valid=validateScenarioRecord(record);if(valid.symbol!==symbol)throw Error('标的键不匹配');scenarioRecords[symbol]=valid}catch{scenarioLoadWarning='部分旧情景未通过校验，未载入；可从导出文件恢复。'}}if(known.includes(store.selected_symbol))scenarioSelected=store.selected_symbol}}catch{scenarioLoadWarning='情景存储不可读，未载入旧值；请导入已导出的情景。'}
const requestedScenario=new URLSearchParams(location.search).get('symbol');if(known.includes(requestedScenario))scenarioSelected=requestedScenario;
function readScenario(){const x=Object.fromEntries(fields.map(([id])=>[id,$('s_'+id).value.trim()===''?(id==='withholding'?null:NaN):Number($('s_'+id).value)]));for(const k of PERCENT_FIELDS)if(x[k]!==null)x[k]/=100;x.fee_mode=$('feeTreatment').value;x.valuation_basis=$('earningsBasis').value;for(const k of META_FIELDS)x[k]=$('s_'+k).value.trim();x.price_date=(scenarioSource??sourceBasis(scenarioAsset)).anchor_date;x.context_mode='historical';x.evidence_date=null;x.evidence_date_status='unverified';return x}
function putScenario(x){META_FIELDS.forEach(k=>$('s_'+k).value=x[k]??'');fields.forEach(([id])=>$('s_'+id).value=x[id]==null?'':PERCENT_FIELDS.includes(id)?x[id]*100:x[id]);$('feeTreatment').value=x.fee_mode??'deduct';$('earningsBasis').value=x.valuation_basis??'unverified'}
function scenarioStatus(message=''){const node=$('scenarioSaveStatus');if(!node)return;const basis=scenarioSource??sourceBasis(scenarioAsset),current=DATA.manifest.find(x=>x.symbol===scenarioAsset)?.raw_sha256,old=basis.price_source_sha256&&current!==basis.price_source_sha256,oldForecast=basis.expectation_version!==DATA.expectations?.version;node.classList.toggle('good',!scenarioStorageFailed);node.classList.toggle('error',scenarioStorageFailed);node.textContent=[message||'有效情景已按标的保存在本浏览器。',scenarioStorageFailed?'浏览器保存失败；请导出JSON备份。':'',old?'官方价格快照已更新，保留原估值锚与假设。':'',oldForecast?'盈利参考已更新；保留你的旧情景，点击恢复参考值可采用本轮参数。':'',scenarioLoadWarning].filter(Boolean).join(' ');if($('scenarioReferenceSummary'))$('scenarioReferenceSummary').textContent='完整基金三年盈利未核实。增长、倍数和EPS默认留空；局部持仓观测见研究页。旧版情景保留在原浏览器存储键，V7不自动激活。'}
function updateScenarioBasis(x){const basis=scenarioSource??sourceBasis(scenarioAsset);const manual=Math.abs(x.reference-(basis.anchor_price??x.reference))>1e-4;const current=rowsFor(scenarioAsset).at(-1);$('scenarioBasis').textContent=`估值锚 $${fmt(x.reference)}（${manual?'手动/导入值；':'固定参考；'}参考日期${basis.anchor_date??'未知'}）；所选历史最后收盘${current[0]} $${fmt(current[1])}${local[scenarioAsset]?'，含本地输入':''}。${'V7手填条件，未独立核实'}。拟买价${basis.entry_mode==='latest_close'?'跟随最新历史收盘':'为保留的手动计划价'}；估值锚不自动移动。当前为历史情景；价格锚日期${x.price_date}，预测可得日未核实，不能据此认定点时预测已验证。`;const posture=$('scenarioInputPosture');if(posture){const ref=DATA.expectations?.reference_inputs_by_symbol?.[scenarioAsset],changed=ref&&['g1','growth','multiple'].some(k=>typeof ref[k]==='number'&&Math.abs(x[k]-ref[k])>1e-12);posture.textContent=basis.origin==='imported_unverified'?'导入情景；来源元数据待核实':!ref?'该标的暂无参考值，当前为演示假设':changed?'含手动调整；来源参考另列':'分析情景，盈利基准尚未验证'}}
function persistScenario(x){const record={schema:SCENARIO_SCHEMA,algorithm_version:M.VERSION,scenario_algorithm_version:M.SCENARIO_VERSION,symbol:scenarioAsset,inputs:{...x},source_basis:JSON.parse(JSON.stringify(scenarioSource??sourceBasis(scenarioAsset))),saved_at:new Date().toISOString()};record.source_basis.anchor_kind=Math.abs(x.reference-(record.source_basis.anchor_price??x.reference))>1e-4?'manual_override':'fixed_source_reference';const ref=record.source_basis.reference_parameters??{};record.parameter_posture=Object.fromEntries(['g1','growth','multiple'].map(k=>[k,record.source_basis.origin==='imported_unverified'?'imported_unverified':typeof ref[k]==='number'&&Math.abs(x[k]-ref[k])<1e-12?'reference_value':'manual_override']));const old=scenarioRecords[scenarioAsset];if(old&&JSON.stringify(old.inputs)===JSON.stringify(record.inputs)&&JSON.stringify(old.source_basis)===JSON.stringify(record.source_basis))record.saved_at=old.saved_at;scenarioRecords[scenarioAsset]=record;try{localStorage.setItem(SCENARIO_KEY,JSON.stringify({schema:'etf.scenario_store.v1',selected_symbol:scenarioAsset,records:scenarioRecords}));scenarioStorageFailed=false}catch{scenarioStorageFailed=true}return record}
function clearScenarioDescriptions(){for(const id of ['valuationDefinition','fundCostBasis','scenarioBasis','scenarioInputPosture','scenarioReferenceSummary'])if($(id))$(id).textContent=''}
function calcScenario(settings={}){if(settings.target?.id==='s_entry'&&scenarioSource)scenarioSource.entry_mode='manual';try{const x=readScenario(),r=M.scenarioV6(x);scenarioLast={symbol:scenarioAsset,inputs:x,result:r};window.lastScenarioSite=scenarioLast;$('scenarioError').classList.add('hidden');$('scenarioError').textContent='';$('scenarioMax').textContent=r.maxEntry===null?'未建股票仓位':'US$'+fmt(r.maxEntry);$('scenarioGap').textContent=`相对参考价 ${r.maxEntry===null?'不可计算':pct(r.maxEntry/x.reference-1)}。这是给定情景的算术门槛，不产生买卖信号。`;renderV6Scenario(x,r);$('scenarioTarget').textContent='US$'+fmt(r.target);svgPlot($('scenarioChart'),[{points:r.integer.path.map(p=>({x:p.year/x.years,y:p.wealth_sgd})),color:'#206f5d'},{points:r.fractional.path.map(p=>({x:p.year/x.years,y:p.wealth_sgd})),color:'#5a7f9f'}],{labels:[[0,'现在'],[1,x.years+'年后']],baseline:x.budget});$('scenarioResults').innerHTML=[['整股',r.integer],['碎股',r.fractional]].map(([label,v])=>`<tr><td>${label}</td><td class="num">${fmt(v.units,3)}</td><td class="num">${fmt(v.cash_usd)}</td><td class="num">${money(v.terminal_sgd)}</td><td class="num">${pct(v.annualized)}</td><td class="num">手工路径，非风险估计</td></tr>`).join('');updateScenarioBasis(x);if(settings.persist!==false)persistScenario(x);scenarioStatus(settings.message??'')}catch(e){clearScenarioDescriptions();scenarioLast=null;window.lastScenarioSite=null;$('scenarioError').classList.remove('hidden');$('scenarioError').textContent=e.message;$('scenarioMax').textContent='—';$('scenarioGap').textContent='缺少已声明的盈利/期间假设，未生成条件买价。';if($('sensitivityRows'))$('sensitivityRows').innerHTML='';if($('sensitivityHead'))$('sensitivityHead').innerHTML='';$('scenarioTarget').textContent='—';$('scenarioResults').innerHTML='';$('scenarioChart').innerHTML='';if($('reverseStress'))$('reverseStress').textContent='参数未就绪，未计算反向门槛。';scenarioStatus('当前输入无效，未覆盖上次保存的有效情景。')}}
function scenarioSymbol(){clearScenarioDescriptions();scenarioAsset=$('scenarioAsset').value;const saved=scenarioRecords[scenarioAsset];if(saved){scenarioSource=JSON.parse(JSON.stringify(saved.source_basis));const x={...saved.inputs};if(scenarioSource.entry_mode==='latest_close'){const latest=rowsFor(scenarioAsset).at(-1);x.entry=Number(latest[1].toFixed(4));scenarioSource.entry_date=latest[0]}putScenario(x);calcScenario({message:scenarioSource.entry_mode==='latest_close'?'已恢复情景；拟买价跟随最新历史收盘，估值锚与假设保留。':'已恢复该标的上次有效情景；保留手动拟买价、估值锚与假设。'})}else{scenarioSource=sourceBasis(scenarioAsset);putScenario(referenceInputs(scenarioAsset));calcScenario({message:'已载入参考起点；有效修改会自动保存在本浏览器。'})}}
if($('scenarioInputs')){options($('scenarioAsset'));$('scenarioAsset').value=scenarioSelected;$('scenarioInputs').innerHTML=fields.map(([id,label,value])=>`<div class="field"><label for="s_${id}">${label}</label><input id="s_${id}" type="number" step="any" value="${value===null?'':Number(value.toFixed(6))}"></div>`).join('');$('scenarioInputs').insertAdjacentHTML('beforeend',META_FIELDS.map(k=>`<div class="field"><label for="s_${k}">${({valuation_date:'估值日',base_start:'基准盈利窗口开始',base_end:'基准盈利窗口末日（不含）',terminal_start:'退出盈利窗口开始',terminal_end:'退出盈利窗口末日（不含）',source_note:'EPS来源/假设与口径说明'})[k]}</label><input id="s_${k}" type="${k==='source_note'?'text':'date'}"></div>`).join(''));[...fields.map(([id])=>id),...META_FIELDS].forEach(id=>$('s_'+id).oninput=calcScenario);$('feeTreatment').onchange=calcScenario;$('earningsBasis').onchange=calcScenario;$('scenarioAsset').onchange=scenarioSymbol;document.querySelectorAll('[data-case]').forEach(b=>b.onclick=()=>{const a=presets[b.dataset.case];['g1','growth','multiple'].forEach((k,i)=>$('s_'+k).value=a[i]);calcScenario({message:'已应用演示压力情景，并自动保存；不是市场一致预期。'})});$('exportScenarioSite').onclick=()=>{if(!scenarioLast){scenarioStatus('请先修正无效输入，再导出。');return}const record=persistScenario(scenarioLast.inputs);download(scenarioAsset+'_情景.json',{...record,result:scenarioLast.result,exported_at:new Date().toISOString(),type:'manual_scenario_not_forecast'});scenarioStatus('已导出含输入、来源和算法版本的情景；可在另一设备导入并重新计算。')};$('resetScenarioReference').onclick=()=>{const x=readScenario(),reference=referenceInputs(scenarioAsset);for(const k of ['reference','g1','growth','multiple','hurdle','base_eps'])x[k]=reference[k];scenarioSource={...sourceBasis(scenarioAsset),entry_mode:scenarioSource?.entry_mode??'manual'};putScenario(x);calcScenario({message:'已主动恢复当前参考增长、倍数和估值锚；拟买价、资金、费用及FX等个人输入保留。'})};$('latestScenarioEntry').onclick=()=>{scenarioSource.entry_mode='latest_close';scenarioSource.entry_date=rowsFor(scenarioAsset).at(-1)[0];$('s_entry').value=Number(rowsFor(scenarioAsset).at(-1)[1].toFixed(4));calcScenario({message:'仅将拟买价更新为所选历史最后收盘，原估值锚与盈利假设保留。'})};$('importScenarioSite').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>2e6)throw Error('情景文件请限制在2MB以内');const record=validateScenarioRecord(JSON.parse(await file.text()),{allowLegacy:true});scenarioAsset=record.symbol;$('scenarioAsset').value=scenarioAsset;scenarioSource={...record.source_basis,origin:'imported_unverified',entry_mode:'manual'};putScenario(record.inputs);calcScenario({message:'已导入参数并重新计算。文件内结果未被采用，来源元数据未经独立核实。'})}catch(err){scenarioStatus('未导入：'+err.message+'；原有效情景保留。')}finally{e.target.value=''}};scenarioSymbol()}
window.ScenarioPersistence={schema:SCENARIO_SCHEMA,storage_key:SCENARIO_KEY,validateRecord:validateScenarioRecord,referenceInputs,sourceBasis};
if($('robustSite')){$('robustSite').innerHTML=DATA.robustness.filter(r=>r.scope==='current_bin_only').map(r=>`<tr><td>${r.symbol}</td><td class="num">${money(r.min_mean_sgd)} 至 ${money(r.max_mean_sgd)}</td><td>${r.sign_changes_across_variants?'方向翻转，依赖样本选择':'本组未翻转，仍非稳定预测'}<br><small>每组${r.min_cohort_n}–${r.max_cohort_n}个起点</small></td></tr>`).join('');$('coverageSite').innerHTML=DATA.bridge.fund_scenarios.filter(r=>r.scenario_id==='unchanged').map(r=>`<tr><td>${r.fund}</td><td class="num">${pct(r.covered_weight)}</td><td>残差${pct(r.uncovered_weight)}，不默认为已验证的盈利或零回报</td></tr>`).join('');$('evidenceFreshness').textContent=`冻结价格/历史主分析截至${DATA.price_cutoff}；最近分析复核记录${DATA.evidence?.last_review?.recorded_at??'尚无'}。各公司事实保留各自来源日期；预测可得日未完全核实；网页构建时间${DATA.built_at}不代表所有事实已更新。`;$('sourceList').innerHTML=DATA.evidence.snapshot.sources.map(s=>`<p><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a><br>${esc(s.published??'见原页')} · 取回 ${esc(s.retrieved_at??'见原记录')}</p>`).join('');$('manifestList').innerHTML=DATA.manifest.map(s=>`<p><b>${s.symbol}</b> · ${s.start}—${s.end} · ${s.rows}行<br><span style="word-break:break-all">SHA256 ${s.raw_sha256}</span></p>`).join('')}
let resizeTimer;window.addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if($('historyChart'))renderChart();if($('scenarioChart'))calcScenario()},100)});

function renderMonitor(){if(!$('monitorStatus'))return;const m=DATA.monitor;if(!m){$('monitorStatus').textContent='尚未配置持续任务。';return}const never=!m.last_success_at,stale=m.stale_after&&Date.parse(m.stale_after)<Date.now();$('monitorStatus').textContent=`每${m.cadence_minutes}分钟的本地任务已配置；电脑和桌面应用须保持运行。${never?'尚未完成首次成功市场内容扫描。':stale?'上次完整扫描已超过有效期。':'最近完整内容扫描：'+m.last_success_at} 最近内容检查：${m.last_market_check_at??'尚未执行'}（${m.runtime_status==='degraded'?'部分完成，存在来源缺口':m.runtime_status??'未知'}）。 最近访问探测：${m.last_source_probe_at??'未执行'}（可访问性检查不等于新闻核实）。`;$('monitorStatus').className=never||stale?'notice error':'notice good';if(m.automation_status==='PAUSED'){$('monitorStatus').textContent='定时任务已暂停。以下为上次手动检查的结果，不会周期自动更新。';$('monitorStatus').className='notice';}$('monitorUpdates').innerHTML=(m.failed_sources?.length?'<p><b>本轮未能完整审阅的来源：</b>'+m.failed_sources.map(x=>esc(x.name)+' '+esc(x.http_status??x.error)).join('；')+'。其他浏览渠道可能仍可用，不能将失败解释为没有新消息。</p>':'')+(m.last_market_review_summary?'<details><summary>本次检查覆盖与限制</summary><p>'+esc(m.last_market_review_summary)+'</p></details>':'')+(m.confirmed_updates??[]).map(x=>`<p><a href="${esc(x.url)}" target="_blank" rel="noopener">${esc(x.title)}</a><br>发布日期 ${esc(x.published_date)} · 记录于${esc(x.recorded_at)} · 已有审阅台账记录</p>`).join('')}
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

## v8_app.js
SHA256 de6c80445ef2837709804b3530f0fa44775d3e83a5a8f2eb6a1bd86aa0d3329e
```
/* V8 absolute earnings/valuation workbench. All forecasts remain declared assumptions. */
(()=>{'use strict';const M=window.ResearchMath,D=window.RESEARCH_DATA,$=id=>document.getElementById(id);if(!$('scenarioInputs'))return;
const names=['budget','reference','entry','years','g1','growth','multiple','hurdle','fx0','fx1','bps','fee','fx_bps','cash_rate','shock','fund_fee','dividend','withholding','base_eps','valuation_date','base_start','base_end','terminal_start','terminal_end','source_note'];const percent=['g1','growth','hurdle','cash_rate','shock','fund_fee','withholding'];
const own=[['terminal_eps','退出EPS：USD/同一基金份额'],['terminal_pe','退出市盈率：独立绝对倍数'],['price_date','参考价格日期（须与估值日对齐）']];
const panel=document.createElement('section');panel.className='sheet';panel.id='absolutePanel';panel.style.overflowWrap='anywhere';panel.style.minWidth='0';panel.innerHTML='<h2>V8：独立盈利与绝对估值</h2><p>先填写上方资金、费用、日期、基准EPS及目标回报。这里的退出EPS和绝对倍数决定终值；不依赖相对情景的增长率或倍数比。所有前瞻输入默认空白，完整基金数据仍未核实。</p><div class="formgrid">'+own.map(([id,label])=>`<div class="field"><label for="a_${id}">${label}</label><input id="a_${id}" type="${id==='price_date'?'date':'number'}" step="any"></div>`).join('')+'</div><p id="absoluteStatus" class="notice"></p><p id="absoluteValue" class="keyresult"></p><p id="absoluteExecution" class="note"></p><button class="button secondary" id="exportAbsolute">导出绝对估值情景</button> <label class="button secondary">导入V8情景<input type="file" id="importAbsolute" accept=".json" hidden></label><p class="tiny">按标的保存在当前浏览器。导入后重算，不信任文件中的旧结果。买价上限按碎股完全投入推导；整股执行另列实际回报。</p><details><summary>经营路径：收入 → 利润 → 税后EPS</summary><p>全部使用同一年度、同一基础股本的USD单位。不得将季度收入乘4作为已核实全年预测；基金/公司单位不能混用。股数因子是各年相对基准股数，如1.02,1.04,1.06。</p><div class="formgrid">'+[['revenue','基准年收入/基准股数 USD'],['revenues','逐年收入增长%（逗号分隔）'],['margins','逐年经营利润率%'],['shares','逐年股数因子'],['interest','年利息/基准股数 USD'],['tax','税率%'],['other','年经常性税前其他收益/基准股数 USD']].map(([id,label])=>`<div class="field"><label for="b_${id}">${label}</label><input id="b_${id}"></div>`).join('')+'</div><button class="button secondary" id="bridgeApply">推导并采用退出EPS</button><p id="bridgeStatus"></p></details><details><summary>利率与风险溢价 → 稳态退出倍数（可选假设）</summary><p>Gordon稳态分红模型：k=名义无风险利率+股票风险溢价，NTM P/E=payout/(k−g)，TTM P/E=payout×(1+g)/(k−g)。只适合稳定正盈利、持续分配情景；不能用实际利率替代名义利率，不适用于未正常化周期利润。四项均为手填假设，未从新闻自动填入。</p><div class="formgrid">'+[['rf','名义无风险利率%'],['erp','股票风险溢价%'],['g','长期名义EPS增速%'],['payout','分配率%']].map(([id,label])=>`<div class="field"><label for="m_${id}">${label}</label><input id="m_${id}" type="number" step="any"></div>`).join('')+'</div><button class="button secondary" id="multipleApply">推导并采用退出倍数</button><p id="multipleStatus"></p></details>';
const relativeInputs=document.createElement('details');relativeInputs.style.gridColumn='1 / -1';relativeInputs.innerHTML='<summary>可选：相对价格敏感性的增长与倍数假设</summary><div class="formgrid"></div>';$('scenarioInputs').append(relativeInputs);for(const id of ['g1','growth','multiple'])relativeInputs.querySelector('div').append($('s_'+id).closest('.field'));$('scenarioInputs').closest('section').after(panel);let last=null,restoring=false;const key='etf_absolute_v8',recordIds=[...own.map(x=>'a_'+x[0]),...['revenue','revenues','margins','shares','interest','tax','other'].map(x=>'b_'+x),...['rf','erp','g','payout'].map(x=>'m_'+x)];
function base(){const x={};for(const k of names){const v=$('s_'+k)?.value??'';x[k]=['valuation_date','base_start','base_end','terminal_start','terminal_end','source_note'].includes(k)?v:v.trim()===''?null:Number(v);if(percent.includes(k)&&x[k]!==null)x[k]/=100}return {...x,fee_mode:$('feeTreatment').value,valuation_basis:$('earningsBasis').value,context_mode:'historical',price_date:$('a_price_date').value,evidence_date:null,terminal_eps:Number($('a_terminal_eps').value)||null,terminal_pe:Number($('a_terminal_pe').value)||null}}
function save(){if(restoring)return;try{const all=JSON.parse(localStorage.getItem(key)||'{}');all[$('scenarioAsset').value]={...Object.fromEntries(recordIds.map(id=>[id,$(id).value])),common:Object.fromEntries([...names.map(k=>'s_'+k),'earningsBasis','feeTreatment'].map(id=>[id,$(id)?.value??'']))};localStorage.setItem(key,JSON.stringify(all))}catch{$('absoluteStatus').textContent+=' 浏览器保存失败，请导出。'}}
function restore(){restoring=true;recordIds.forEach(id=>$(id).value='');try{const all=JSON.parse(localStorage.getItem(key)||'{}'),s=all[$('scenarioAsset').value]??{};for(const id of recordIds)if(typeof s[id]==='string')$(id).value=s[id];for(const id of [...names.map(k=>'s_'+k),'earningsBasis','feeTreatment'])if(typeof s.common?.[id]==='string')$(id).value=s.common[id]}catch{}if(!$('a_price_date').value)$('a_price_date').value=D.series[$('scenarioAsset').value].at(-1)[0];restoring=false;calc()}
function calc(){last=null;$('absoluteValue').textContent='—';$('absoluteExecution').textContent='';try{const x=base(),r=M.scenarioAbsolute(x);last={schema:'etf.absolute.v8',symbol:$('scenarioAsset').value,inputs:x,result:r};$('absoluteStatus').textContent='条件算术完成；预测来源与完整基金三年盈利未验证，不是入场信号。';$('absoluteValue').textContent=`退出价 US$${r.target.toFixed(2)} · 碎股条件买价上限 ${r.maxEntry===null?'无股票仓位':'US$'+r.maxEntry.toFixed(2)}`;$('absoluteExecution').textContent=`拟买价下：碎股年化 ${(r.fractional.annualized*100).toFixed(2)}%；整股年化 ${r.integer.annualized===null?'无定义':(r.integer.annualized*100).toFixed(2)+'%'}；整股余款US$${r.integer.cash_usd.toFixed(2)}。未核实预测可得日；所有日期是声明，未构成点时验证。`}catch(e){$('absoluteStatus').textContent=e.message}save();window.lastAbsoluteScenario=last}
document.addEventListener('input',e=>{if(e.target.closest('#absolutePanel')||e.target.id.startsWith('s_'))calc()});document.addEventListener('change',e=>{if(e.target.id==='scenarioAsset')restore();else if(['earningsBasis','feeTreatment'].includes(e.target.id))calc()});
const csv=(id,scale=1)=>{const v=$(id).value.trim();if(!v)throw Error('经营路径字段不能留空');return v.split(',').map(s=>{if(!s.trim()||!Number.isFinite(Number(s)))throw Error('逐年路径格式无效');return Number(s)/scale})};const number=id=>{if(!$(id).value.trim()||!Number.isFinite(Number($(id).value)))throw Error('请完整填写数值假设');return Number($(id).value)};
$('bridgeApply').onclick=()=>{try{const growth=csv('b_revenues',100);if(growth.length!==Number($('s_years').value))throw Error('经营路径年数必须等于持有年数');const r=M.operatingBridgeV8({R0:number('b_revenue'),revenue_growth_path:growth,operating_margin_path:csv('b_margins',100),share_factor_path:csv('b_shares'),interest_per_share:number('b_interest'),tax_rate:number('b_tax')/100,other_recurring_per_share:number('b_other')});if(!(r.valuation_eps>0))throw Error('亏损或负EPS不适用PE估值');$('a_terminal_eps').value=r.terminal_eps;$('bridgeStatus').textContent='已采用条件经营路径推导值；不是完整ETF预测。'+r.years.map((y,i)=>'第'+(i+1)+'年 EPS '+Number(y.eps_usd).toFixed(4)+' USD').join('；');calc()}catch(e){$('a_terminal_eps').value='';$('bridgeStatus').textContent=e.message;calc()}};
$('multipleApply').onclick=()=>{try{const k=(number('m_rf')+number('m_erp'))/100,g=number('m_g')/100,p=number('m_payout')/100,basis=$('earningsBasis').value;if(!['ttm','ntm'].includes(basis)||k<=g||k<=0||g<=-1||p<=0||p>1)throw Error('需要TTM/NTM、k>g、正折现率及0–100%分配率');const pe=p*(basis==='ttm'?1+g:1)/(k-g);if(!Number.isFinite(pe)||pe<=0)throw Error('倍数无效');$('a_terminal_pe').value=pe;$('multipleStatus').textContent=`采用稳态情景P/E ${pe.toFixed(2)}；分配率、增长与资本回报是否可持续仍须验证。`;calc()}catch(e){$('a_terminal_pe').value='';$('multipleStatus').textContent=e.message;calc()}};
$('exportAbsolute').onclick=()=>{if(!last){$('absoluteStatus').textContent+=' 先完成有效输入再导出。';return}const blob=new Blob([JSON.stringify({...last,extras:Object.fromEntries(recordIds.map(id=>[id,$(id).value]))},null,2)],{type:'application/json'}),u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download=last.symbol+'_absolute_v8.json';a.click();URL.revokeObjectURL(u)};
$('importAbsolute').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>2e6)throw Error('文件过大');const v=JSON.parse(await f.text());if(v.schema!=='etf.absolute.v8'||!D.series[v.symbol])throw Error('不是支持的V8绝对情景');M.scenarioAbsolute(v.inputs);$('scenarioAsset').value=v.symbol;$('scenarioAsset').dispatchEvent(new Event('change',{bubbles:true}));for(const k of names){const el=$('s_'+k);if(el&&k in v.inputs)el.value=v.inputs[k]==null?'':percent.includes(k)?v.inputs[k]*100:v.inputs[k]}$('earningsBasis').value=v.inputs.valuation_basis;$('feeTreatment').value=v.inputs.fee_mode;for(const id of recordIds)if(typeof v.extras?.[id]==='string')$(id).value=v.extras[id];$('a_price_date').value=v.inputs.price_date;$('a_terminal_eps').value=v.inputs.terminal_eps;$('a_terminal_pe').value=v.inputs.terminal_pe;calc();if(last===null)throw Error('界面重新计算失败')}catch(err){$('absoluteStatus').textContent='未导入：'+err.message}finally{e.target.value=''}};restore();
})();

```

## reproduce.py
SHA256 389f292bbedb6a5699e6cd87f15de35a2c9348a0b8e3c9011787e6a402b28c60
```
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

## core_tests.mjs
SHA256 b1be1c12c522335e5fa57bae138587e46b23a1a3f0e63fdb7d8ebd1222534ac2
```
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createContext,runInContext} from 'node:vm';
import {resolve} from 'node:path';

const context=createContext({window:{ResearchMath:{}}});
const coreSource=readFileSync(resolve('sites/etf-research/src/v6_calc.js'),'utf8');
runInContext(coreSource,context);
const M=context.window.ResearchMath,checks=[];
function test(name,fn){fn();checks.push(name)}
function near(a,b,tolerance=1e-10){assert.ok(Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a-b)<=tolerance*Math.max(1,Math.abs(b)),`${a} != ${b}`)}
function fails(fn){assert.throws(fn)}
const base={budget:3000,entry:100,reference:100,years:3,fx0:1.28,fx1:1.28,bps:5,fee:1,fx_bps:10,cash_rate:0,shock:-.3,dividend:0,withholding:null,fund_fee:.0035,fee_mode:'deduct',valuation_basis:'ntm',valuation_date:'2026-10-26',price_date:'2026-10-26',context_mode:'historical',evidence_date:null,base_start:'2026-10-26',base_end:'2027-10-26',terminal_start:'2029-10-26',terminal_end:'2030-10-26',base_eps:5,terminal_eps:8,terminal_pe:20,hurdle:.1,source_note:'人工输入的独立退出盈利和估值情景，不构造市场事实'};
test('Absolute exit price equals independent EPS times PE',()=>{const r=M.scenarioAbsolute(base);near(r.gross_target,160);near(r.target,160*.9965**3);assert.equal(r.valuation_model,'absolute_terminal_eps_pe')});
test('Changing terminal EPS independently changes target and entry bound',()=>{const a=M.scenarioAbsolute(base),b=M.scenarioAbsolute({...base,terminal_eps:16});near(b.gross_target,2*a.gross_target);near(b.maxEntry,2*a.maxEntry);assert.equal(b.terminal_pe,a.terminal_pe)});
test('Changing reference price does not rederive exit PE or terminal price',()=>{const a=M.scenarioAbsolute(base),b=M.scenarioAbsolute({...base,reference:200});near(b.gross_target,a.gross_target);near(b.maxEntry,a.maxEntry);near(b.base_pe,2*a.base_pe);assert.equal(b.terminal_pe,20)});
test('Changing base EPS does not cancel an independent terminal EPS input',()=>{const r=M.scenarioAbsolute({...base,base_eps:10});near(r.gross_target,160);near(r.earnings_factor,.8);near(r.base_pe,10)});
test('Absolute mode ignores invalid legacy relative-growth inputs',()=>{const r=M.scenarioAbsolute({...base,g1:NaN,growth:NaN,multiple:NaN});near(r.gross_target,160)});
test('Missing fund fee cannot silently become zero',()=>{const x={...base};delete x.fund_fee;fails(()=>M.scenarioAbsolute(x));fails(()=>M.scenarioV6({...x,g1:.2,growth:.1,multiple:.9}))});
test('Prototype fund fee is not an explicitly supplied input',()=>{const x=Object.assign(Object.create({fund_fee:.0035}),base);delete x.fund_fee;fails(()=>M.scenarioAbsolute(x))});
test('Explicit zero fee is allowed as an assumption',()=>{near(M.scenarioAbsolute({...base,fund_fee:0}).target,160)});
test('Embedded expense mode does not deduct fund fee twice',()=>{near(M.scenarioAbsolute({...base,fee_mode:'embedded'}).target,160)});
test('Current mode requires same price and valuation date',()=>{fails(()=>M.scenarioAbsolute({...base,context_mode:'current',price_date:'2026-10-25'}));assert.equal(M.scenarioAbsolute({...base,context_mode:'current'}).date_alignment.price_age_days,0)});
test('Historical mode permits at most seven prior calendar days',()=>{const x={...base,valuation_date:'2026-11-02',base_start:'2026-11-02',base_end:'2027-11-02',terminal_start:'2029-11-02',terminal_end:'2030-11-02'};assert.equal(M.scenarioAbsolute(x).date_alignment.price_age_days,7);fails(()=>M.scenarioAbsolute({...x,price_date:'2026-10-25'}))});
test('Future or missing price dates are rejected',()=>{fails(()=>M.scenarioAbsolute({...base,price_date:'2026-10-27'}));const x={...base};delete x.price_date;fails(()=>M.scenarioAbsolute(x))});
test('Missing evidence date stays unverified rather than inferred from price date',()=>{const r=M.scenarioAbsolute(base);assert.equal(r.evidence_date,null);assert.equal(r.evidence_status,'unverified')});
test('Explicit future evidence date is rejected',()=>{fails(()=>M.scenarioAbsolute({...base,evidence_date:'2026-10-27'}))});
test('A declared past date is not mislabeled independently verified',()=>{const r=M.scenarioAbsolute({...base,evidence_date:'2026-10-25'});assert.equal(r.evidence_status,'declared_date_not_independently_verified')});
test('Wrong earnings windows remain blocked',()=>{fails(()=>M.scenarioAbsolute({...base,terminal_end:'2030-10-27'}));fails(()=>M.scenarioAbsolute({...base,base_start:'2026-10-25'}))});
test('Nonpositive terminal EPS cannot be PE-valued',()=>{for(const terminal_eps of[0,-1])fails(()=>M.scenarioAbsolute({...base,terminal_eps}))});
test('Derived PE and target overflow cannot leak Infinity',()=>{fails(()=>M.scenarioAbsolute({...base,base_eps:Number.MIN_VALUE}));fails(()=>M.scenarioAbsolute({...base,terminal_eps:Number.MAX_VALUE}));fails(()=>M.scenarioV6({...base,g1:1e308,growth:1e308,multiple:1}))});
test('Maximum fractional entry solves the same cash-flow hurdle with fees and dividends',()=>{const x={...base,dividend:2,withholding:.3,cash_rate:.02,fx1:1.33};const r=M.scenarioAbsolute(x),q=M.scenarioAbsolute({...x,entry:r.maxEntry});near(q.fractional.annualized,.1)});
test('Required terminal EPS and PE each solve the hurdle independently',()=>{const x={...base,dividend:2,withholding:.3,cash_rate:.02};const r=M.scenarioAbsolute(x);near(M.scenarioAbsolute({...x,terminal_eps:r.reverse.required_terminal_eps}).fractional.annualized,.1);near(M.scenarioAbsolute({...x,terminal_pe:r.reverse.required_terminal_pe}).fractional.annualized,.1)});
test('Legacy relative API is retained and explicitly versioned as sensitivity',()=>{const r=M.scenarioV6({...base,g1:.2,growth:.1,multiple:.9});near(r.gross_target,130.68);assert.equal(r.valuation_model,'relative_sensitivity_compatibility');assert.match(r.algorithm_version,/v8/)});
test('Cash remainder and distributions remain USD and include anniversary timing',()=>{const r=M.executionV6({budget:1000,entry:100,target:100,years:3,fx0:1,fx1:1,bps:0,fee:0,fx_bps:0,cash_rate:.1,shock:-.3,dividend:2,withholding:.25});near(r.terminal_sgd,1049.65);assert.equal(r.cash_currency,'USD')});
test('Zero stock units charge no stock fees and preserve cash interest',()=>{const r=M.executionV6({budget:1000,entry:100,target:120,years:3,fx0:2,fx1:2,bps:0,fee:501,fx_bps:0,cash_rate:.05,shock:-.3,dividend:0,withholding:null},true);assert.equal(r.units,0);near(r.terminal_sgd,1157.625)});

const operating={R0:100,revenue_growth_path:[.1,.2],operating_margin_path:[.2,.25],interest_per_share:2,tax_rate:.2,other_recurring_per_share:1,share_factor_path:[1.1,1.2]};
test('Operating bridge derives EPS from revenue margin interest tax and cumulative dilution',()=>{const r=M.operatingBridgeV8(operating);near(r.years[0].eps_usd,16.8/1.1);near(r.terminal_eps,25.6/1.2);near(r.valuation_eps,25.6/1.2);assert.equal(r.eps_type,'conditional_common_eps_proxy')});
test('Negative and zero EPS remain unavailable for PE without fabricated zero',()=>{const r=M.operatingBridgeV8({...operating,revenue_growth_path:[0],operating_margin_path:[-.1],share_factor_path:[1],interest_per_share:2,other_recurring_per_share:0});near(r.terminal_eps,-12);assert.equal(r.valuation_eps,null);assert.equal(r.pe_valuation_available,false);assert.equal(r.years[0].tax_per_base_share_usd,0)});
test('Intermediate loss is preserved even if terminal earnings recover',()=>{const r=M.operatingBridgeV8({...operating,revenue_growth_path:[0,0],operating_margin_path:[-.1,.2],share_factor_path:[1,1],interest_per_share:0,other_recurring_per_share:0});near(r.years[0].eps_usd,-10);near(r.terminal_eps,16);assert.equal(r.years[0].pe_valuation_available,false);assert.equal(r.pe_valuation_available,true)});
test('Operating inputs are explicit and mismatched paths rejected',()=>{const x={...operating};delete x.interest_per_share;fails(()=>M.operatingBridgeV8(x));fails(()=>M.operatingBridgeV8({...operating,share_factor_path:[1]}));fails(()=>M.operatingBridgeV8({...operating,share_factor_path:[0,1]}))});
test('Operating revenue or EPS overflow cannot produce output',()=>{fails(()=>M.operatingBridgeV8({...operating,R0:Number.MAX_VALUE}));fails(()=>M.operatingBridgeV8({...operating,share_factor_path:[Number.MIN_VALUE,1]}))});
test('Normalized earnings must be annualized at the valuation date',()=>{fails(()=>M.scenarioAbsolute({...base,valuation_basis:'normalized',base_start:'2050-01-01',base_end:'2051-01-01',terminal_start:'2053-01-01',terminal_end:'2054-01-01'}));const r=M.scenarioAbsolute({...base,valuation_basis:'normalized',base_start:'2025-10-26',base_end:'2026-10-26',terminal_start:'2028-10-26',terminal_end:'2029-10-26'});assert.ok(r.target>0)});
const report={status:'passed',checks:checks.length,version:M.SCENARIO_VERSION,executed_at:new Date().toISOString(),core_file:'sites/etf-research/src/v6_calc.js',core_sha256:createHash('sha256').update(coreSource).digest('hex'),checks_run:checks};
mkdirSync('v8',{recursive:true});writeFileSync('v8/core_test_results.json',JSON.stringify(report,null,2));
console.log(JSON.stringify(report));

```

## ui_tests.mjs
SHA256 fd33d751c60084dd42027b12108a105781dcdee4c040680acda626cf6b688092
```
/* Browser regression for UI fixes. Serves current src JS over existing built HTML. */
import{chromium}from'playwright';import fs from'node:fs';import http from'node:http';import path from'node:path';
const root=path.resolve('sites/etf-research/dist'),src=path.resolve('sites/etf-research/src'),checks=[],errors=[];
function check(name,ok){if(!ok)throw Error(name);checks.push(name)}
const server=http.createServer((req,res)=>{try{const name=new URL(req.url,'http://local').pathname;let p=path.join(root,name==='/'?'index.html':name);if(['/app.js','/model.js','/v6_calc.js','/v8_app.js'].includes(name))p=path.join(src,name);res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.css')?'text/css':p.endsWith('.json')?'application/json':'text/html');res.end(fs.readFileSync(p))}catch{res.statusCode=404;res.end()}});await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'}),context=await browser.newContext();await context.addInitScript(()=>{Date.now=()=>Date.parse('2026-10-28T12:00:00Z')});const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));const base='http://127.0.0.1:'+server.address().port;
try{await page.goto(base+'/scenarios.html');const values={budget:3000,reference:100,entry:100,years:3,g1:10,growth:10,multiple:.9,hurdle:10,fx0:1.3,fx1:1.3,bps:5,fee:1,fx_bps:10,cash_rate:0,shock:-30,fund_fee:.15,dividend:0,withholding:'',base_eps:5,valuation_date:'2026-10-26',base_start:'2026-10-26',base_end:'2027-10-26',terminal_start:'2029-10-26',terminal_end:'2030-10-26',source_note:'Synthetic illustration for UI regression only'};
await page.locator('#s_g1').evaluate(el=>{const section=el.closest('details');if(section)section.open=true});for(const[k,v]of Object.entries(values))await page.locator('#s_'+k).fill(String(v));await page.locator('#earningsBasis').selectOption('ntm');const relative=page.locator('details').filter({has:page.locator('#scenarioMax')}).first();if(await relative.count())await relative.locator(':scope > summary').click();check('valid declared example produces a price: '+await page.locator('#scenarioError').innerText(),(await page.locator('#scenarioMax').innerText()).startsWith('US$'));
const api=await page.evaluate(()=>({version:ResearchMath.SCENARIO_VERSION,inputs:lastScenarioSite.inputs}));check('valid input clears stale error text',await page.locator('#scenarioError').textContent()==='');check('historical price date is attached',api.inputs.price_date==='2026-10-26'&&api.inputs.context_mode==='historical');check('forecast availability is explicitly unknown',api.inputs.evidence_date===null&&api.inputs.evidence_date_status==='unverified');
check('new context fields survive record validation',await page.evaluate(()=>{const s=JSON.parse(localStorage.getItem(ScenarioPersistence.storage_key));const r=ScenarioPersistence.validateRecord(s.records.QQQM);return r.inputs.price_date==='2026-10-26'&&r.inputs.evidence_date_status==='unverified'}));
await page.locator('#s_base_eps').fill('');check('blank EPS clears price',await page.locator('#scenarioMax').innerText()==='—');for(const id of ['valuationDefinition','fundCostBasis','scenarioBasis','scenarioInputPosture'])check('blank EPS clears '+id,await page.locator('#'+id).innerText()==='');
await page.locator('#scenarioAsset').selectOption('SMH');check('fresh SMH uses current fee input',Math.abs(Number(await page.locator('#s_fund_fee').inputValue())-.35)<1e-10);for(const id of ['valuationDefinition','fundCostBasis','scenarioBasis','scenarioInputPosture'])check('switch to fresh asset clears '+id,await page.locator('#'+id).innerText()==='');
await page.evaluate(()=>localStorage.setItem('etf_research_local_rows_v1',JSON.stringify({QQQM:{rows:[['2026-10-27',100]],base_hash:RESEARCH_DATA.manifest.find(x=>x.symbol==='QQQM').raw_sha256,imported_at:new Date().toISOString()}})));
await page.goto(base+'/etf-overview.html');const home=await page.evaluate(()=>({text:document.getElementById('homeView').innerText,expected:RESEARCH_DATA.evidence.last_review.payload.conclusion,reviewDate:document.getElementById('reviewDate').innerText,recorded:RESEARCH_DATA.evidence.last_review.recorded_at,card:document.querySelector('#homeFunds a').innerText,second:document.querySelectorAll('#homeFunds a')[1].innerText}));
check('home displays latest reviewed conclusion',home.text===home.expected||(home.text.startsWith('【已过期或待复核的历史记录】')&&home.text.includes(home.expected)));check('home review timestamp is sourced',home.reviewDate.includes(home.recorded));check('local card shows actual price date',home.card.includes('2026-10-27'));check('local card labels unverified local inputs',home.card.includes('本地输入')&&home.card.includes('未独立核实'));check('unmodified card retains frozen source and date',home.second.includes('冻结行情快照')&&home.second.includes('2026-10-26'));
const expired=await browser.newContext();await expired.addInitScript(()=>{Date.now=()=>Date.parse('2026-10-30T12:00:00Z')});const old=await expired.newPage();old.on('pageerror',e=>errors.push(e.message));await old.goto(base+'/etf-overview.html');check('expired conclusion explicitly marked historical',(await old.locator('#homeView').innerText()).startsWith('【已过期或待复核的历史记录】'));check('expired status is visible',await old.locator('#homeStatus').innerText()==='历史结论待复核');await expired.close();
check('no JavaScript runtime errors',errors.length===0);fs.mkdirSync('v8',{recursive:true});fs.writeFileSync('v8/ui_test_results.json',JSON.stringify({run_at:new Date().toISOString(),core_algorithm_version:api.version,tests:checks.length,checks,scope:'Current src JS served with built HTML. Synthetic numbers only; no production changes or external market-data verification.'},null,2));console.log(JSON.stringify({passed:checks.length,core:api.version}));
}finally{await browser.close();await new Promise(r=>server.close(r))}

```

## integration_tests.mjs
SHA256 a2223fd13bcbc3b85ebb53966acc45d43d43633f82dc0ea3a8a062bb9f898371
```
import{chromium}from'playwright';import fs from'node:fs';import http from'node:http';import path from'node:path';
const root=path.resolve('sites/etf-research/dist'),checks=[],server=http.createServer((req,res)=>{try{const n=new URL(req.url,'http://local').pathname,p=path.join(root,n==='/'?'index.html':n);res.setHeader('Content-Type',p.endsWith('.js')?'text/javascript':p.endsWith('.css')?'text/css':'text/html');res.end(fs.readFileSync(p))}catch{res.statusCode=404;res.end()}});await new Promise(r=>server.listen(0,'127.0.0.1',r));const b=await chromium.launch({headless:true,executablePath:'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'});const p=await b.newPage({viewport:{width:1280,height:1000}}),errors=[];p.on('pageerror',e=>errors.push(e.message));const ok=(n,v)=>{if(!v)throw Error(n);checks.push(n)};
try{await p.goto('http://127.0.0.1:'+server.address().port+'/scenarios.html');ok('absolute outputs blank initially',await p.locator('#absoluteValue').innerText()==='—');const fields={budget:3000,reference:100,entry:100,years:3,hurdle:10,fx0:1.3,fx1:1.3,bps:5,fee:1,fx_bps:10,cash_rate:0,shock:-30,fund_fee:.35,dividend:0,base_eps:5,valuation_date:'2026-10-26',base_start:'2026-10-26',base_end:'2027-10-26',terminal_start:'2029-10-26',terminal_end:'2030-10-26',source_note:'Synthetic V8 integration scenario'};for(const[k,v]of Object.entries(fields))await p.locator('#s_'+k).fill(String(v));await p.locator('#earningsBasis').selectOption('ntm');await p.locator('#a_terminal_eps').fill('7');await p.locator('#a_terminal_pe').fill('18');let first=await p.evaluate(()=>lastAbsoluteScenario);ok('absolute calculation works with relative growth fields blank',!!first&&await p.locator('#s_growth').inputValue()==='');await p.locator('#a_terminal_eps').fill('14');const twice=await p.evaluate(()=>lastAbsoluteScenario);ok('independent exit EPS doubles gross value',Math.abs(twice.result.gross_target/first.result.gross_target-2)<1e-12);await p.reload();ok('absolute inputs and base dates persist',await p.locator('#a_terminal_eps').inputValue()==='14'&&await p.locator('#s_base_start').inputValue()==='2026-10-26');ok('restored absolute calculation valid',await p.evaluate(()=>lastAbsoluteScenario!==null));await p.locator('#a_price_date').fill('2000-01-01');ok('mismatched price date blocks value',await p.locator('#absoluteValue').innerText()==='—');await p.locator('#a_price_date').fill('2026-10-26');
await p.locator('#absolutePanel details').nth(0).evaluate(e=>e.open=true);for(const[k,v]of Object.entries({revenue:'100',revenues:'10,10,10',margins:'20,20,20',shares:'1,1,1',interest:'1',tax:'20',other:'0'}))await p.locator('#b_'+k).fill(v);await p.locator('#bridgeApply').click();ok('operating bridge produces an adopted positive EPS',Number(await p.locator('#a_terminal_eps').inputValue())>0);const bridgeEPS=Number(await p.locator('#a_terminal_eps').inputValue());await p.locator('#b_shares').fill('2,2,2');await p.locator('#bridgeApply').click();ok('dilution halves derived EPS',Math.abs(Number(await p.locator('#a_terminal_eps').inputValue())/bridgeEPS-.5)<1e-12);
await p.locator('#absolutePanel details').nth(1).evaluate(e=>e.open=true);for(const[k,v]of Object.entries({rf:'4',erp:'5',g:'3',payout:'50'}))await p.locator('#m_'+k).fill(v);await p.locator('#multipleApply').click();const pe1=Number(await p.locator('#a_terminal_pe').inputValue());await p.locator('#m_rf').fill('5');await p.locator('#multipleApply').click();ok('higher nominal rate reduces steady-state PE',Number(await p.locator('#a_terminal_pe').inputValue())<pe1);await p.locator('#s_base_eps').fill('');ok('invalid base clears all absolute numbers',await p.locator('#absoluteValue').innerText()==='—'&&await p.locator('#absoluteExecution').innerText()==='');ok('no JS errors',errors.length===0);await p.setViewportSize({width:390,height:844});ok('no mobile page overflow',await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+2));await p.screenshot({path:'v8/scenarios_mobile.png',fullPage:true});
}finally{await b.close();await new Promise(r=>server.close(r))}fs.writeFileSync('v8/integration_test_results.json',JSON.stringify({passed:checks.length,checks,scope:'synthetic browser scenarios; not market validation'},null,2));console.log(JSON.stringify({passed:checks.length}));

```

## core_test_results.json
SHA256 f9ddcd4f5f9d6173a92c1634e4f2e0ce2d110fb9128b9c67252aa97f1923a9ec
```
{
  "status": "passed",
  "checks": 29,
  "version": "absolute-earnings-periods-v8",
  "executed_at": "2026-10-29T03:05:33.301Z",
  "core_file": "sites/etf-research/src/v6_calc.js",
  "core_sha256": "3513ffe1ead974a5a508ce0b0bdac1c7008493587325844cbb7e245a2d8a1bb0",
  "checks_run": [
    "Absolute exit price equals independent EPS times PE",
    "Changing terminal EPS independently changes target and entry bound",
    "Changing reference price does not rederive exit PE or terminal price",
    "Changing base EPS does not cancel an independent terminal EPS input",
    "Absolute mode ignores invalid legacy relative-growth inputs",
    "Missing fund fee cannot silently become zero",
    "Prototype fund fee is not an explicitly supplied input",
    "Explicit zero fee is allowed as an assumption",
    "Embedded expense mode does not deduct fund fee twice",
    "Current mode requires same price and valuation date",
    "Historical mode permits at most seven prior calendar days",
    "Future or missing price dates are rejected",
    "Missing evidence date stays unverified rather than inferred from price date",
    "Explicit future evidence date is rejected",
    "A declared past date is not mislabeled independently verified",
    "Wrong earnings windows remain blocked",
    "Nonpositive terminal EPS cannot be PE-valued",
    "Derived PE and target overflow cannot leak Infinity",
    "Maximum fractional entry solves the same cash-flow hurdle with fees and dividends",
    "Required terminal EPS and PE each solve the hurdle independently",
    "Legacy relative API is retained and explicitly versioned as sensitivity",
    "Cash remainder and distributions remain USD and include anniversary timing",
    "Zero stock units charge no stock fees and preserve cash interest",
    "Operating bridge derives EPS from revenue margin interest tax and cumulative dilution",
    "Negative and zero EPS remain unavailable for PE without fabricated zero",
    "Intermediate loss is preserved even if terminal earnings recover",
    "Operating inputs are explicit and mismatched paths rejected",
    "Operating revenue or EPS overflow cannot produce output",
    "Normalized earnings must be annualized at the valuation date"
  ]
}
```

## ui_test_results.json
SHA256 3c07cafd5343ab11a38651ee24222950018bbb049d18fbf7dc4bfca2b29230b8
```
{
  "run_at": "2026-10-29T03:13:49.311Z",
  "core_algorithm_version": "absolute-earnings-periods-v8",
  "tests": 23,
  "checks": [
    "valid declared example produces a price: ",
    "valid input clears stale error text",
    "historical price date is attached",
    "forecast availability is explicitly unknown",
    "new context fields survive record validation",
    "blank EPS clears price",
    "blank EPS clears valuationDefinition",
    "blank EPS clears fundCostBasis",
    "blank EPS clears scenarioBasis",
    "blank EPS clears scenarioInputPosture",
    "fresh SMH uses current fee input",
    "switch to fresh asset clears valuationDefinition",
    "switch to fresh asset clears fundCostBasis",
    "switch to fresh asset clears scenarioBasis",
    "switch to fresh asset clears scenarioInputPosture",
    "home displays latest reviewed conclusion",
    "home review timestamp is sourced",
    "local card shows actual price date",
    "local card labels unverified local inputs",
    "unmodified card retains frozen source and date",
    "expired conclusion explicitly marked historical",
    "expired status is visible",
    "no JavaScript runtime errors"
  ],
  "scope": "Current src JS served with built HTML. Synthetic numbers only; no production changes or external market-data verification."
}
```

## integration_test_results.json
SHA256 eeb45423a506f02042f3648e444a0f891d9c1be791af21011c27ffb642f3a2f2
```
{
  "passed": 12,
  "checks": [
    "absolute outputs blank initially",
    "absolute calculation works with relative growth fields blank",
    "independent exit EPS doubles gross value",
    "absolute inputs and base dates persist",
    "restored absolute calculation valid",
    "mismatched price date blocks value",
    "operating bridge produces an adopted positive EPS",
    "dilution halves derived EPS",
    "higher nominal rate reduces steady-state PE",
    "invalid base clears all absolute numbers",
    "no JS errors",
    "no mobile page overflow"
  ],
  "scope": "synthetic browser scenarios; not market validation"
}
```

## evidence_map.json
SHA256 3ad76a786e6d8752ee193ea79f02eeee6bf32a5dd719adbf93b7bada55cf1e1e
```
{
  "schema": "v8.evidence_to_model_map.v1",
  "status": "reference_only_not_full_fund_forecast",
  "financial_actuals_unchanged": true,
  "company_references": [
    {
      "symbol": "MSFT",
      "reported_period": "FY27 Q1",
      "period_end": "2026-09-30",
      "unit": "USD billions except EPS",
      "actual_revenue": 92.279,
      "operating_margin_same_period": 0.4975671604590427,
      "guidance": {
        "status": "call_guidance_not_extracted",
        "notes": "Press release refers guidance to the conference call; prior quarter guidance not reused as current."
      },
      "source_ids": [
        "MSFT_Q1_ACTUAL_20261028"
      ],
      "mapping": "reference_only",
      "blocking_inputs": [
        "verified annual revenue per common share or ETF unit",
        "comparable recurring earnings basis",
        "interest/tax/common-share and preferred claims",
        "future annual margins/share counts",
        "independent exit valuation assumptions"
      ],
      "automatic_forecast_update": false
    },
    {
      "symbol": "AMZN",
      "reported_period": "Q2 2026",
      "period_end": "2026-06-30",
      "unit": "USD billions",
      "actual_revenue": 200.6,
      "operating_margin_same_period": 0.1370887337986042,
      "guidance": null,
      "source_ids": [
        "AMZN_Q2"
      ],
      "mapping": "reference_only",
      "blocking_inputs": [
        "verified annual revenue per common share or ETF unit",
        "comparable recurring earnings basis",
        "interest/tax/common-share and preferred claims",
        "future annual margins/share counts",
        "independent exit valuation assumptions"
      ],
      "automatic_forecast_update": false
    },
    {
      "symbol": "GOOGL",
      "reported_period": "Q2 2026",
      "period_end": "2026-06-30",
      "unit": "USD billions",
      "actual_revenue": 119.796,
      "operating_margin_same_period": 0.3403285585495342,
      "guidance": null,
      "source_ids": [
        "GOOGL_Q2"
      ],
      "mapping": "reference_only",
      "blocking_inputs": [
        "verified annual revenue per common share or ETF unit",
        "comparable recurring earnings basis",
        "interest/tax/common-share and preferred claims",
        "future annual margins/share counts",
        "independent exit valuation assumptions"
      ],
      "automatic_forecast_update": false
    },
    {
      "symbol": "META",
      "reported_period": "Q3 2026",
      "period_end": "2026-09-30",
      "unit": "USD billions",
      "actual_revenue": 64.601,
      "operating_margin_same_period": 0.2010495193572855,
      "guidance": {
        "period": "calendar2026",
        "capex_including_lease_principal_low": 135,
        "capex_including_lease_principal_high": 145,
        "previous_low": 130,
        "next_quarter_revenue_low": 73,
        "next_quarter_revenue_high": 76
      },
      "source_ids": [
        "META_Q3",
        "META_FINANCING_PRICING_20261027",
        "META_FINANCING_LAUNCH_20261026",
        "NVDA_META_20261027",
        "AMD_META_20261027"
      ],
      "mapping": "reference_only",
      "blocking_inputs": [
        "verified annual revenue per common share or ETF unit",
        "comparable recurring earnings basis",
        "interest/tax/common-share and preferred claims",
        "future annual margins/share counts",
        "independent exit valuation assumptions"
      ],
      "automatic_forecast_update": false
    },
    {
      "symbol": "NVDA",
      "reported_period": "FY27 Q2",
      "period_end": "2026-07-26",
      "unit": "USD billions except EPS",
      "actual_revenue": 96.221,
      "operating_margin_same_period": null,
      "guidance": {
        "period": "FY27 Q3",
        "revenue": 108,
        "tolerance_pct": 2,
        "gross_margin_pct": 74,
        "china_data_center_compute_assumed": 0
      },
      "source_ids": [
        "NVDA_Q2",
        "NVDA_ORACLE_20261027",
        "NVDA_META_20261027"
      ],
      "mapping": "reference_only",
      "blocking_inputs": [
        "verified annual revenue per common share or ETF unit",
        "comparable recurring earnings basis",
        "interest/tax/common-share and preferred claims",
        "future annual margins/share counts",
        "independent exit valuation assumptions"
      ],
      "automatic_forecast_update": false
    },
    {
      "symbol": "TSM",
      "reported_period": "Q3 2026",
      "period_end": "2026-09-30",
      "unit": "USD billions",
      "actual_revenue": 46.72,
      "operating_margin_same_period": null,
      "guidance": {
        "period": "Q4 2026",
        "revenue_low": 52.3,
        "revenue_high": 54.3,
        "gross_margin_low_pct": 65,
        "gross_margin_high_pct": 67,
        "calendar2026_capex_low": 60,
        "calendar2026_capex_high": 64
      },
      "source_ids": [
        "TSM_Q3",
        "TSM_Q3_CALL"
      ],
      "mapping": "reference_only",
      "blocking_inputs": [
        "verified annual revenue per common share or ETF unit",
        "comparable recurring earnings basis",
        "interest/tax/common-share and preferred claims",
        "future annual margins/share counts",
        "independent exit valuation assumptions"
      ],
      "automatic_forecast_update": false
    },
    {
      "symbol": "MU",
      "reported_period": "FY26 Q4",
      "period_end": "2026-09-03",
      "unit": "USD billions except EPS",
      "actual_revenue": 54.229,
      "operating_margin_same_period": null,
      "guidance": {
        "period": "FY27 Q1",
        "revenue": 61.5,
        "revenue_tolerance": 1.5,
        "gaap_gross_margin_pct": 85.95,
        "non_gaap_gross_margin_pct": 86.25,
        "gaap_eps": 37.84,
        "non_gaap_eps": 38.15,
        "eps_tolerance": 1
      },
      "source_ids": [
        "MU_Q4"
      ],
      "mapping": "reference_only",
      "blocking_inputs": [
        "verified annual revenue per common share or ETF unit",
        "comparable recurring earnings basis",
        "interest/tax/common-share and preferred claims",
        "future annual margins/share counts",
        "independent exit valuation assumptions"
      ],
      "automatic_forecast_update": false
    },
    {
      "symbol": "000660.KS",
      "reported_period": "Q3 2026",
      "period_end": "2026-09-30",
      "unit": "KRW trillions",
      "actual_revenue": 104.6155,
      "operating_margin_same_period": 0.796572209663004,
      "guidance": {
        "status": "management_forward_claims_not_verified_outcomes",
        "investment_next_year": "significant increase planned; scale and timing conditional on demand/profitability",
        "capacity_LTA_2027_2028": "more than50% according to management",
        "shortage_through_2030": "management expectation, not fact"
      },
      "source_ids": [
        "SK_Q3_RESULTS"
      ],
      "mapping": "reference_only",
      "blocking_inputs": [
        "verified annual revenue per common share or ETF unit",
        "comparable recurring earnings basis",
        "interest/tax/common-share and preferred claims",
        "future annual margins/share counts",
        "independent exit valuation assumptions"
      ],
      "automatic_forecast_update": false
    },
    {
      "symbol": "005930.KS",
      "reported_period": "Q3 preliminary earnings guidance, not full released actuals",
      "period_end": "2026-09-30",
      "unit": "KRW trillions",
      "actual_revenue": null,
      "operating_margin_same_period": null,
      "guidance": {
        "consolidated_revenue": 195,
        "consolidated_operating_income": 107.4
      },
      "source_ids": [
        "SAMSUNG_GUIDE"
      ],
      "mapping": "reference_only",
      "blocking_inputs": [
        "verified annual revenue per common share or ETF unit",
        "comparable recurring earnings basis",
        "interest/tax/common-share and preferred claims",
        "future annual margins/share counts",
        "independent exit valuation assumptions"
      ],
      "automatic_forecast_update": false
    }
  ],
  "macro_references": [
    {
      "id": "fed_rate",
      "source_ids": [
        "FOMC_OCT_ACTUAL_20261028"
      ],
      "observation_date": "2026-10-28",
      "facts": {
        "target_low_pct": 3.75,
        "target_high_pct": 4.0,
        "change_bp": 0,
        "vote_for": 10,
        "vote_against": 2
      },
      "analysis": "本次维持区间，2位异议者倾向加息25bp。不能把维持利率理解为确定宽松或股市上涨。"
    },
    {
      "id": "cpi",
      "source_ids": [
        "CPI_SEP"
      ],
      "observation_period": "2026-09",
      "released": "2026-10-14",
      "facts": {
        "headline_yoy_pct": 3.7,
        "headline_mom_sa_pct": 0.6,
        "core_yoy_pct": 2.6,
        "core_mom_sa_pct": 0.3,
        "energy_yoy_pct": 20.4,
        "gasoline_mom_pct": 9.1
      },
      "analysis": "Headline inflation shock is energy-heavy, while core is milder; Fed cannot be presumed to provide immediate valuation relief."
    },
    {
      "id": "pce",
      "source_ids": [
        "PCE_AUG"
      ],
      "observation_period": "2026-08",
      "released": "2026-09-30",
      "facts": {
        "headline_yoy_pct": 3.4,
        "headline_mom_pct": 0.3,
        "core_yoy_pct": 3,
        "core_mom_pct": 0.2,
        "real_consumption_mom_pct": 0.6
      },
      "analysis": "Consumption remained strong. September PCE not released yet; scheduled Oct29 08:30EDT."
    },
    {
      "id": "jobs",
      "source_ids": [
        "JOBS_SEP"
      ],
      "observation_period": "2026-09",
      "released": "2026-10-02",
      "facts": {
        "payroll_change": 29000,
        "unemployment_pct": 4.2,
        "prior_12month_mean_payroll_change": 45000,
        "july_revised_payroll_change": -10000,
        "august_revised_payroll_change": 133000,
        "two_month_revision": -60000
      },
      "analysis": "Hiring is slow, but headline unemployment alone is not a recession call; GDP remains positive."
    },
    {
      "id": "gdp",
      "source_ids": [
        "GDP_Q2",
        "GDP_CAL"
      ],
      "observation_period": "2026Q2_third_estimate",
      "released": "2026-09-30",
      "facts": {
        "real_gdp_qoq_annualized_pct": 2.2,
        "prior_quarter_revised_pct": 2.5
      },
      "analysis": "Q2 positive growth; Q3 advance estimate still upcoming Oct29. Do not cite unreleased Q3 actuals."
    },
    {
      "id": "hy_oas",
      "source_ids": [
        "FRED_HY"
      ],
      "observation_date": "2026-10-26",
      "published_update": "2026-10-27T10:13:00-05:00",
      "facts": {
        "percent": 3.3,
        "previous_oct23_percent": 3.38
      },
      "analysis": "Latest 1-day narrowing, not proof of systemic all-clear. FRED notes only3years history fromApril2026: old free-full-history assumptions no longer valid."
    },
    {
      "id": "real_yield",
      "source_ids": [
        "FRED_REAL"
      ],
      "observation_date": "2026-10-23",
      "published_update": "2026-10-26T15:16:00-05:00",
      "facts": {
        "ten_year_real_yield_pct": 2.66
      },
      "analysis": "Latest accessible observation lags price cutoff; use explicitly dated. High real discount rate can pressure growth multiples even while earnings rise."
    },
    {
      "id": "industry_sales",
      "source_ids": [
        "SIA_AUG"
      ],
      "observation_period": "2026-08",
      "released": "2026-10-05",
      "facts": {
        "global_sales_usd_bn": 159.7,
        "yoy_pct": 144.3,
        "mom_pct": 8
      },
      "basis": "WSTS three-month moving average, nominal sales, not unit volume.",
      "analysis": "Broad current sales expansion supports industry growth. Mix and pricing mean this is not proof every chip subsegment or end demand is equally healthy."
    }
  ],
  "transmission": {
    "revenue_guidance": "compare matching period/unit before constructing annual growth path",
    "capex_depreciation": "affects future margins/cash flow; no mechanical revenue increment",
    "financing": "interest/preferred claims and share-count dilution; not revenue",
    "nominal_rates": "Gordon k=nominal risk-free+equity risk premium, chosen scenario only",
    "credit_spreads": "risk-premium review reference, no one-to-one coefficient",
    "valuation": "independent terminal EPS times independent terminal PE; not derived from current reference price"
  },
  "funds": [
    {
      "symbol": "QQQM",
      "full_fund_forecast_ready": false,
      "missing": [
        "verified complete base annual EPS",
        "complete three-year exit earnings",
        "independently supported exit PE"
      ],
      "available_subset_is_not_full_fund": true
    },
    {
      "symbol": "SMH",
      "full_fund_forecast_ready": false,
      "missing": [
        "verified complete base annual EPS",
        "complete three-year exit earnings",
        "independently supported exit PE"
      ],
      "available_subset_is_not_full_fund": true
    },
    {
      "symbol": "SOXX",
      "full_fund_forecast_ready": false,
      "missing": [
        "verified complete base annual EPS",
        "complete three-year exit earnings",
        "independently supported exit PE"
      ],
      "available_subset_is_not_full_fund": true
    },
    {
      "symbol": "DRAM",
      "full_fund_forecast_ready": false,
      "missing": [
        "verified complete base annual EPS",
        "complete three-year exit earnings",
        "independently supported exit PE"
      ],
      "available_subset_is_not_full_fund": true
    }
  ]
}
```

## core_notes.md
SHA256 9080400cc35ed2baf827eafedafcfcc098b336b5598845ed0197ade2a77cd0c1
```
# V8核心公式修复与接口

本轮只修改`sites/etf-research/src/v6_calc.js`，新增`v8/core_tests.mjs`及本说明；没有修改`app.js`、V6/V7历史结果或发布网站。Node语法检查和29项核心测试已实际通过。

版本为`absolute-earnings-periods-v8`。所有前瞻数值仍是明确输入的情景，不从代码构造市场事实，也不证明价格便宜、底部存在或预测有效。

## 绝对退出估值：scenarioAbsolute

调用`ResearchMath.scenarioAbsolute(input)`。所需公共字段沿用情景表单：

```javascript
{
  budget, entry, reference, years, fx0, fx1,
  bps, fee, fx_bps, cash_rate, shock,
  dividend, withholding,
  fund_fee,                     // 必须显式提供有限数字，未知不默认0
  fee_mode: 'deduct',            // 或 'embedded'
  valuation_basis: 'ntm',        // 'ttm' / 'ntm' / 'normalized'
  valuation_date: '2026-10-26',
  price_date: '2026-10-26',
  context_mode: 'historical',    // 'current'默认要求同日
  evidence_date: null,           // 缺失表示未验证，不借用价格日期
  base_start: '2026-10-26',
  base_end: '2027-10-26',
  terminal_start: '2029-10-26',
  terminal_end: '2030-10-26',
  base_eps: 5,
  terminal_eps: 8,               // 独立输入，不能由reference反算
  terminal_pe: 20,               // 独立输入
  hurdle: 0.10,
  source_note: '人工输入条件情景，基准与退出均须同基金份额口径'
}
```

基准PE只用于展示：`base_pe = reference / base_eps`。条件毛退出价格为`terminal_eps × terminal_pe`，不再从参考价反算退出倍数。所以只改退出EPS会独立改变退出价和条件买价；只改参考价不会机械改变退出价。它改变基准PE和显示出的相对倍数比例。

`fee_mode='deduct'`时补扣基金费用：`target = gross_target × (1-fund_fee)^years`；`embedded`表示输入退出价格口径已包含基金层面费用，不再重复扣。历史ETF价格不通过这里重复扣费。

返回保留`target/gross_target/maxEntry/fractional/integer/reverse`等执行字段，增加：

- `valuation_model='absolute_terminal_eps_pe'`
- `base_eps/base_pe/terminal_eps/terminal_pe/multiple_ratio_vs_base`
- `base_window/terminal_window/date_alignment`
- `evidence_date/evidence_status`
- `decision_status='not_decision_ready'`

旧相对增长字段`g1/growth/multiple`不参与绝对估值，因此它们缺失或无效不应阻断独立退出EPS/PE计算。

## 日期与证据

- `price_date`、`valuation_date`必须为真实ISO日期，不能缺失。
- `context_mode='current'`要求两日相同；`historical`允许价格日期在估值日前0–7个日历日内，禁止未来价格。冻结研究可直接将估值日选为价格日。
- `evidence_date`为null/缺失/空白时返回`evidence_status='unverified'`；不能把价格截止日、构建日当作盈利预测可得日。
- 显式证据日期必须不晚于估值日；返回`declared_date_not_independently_verified`，没有把用户填写日期冒充独立验证。
- 盈利窗口仍要求一日历年、退出窗口整体平移整数3–20年。NTM从估值日开始；TTM在估值日结束。归一化口径须给足周期/调整说明。

## 相对敏感性兼容

保留`scenarioV6(input)`，另导出同一函数别名`scenarioRelativeV8`。它仍按`reference × (1+g1) × (1+growth)^(years−1) × multiple`计算，但明确返回`valuation_model='relative_sensitivity_compatibility'`与V8版本。

这是显式关联基准PE的相对敏感性，不是独立的退出PE估值。它也执行显式费率、日期/窗口、证据时点和派生有限值检查。

## 经营桥接：operatingBridgeV8

调用格式：

```javascript
{
  R0: 100,
  revenue_growth_path: [0.10, 0.20],
  operating_margin_path: [0.20, 0.25],
  interest_per_share: 2,
  tax_rate: 0.20,
  other_recurring_per_share: 1,
  share_factor_path: [1.10, 1.20]
}
```

`R0`单位为USD/基准日份额；收入增长按年累乘。利息和其他经常项也使用USD/基准日份额，可输入有限标量或同长度逐年数组。`share_factor_path`是累计总股数/基准日总股数的正因子，不是每年股数增长率，避免重复摊薄。

逐年计算：

`收入/基准份额 = R0 × 累计收入增长因子`

`税前利润/基准份额 = 收入 × 经营利润率 − 利息 + 其他税前经常项`

`EPS = [税前利润 − max(税前利润,0)×税率] / 累计股数因子`

亏损时不自动确认税收利益。没有少数股东权益/优先股分配输入，因此明确假设模型利润归属于普通股；输出叫`conditional_common_eps_proxy`，不冒充真实GAAP归母EPS。

`years[]`逐年返回`eps_usd`、收入、经营利润、税前利润、税、股数因子和`pe_valuation_available`。`terminal_eps`保留真实计算值；若最终EPS非正，`valuation_eps=null`、`pe_valuation_available=false`、状态为`unavailable_for_pe_nonpositive_terminal_eps`，不拿0替代亏损。中间年亏损仍保留；若终值年恢复盈利，只允许正终值年进入PE情景。

例如上例首年EPS为16.8/1.1，第二年为25.6/1.2。若收入100、经营利润率−10%、利息2、无其他收益，则EPS为−12，税为0，PE估值不可用。

## 费用、分红、现金与反解

执行接口仍为`executionV6`，另导出别名`executionV8`；它接收已经确定的净退出市场价格，现金引擎本身不再另扣基金费。FX单位始终为每1 USD对应的SGD，余款和分红为USD现金。

分红每持有整周年支付，非整数末期按比例支付；税率为用户情景，分红大于0但税率未知时拒绝税后计算。分红留下USD并按现金假设利率计息，不再投资股票。

碎股最高买价反解仍使用同一份额终值现金流，包含卖出成本及每股净分红累计；零股票时不收不存在的股票交易固定费。资金不足以买入时`maxEntry=null`，不返回负数或假造0。

绝对估值反向门槛增加`reverse.required_terminal_eps`和`required_terminal_pe`；它们分别在另一个退出假设保持不变时反解目标。若现金/分红单独足够，所需非负终值可为0，这只是门槛，并非将公司亏损改成0盈利。

所有返回数值和派生PE/EPS/目标价、份额、现金及压力路径均检查有限性。溢出、下溢导致无意义终值时明确拒绝，不泄漏Infinity/NaN。

## 实际测试

运行`node v8/core_tests.mjs`：29项通过，包括独立EPS反例、参考价不改变退出估值、显式基金费、日期7天边界、未来证据拒绝、非正EPS、PE/EPS溢出、含基金费/分红/税/FX的最高买价回代、退出EPS/PE反解回代、现金币种及周年分红、零股现金利息、经营亏损与税盾、路径长度和摊薄边界。

这些是实现与规格检查，不是市场预期准确性、模型盈利能力或当前入场判断验证。

归一化EPS的年度化基准窗口末日必须等于估值日；用于周期调整的历史期间另在来源说明列明。已追加反例测试。

```
