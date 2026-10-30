import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import assert from 'node:assert/strict';import crypto from 'node:crypto';import{spawnSync}from'node:child_process';
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'etf-research-'));try{
 const baseraw=fs.readFileSync('web/stock-data-monitor-20261029.json'),base=JSON.parse(baseraw),c=base.companies[0],h=crypto.createHash('sha256').update(baseraw).digest('hex'),input=path.join(dir,'s.json'),output=path.join(dir,'o.json'),clock=new Date().toISOString();
 const source=(host,value)=>({value,sha256:'a'.repeat(64),retrieved_at:clock,url:host});
 const snapshot={schema:'etf.cloud.partial_snapshot.v1',started_at:clock,latest_scheduled_session:'2026-10-29',baseline_sha256:h,prices:[{symbol:c.symbol,session_date:'2026-10-29',agreement:true,sources:{nasdaq:source('https://api.nasdaq.com/example',90),yahoo:source('https://query1.finance.yahoo.com/example',90)}}]};
 const run=()=>spawnSync(process.execPath,['tools/research_daily.mjs',input,output],{encoding:'utf8'});
 fs.writeFileSync(input,JSON.stringify(snapshot));let r=run();assert.equal(r.status,0,r.stderr);let out=JSON.parse(fs.readFileSync(output,'utf8'));assert.equal(out.status,'research_only_not_a_buy_signal');assert.equal(out.rows[0].status,'computed_for_research_only');assert.equal(out.rows.filter(x=>x.status==='blocked').length,base.companies.length-1);
 assert.notEqual(run().status,0,'must not overwrite');fs.unlinkSync(output);
 snapshot.prices[0].sources.yahoo.value=200;fs.writeFileSync(input,JSON.stringify(snapshot));r=run();assert.equal(r.status,0);out=JSON.parse(fs.readFileSync(output));assert.equal(out.rows[0].status,'blocked');fs.unlinkSync(output);
 snapshot.started_at='2026-01-01T00:00:00Z';fs.writeFileSync(input,JSON.stringify(snapshot));assert.notEqual(run().status,0,'stale snapshots must fail');
 console.log('Date-only research calculations, cross-source mismatch, stale input and immutable outputs passed');
}finally{fs.rmSync(dir,{recursive:true,force:true})}
