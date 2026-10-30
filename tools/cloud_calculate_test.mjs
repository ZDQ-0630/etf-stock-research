import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import assert from 'node:assert/strict';import{spawnSync}from'node:child_process';
import{validateClose}from'./quote_guard.mjs';
const now=Date.parse('2026-10-30T04:00:00Z'),hash='a'.repeat(64),calendar={source_url:'https://www.nyse.com/trade/hours-calendars',source_sha256:hash,checked_at:'2026-10-30T03:00:00Z',unplanned_closure_reviewed:true};
const q={symbol:'AAA.US',session:'official_regular_close',trade_date:'2026-10-29',timestamp:'2026-10-29T20:00:00Z',retrieved_at:'2026-10-30T03:00:00Z',price:90,source_sha256:hash};
const obs=[{...q,provider_id:'a',source_url:'https://a.example/close'},{...q,provider_id:'b',source_url:'https://b.example/close'}];
const valid=(a=obs,c=calendar,n=now)=>validateClose('AAA.US',{observations:a},c,n);
assert.equal(valid().ok,true);assert.equal(valid([{...obs[0],session:'post_market'},obs[1]]).ok,false);
assert.equal(valid([{...obs[0],timestamp:'2026-10-29T19:59:00Z'},obs[1]]).ok,false);
assert.equal(valid([{...obs[0],timestamp:'invalid'},obs[1]]).ok,false);
assert.equal(valid([{...obs[0],trade_date:'2026-10-28'},obs[1]]).ok,false);
assert.equal(valid([obs[0],{...obs[1],price:95}]).ok,false);
assert.equal(valid([obs[0],{...obs[1],source_url:'https://a.example/other'}]).ok,false);
assert.equal(valid(obs,{...calendar,checked_at:'2026-10-28T03:00:00Z'}).ok,false);
assert.equal(valid(obs,{...calendar,unplanned_closure_reviewed:false}).ok,false);
assert.equal(valid(obs,calendar,Date.parse('2027-01-02T00:00:00Z')).ok,false);
const earlyObs=obs.map(x=>({...x,trade_date:'2026-11-27',timestamp:'2026-11-27T18:00:00Z',retrieved_at:'2026-11-27T19:00:00Z'}));
assert.equal(valid(earlyObs,{...calendar,checked_at:'2026-11-27T19:00:00Z'},Date.parse('2026-11-27T20:00:00Z')).ok,true);
assert.equal(valid(earlyObs.map(x=>({...x,timestamp:'2026-11-27T21:00:00Z'})),{...calendar,checked_at:'2026-11-27T22:00:00Z'},Date.parse('2026-11-27T23:00:00Z')).ok,false);
const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'etf-cloud-test-'));
try {
 const input=path.join(tmp,'input.json'),output=path.join(tmp,'out.json');
 const data={run_id:'synthetic-test',quotes:{raw:[{symbol:'AAA.US',timestamp:'2026-10-29T20:00:00Z',last_done:'90'}]},baseline_stocks:{companies:[{symbol:'AAA',quote:{price:100},scenarios:[{id:'reference',terminal_eps:10,terminal_pe:20,years:3}]}]}};
 fs.writeFileSync(input,JSON.stringify(data));const run=()=>spawnSync(process.execPath,['tools/cloud_calculate.mjs',input,output],{encoding:'utf8'});
 const first=run();assert.equal(first.status,0,first.stderr);const out=JSON.parse(fs.readFileSync(output,'utf8'));
 assert.equal(out.results[0].status,'blocked');assert.equal(out.overall_status,'partial_not_a_complete_market_review');assert.notEqual(run().status,0);
 console.log('Calendar, session, time, staleness, cross-source, missing evidence and immutability tests passed');
}finally{fs.rmSync(tmp,{recursive:true,force:true})}
