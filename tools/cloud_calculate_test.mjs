import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import assert from 'node:assert/strict';import{spawnSync}from'node:child_process';
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'etf-cloud-test-'));
try {
 const input=path.join(tmp,'input.json'),output=path.join(tmp,'out.json');
 const data={run_id:'synthetic-test',quotes:{retrieved_at:'2026-01-03T00:00:00Z',raw:[{symbol:'AAA.US',timestamp:'2026-01-02T20:00:00Z',last_done:'90'}]},baseline_stocks:{companies:[{symbol:'AAA',quote:{price:100,timestamp:'2026-01-01T20:00:00Z'},scenarios:[{id:'reference',terminal_eps:10,terminal_pe:20,years:3}]},{symbol:'BBB',quote:{price:20},scenarios:[]}]}};
 fs.writeFileSync(input,JSON.stringify(data));
 const run=()=>spawnSync(process.execPath,['tools/cloud_calculate.mjs',input,output],{encoding:'utf8'});
 const first=run();assert.equal(first.status,0,first.stderr);const out=JSON.parse(fs.readFileSync(output,'utf8'));
 assert.equal(out.results[0].rows[1].current.terminal,200);assert.ok(Math.abs(out.results[0].rows[1].current.annualized-(200/90)**(1/3)+1)<1e-12);
 assert.equal(out.results[1].status,'blocked');assert.equal(out.overall_status,'partial_not_a_complete_market_review');
 assert.notEqual(run().status,0,'existing results must not be overwritten');
 console.log('Synthetic calculation, missing quote, partial status and immutable output: passed');
}finally{fs.rmSync(tmp,{recursive:true,force:true})}
