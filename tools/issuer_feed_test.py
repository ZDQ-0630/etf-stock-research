import unittest,issuer_feed as f
class Tests(unittest.TestCase):
 def test_allowed_host_and_unknown_time(self):
  xml=b'<rss><channel><item><title>Result</title><link>https://investor.atmeta.com/news/1</link><guid>abc</guid><pubDate>Thu, 29 Oct 2026 20:00:00 GMT</pubDate></item><item><title>bad</title><link>https://evil.example/1</link></item></channel></rss>'
  r=f.parse(xml,'META',{'investor.atmeta.com'});self.assertEqual(len(r),1);self.assertEqual(r[0]['published_at'],'2026-10-29T20:00:00+00:00');self.assertIn('not_reviewed',r[0]['status'])
  with self.assertRaises(ValueError):f.parse(b'<!DOCTYPE foo><rss/>','META',{'investor.atmeta.com'})
if __name__=='__main__':unittest.main()
