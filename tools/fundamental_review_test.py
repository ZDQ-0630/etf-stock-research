import json,subprocess,sys,tempfile,unittest
from pathlib import Path
class Tests(unittest.TestCase):
 def test_changed_eps_unknown_asof_cannot_change_scenario(self):
  with tempfile.TemporaryDirectory(dir='.') as temp:
   src=Path(temp)/'in.json';out=Path(temp)/'out.json'
   snap={'schema':'etf.cloud.partial_snapshot.v1','forecasts':{'AAA':{'status':'retrieved_unverified','rows':[{'fiscal_end':'Dec 2028','previous_vendor_eps':10,'vendor_eps':9,'analyst_count':4,'vendor_asof':None,'comparability':'unknown'}]}},'macro':{'treasury_nominal':{'observations':[{'date':'2026-10-28','value_pct':5.0},{'date':'2026-10-29','value_pct':5.1}],'source':'official'}}}
   src.write_text(json.dumps(snap),encoding='utf8');r=subprocess.run([sys.executable,'tools/fundamental_review.py',str(src),str(out)],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
   d=json.loads(out.read_text());self.assertEqual(d['companies'][0]['status'],'changed_requires_review');self.assertEqual(d['companies'][0]['scenario_status'],'unchanged');self.assertIsNone(d['companies'][0]['fiscal_changes'][0]['vendor_asof']);self.assertLess(d['macro'][0]['illustrative_steady_state']['pe_after'],d['macro'][0]['illustrative_steady_state']['pe_before']);self.assertNotEqual(subprocess.run([sys.executable,'tools/fundamental_review.py',str(src),str(out)],capture_output=True).returncode,0)
if __name__=='__main__':unittest.main()
