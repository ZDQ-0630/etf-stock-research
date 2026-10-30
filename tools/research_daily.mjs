// Research-only date-level arithmetic. Never asserts an official close or a trading signal.
import fs from 'node:fs';import path from 'node:path';import vm from 'node:vm';import crypto from 'node:crypto';
import {riskFor} from './etf_risk.mjs';
const [snapshotPath,outputPath]=process.argv.slice(2);if(!snapshotPath||!outputPath||fs.existsSync(outputPath))throw Error('Provide snapshot and new output path');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8')),hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const snapshot=read(snapshotPath),baselinePath='web/stock-data-monitor-20261029.json',baseline=read(baselinePath);
if(snapshot.schema!=='etf.cloud.partial_snapshot.v1'||!Array.isArray(snapshot.prices))throw Error('Unsupported snapshot');
if(snapshot.baseline_sha256!==hash(baselinePath))throw Error('Baseline hash mismatch');
const stamp=Date.parse(snapshot.started_at),now=Date.now();if(!Number.isFinite(stamp)||stamp>now+60000||now-stamp>36*3600000)throw Error('Snapshot missing, future or older than 36 hours');
const source='web/stocks.js',context=vm.createContext({window:{ResearchMath:{}},document:{getElementById:()=>null}});vm.runInContext(fs.readFileSync(source,'utf8'),context);
vm.runInContext(fs.readFileSync('web/model.js','utf8'),context);
vm.runInContext(fs.readFileSync('web/v6_calc.js','utf8'),context);
const rows=[];
for(const c of baseline.companies){
 const p=snapshot.prices.find(x=>x.symbol===c.symbol),a=p?.sources?.nasdaq,b=p?.sources?.yahoo;
 const valid=x=>x&&typeof x.value==='number'&&Number.isFinite(x.value)&&x.value>0&&/^[a-f0-9]{64}$/i.test(x.sha256||'')&&Number.isFinite(Date.parse(x.retrieved_at));
 if(!p||p.session_date!==snapshot.latest_scheduled_session||p.agreement!==true||!valid(a)||!valid(b)||Math.abs(a.value-b.value)>Math.max(.01,a.value*.001)||!/^https:\/\/api\.nasdaq\.com\//.test(a.url)||!/^https:\/\/query1\.finance\.yahoo\.com\//.test(b.url)){
  rows.push({symbol:c.symbol,status:'blocked',reason:'Missing or inconsistent date-level independent observations'});continue;
 }
 const old=c.quote?.price;if(typeof old!=='number'||!Number.isFinite(old)||old<=0){rows.push({symbol:c.symbol,status:'blocked',reason:'Prior reference price missing'});continue;}
 const scenarios=[];
 for(const x of c.scenarios??[])for(const hurdle of [.08,.10,.12]){
  try {const spec={eps:x.terminal_eps,pe:x.terminal_pe,years:x.years,hurdle},before=context.window.StockResearchMath.calculate({...spec,price:old}),after=context.window.StockResearchMath.calculate({...spec,price:a.value});
   scenarios.push({id:x.id,years:x.years,hurdle,terminal_eps:x.terminal_eps,terminal_pe:x.terminal_pe,old:before,current:after,required_pe:a.value*(1+hurdle)**x.years/x.terminal_eps,price_only_delta:after.annualized-before.annualized});
  }catch(e){scenarios.push({id:x.id,hurdle,status:'blocked',reason:e.message});}
 }
 rows.push({symbol:c.symbol,status:scenarios.some(x=>x.current)?'computed_for_research_only':'blocked',price:a.value,date:p.session_date,previous_price:old,previous_date:c.quote.date,sources:[a,b],scenarios});
}
const history=read('web/data.json'),risk=['QQQM','SMH','SOXX','DRAM'].map(s=>riskFor(s,snapshot,history,context.window.ResearchMath));
const fx_sensitivity=[];for(const company of rows.filter(x=>x.status==='computed_for_research_only')){const scenario=company.scenarios.find(x=>x.id==='reference'&&x.hurdle===.1&&x.current);if(!scenario)continue;for(const fx1 of [1.17,1.3,1.43]){const inputs={budget:1000,entry:company.price,target:scenario.current.terminal,years:scenario.years,fx0:1.3,fx1,bps:5,fee:1,fx_bps:10,cash_rate:0,shock:-.3,dividend:0,withholding:0};try{fx_sensitivity.push({symbol:company.symbol,inputs,result:context.window.ResearchMath.executionV6(inputs),scope:'synthetic SGD1000 and explicit cost/FX assumptions; not observed exchange rate, account holdings, return forecast or fee estimate'});}catch(e){fx_sensitivity.push({symbol:company.symbol,status:'blocked',reason:e.message})}}}
const out={schema:'etf.cloud.daily_research.v1',computed_at:new Date().toISOString(),snapshot_sha256:hash(snapshotPath),baseline_sha256:hash(baselinePath),frozen_history_sha256:hash('web/data.json'),script_sha256:hash(import.meta.filename),risk_script_sha256:hash('tools/etf_risk.mjs'),stock_core_sha256:hash(source),history_core_sha256:hash('web/model.js'),scenario_core_sha256:hash('web/v6_calc.js'),status:'research_only_not_a_buy_signal',quote_scope:'Two providers agree on date-only daily bar; close timestamp, extraordinary closures, upstream independence and price adjustments are unverified.',return_scope:'USD gross price-return scenario, excludes fees, tax, dividends and FX; input scenarios are not consensus or forecasts.',rows,risk,fx_sensitivity,blocked:['verified close or entry signal','complete ETF valuation','company fundamental interpretation and forward assumptions','verified actual costs, tax and FX','durable full dataset and comparison','website investment update']};
fs.writeFileSync(outputPath,JSON.stringify(out,null,2),{flag:'wx'});console.log(JSON.stringify({research_only_computed:rows.filter(x=>x.status==='computed_for_research_only').length,risk_states_computed:risk.filter(x=>x.status==='computed_for_research_only').length,blocked:risk.filter(x=>x.status==='blocked').length,status:out.status}));
