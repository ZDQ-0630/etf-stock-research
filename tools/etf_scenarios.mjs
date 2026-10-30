// ETF conditional price calculation from explicitly declared fund-level inputs only.
import fs from 'node:fs';import vm from 'node:vm';import crypto from 'node:crypto';import path from 'node:path';
const [input,output]=process.argv.slice(2);if(!input||!output||fs.existsSync(output))throw Error('Provide assumptions file and new output path');
const raw=fs.readFileSync(input),declared=JSON.parse(raw),ctx=vm.createContext({window:{ResearchMath:{}}});vm.runInContext(fs.readFileSync('web/v6_calc.js','utf8'),ctx);
if(declared.schema!=='etf.cloud.fund_scenarios.v1'||!Array.isArray(declared.funds))throw Error('Unsupported scenario input');
const symbols=['QQQM','SMH','SOXX','DRAM'],results=[];
for(const symbol of symbols){
 const candidates=declared.funds.filter(x=>x.symbol===symbol);
 if(candidates.length!==1){results.push({symbol,status:'blocked',reason:candidates.length?'duplicate scenarios':'No complete fund-level declared scenario'});continue;}
 const s=candidates[0];if(s.fund_eps_scope!=='whole_fund_per_share'||typeof s.source_url!=='string'||!s.source_url.startsWith('https://')||typeof s.assumption_note!=='string'||s.assumption_note.trim().length<12){results.push({symbol,status:'blocked',reason:'Fund-level EPS scope, provenance and assumption explanation required'});continue;}
 try{const result=ctx.window.ResearchMath.scenarioAbsolute(s.inputs);results.push({symbol,status:'conditional_scenario_only',input:s.inputs,source_url:s.source_url,assumption_note:s.assumption_note,result,scope:'Declared hypothetical scenario, not verified fair value, official close or buy signal. Full-fund EPS declaration is an assertion requiring independent validation.'});}
 catch(e){results.push({symbol,status:'blocked',reason:e.message});}
}
const hash=x=>crypto.createHash('sha256').update(x).digest('hex'),out={schema:'etf.cloud.fund_scenario_results.v1',created_at:new Date().toISOString(),input_sha256:hash(raw),core_sha256:hash(fs.readFileSync('web/v6_calc.js')),status:'conditional_only_no_automatic_entry_signal',results};
fs.writeFileSync(output,JSON.stringify(out,null,2),{flag:'wx'});console.log(JSON.stringify({conditional_scenarios:results.filter(x=>x.status==='conditional_scenario_only').length,blocked:results.filter(x=>x.status==='blocked').length,status:out.status}));
