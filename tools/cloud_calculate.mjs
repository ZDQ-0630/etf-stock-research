// Local/cloud-neutral computation only. This program does not retrieve data or publish.
// Usage: node calculate.mjs <run-input.json> <output.json>
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import crypto from 'node:crypto';

const [inputPath, outputPath] = process.argv.slice(2);
if (!inputPath || !outputPath) throw Error('Provide input and new output paths');
if (fs.existsSync(outputPath)) throw Error('Output already exists; historical runs are immutable');
const read = p => JSON.parse(fs.readFileSync(p, 'utf8'));
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const root = process.cwd();
const input = read(inputPath);
if (!input.run_id || !input.quotes?.retrieved_at || !Array.isArray(input.quotes.raw) || !input.baseline_stocks?.companies) throw Error('Missing run, quote timestamp or declared stock scenarios');
const context = vm.createContext({window:{ResearchMath:{}},document:{getElementById:()=>null}});
const coreDir=fs.existsSync(path.join(root,'sites/etf-research/src/model.js'))?'sites/etf-research/src':'web';
const files = ['model.js','v6_calc.js','stocks.js'].map(n => path.join(root,coreDir,n));
for (const file of files) vm.runInContext(fs.readFileSync(file,'utf8'),context);
const S=context.window.StockResearchMath;
const results=[];
for (const company of input.baseline_stocks.companies) {
  const quote=input.quotes.raw.find(q=>q.symbol===company.symbol+'.US');
  if (!quote?.timestamp || !Number.isFinite(Date.parse(quote.timestamp)) || !Number.isFinite(Number(quote.last_done)) || Number(quote.last_done)<=0) {
    results.push({symbol:company.symbol,status:'blocked',reason:'missing dated regular-session price'}); continue;
  }
  const before=company.quote?.price;
  if (!Number.isFinite(before)||before<=0) {results.push({symbol:company.symbol,status:'blocked',reason:'missing baseline price'});continue;}
  const rows=[];
  for(const s of company.scenarios??[]) for(const hurdle of [.08,.10,.12]) {
    try {
      const common={eps:s.terminal_eps,pe:s.terminal_pe,years:s.years,hurdle};
      const old=S.calculate({...common,price:before}), current=S.calculate({...common,price:Number(quote.last_done)});
      rows.push({scenario_id:s.id,hurdle,terminal_eps:s.terminal_eps,terminal_pe:s.terminal_pe,years:s.years,old,current,
        required_pe:Number(quote.last_done)*(1+hurdle)**s.years/s.terminal_eps,
        price_only_annualized_delta:current.annualized-old.annualized,
        conditional_entry_gap:current.max_entry/Number(quote.last_done)-1});
    } catch(e) {rows.push({scenario_id:s.id,hurdle,status:'blocked',reason:e.message});}
  }
  results.push({symbol:company.symbol,status:rows.some(r=>r.current)?'computed':'blocked',old_price:before,old_timestamp:company.quote.timestamp,
    price:Number(quote.last_done),price_timestamp:quote.timestamp,quote_session:'regular_close',rows});
}
const result={schema:'etf.cloud_migration.partial_calculation.v1',run_id:input.run_id,computed_at:new Date().toISOString(),
  input_sha256:hash(inputPath),calculator_sha256:hash(import.meta.filename),algorithm_version:context.window.ResearchMath.SCENARIO_VERSION,
  core_sha256:Object.fromEntries(files.map(f=>[path.basename(f),hash(f)])),
  comparison:'same existing public EPS/PE scenarios, different regular closes; USD gross price return',
  data_freshness:'quote timestamp is market timestamp; retrieval timestamp is not forecast formation time',
  assumptions:'scenarios and hurdle values are illustrations, not validated forecasts or user targets',
  quote_retrieved_at:input.quotes.retrieved_at,results,
  blocked:['automated source acquisition and cross-check','ETF historical risk refresh','company operating and forecast review','ETF valuation','cost and FX','holdings overlap','persistent cloud storage','website publication','reliable entry conclusion'],
  overall_status:'partial_not_a_complete_market_review'};
fs.writeFileSync(outputPath,JSON.stringify(result,null,2),{flag:'wx'});
console.log(JSON.stringify({run_id:result.run_id,computed:results.filter(r=>r.status==='computed').length,blocked:result.blocked.length,output:outputPath}));
