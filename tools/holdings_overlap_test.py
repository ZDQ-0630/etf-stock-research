import json,subprocess,sys,tempfile,unittest
from pathlib import Path
class Tests(unittest.TestCase):
 def test_issuer_equity_only_and_immutable(self):
  with tempfile.TemporaryDirectory(dir='.') as temp:
   out=Path(temp)/'out.json';cmd=[sys.executable,'tools/holdings_overlap.py',str(out)];r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
   d=json.loads(out.read_text());self.assertEqual(d['status'],'frozen_data_not_current');self.assertEqual(len(d['funds']),4)
   a=next(f for f in d['funds'] if f['fund']=='SMH');b=next(f for f in d['funds'] if f['fund']=='SOXX');p=next(p for p in d['pairs'] if set(p['funds'])=={'SMH','SOXX'})
   self.assertAlmostEqual(p['observed_direct_equity_overlap'],sum(min(a['direct_equity'][k],b['direct_equity'][k]) for k in set(a['direct_equity'])&set(b['direct_equity'])))
   self.assertTrue(all(p['status']=='partial_lower_bound_not_full_economic_overlap' for p in d['pairs'] if 'DRAM' in p['funds']));self.assertNotEqual(subprocess.run(cmd,capture_output=True).returncode,0)
if __name__=='__main__':unittest.main()
