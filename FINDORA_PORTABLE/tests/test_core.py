import sys, unittest
sys.path.insert(0,'../app')
import server
class FindoraCoreTests(unittest.TestCase):
 def test_same_category_required(self):
  l={'kind':'lost','category':'phone','description':'black phone','color':'black','brand':'','location':'hall','date_text':'2026-11-01'}
  f={'kind':'found','category':'wallet','description':'black phone','color':'black','brand':'','location':'hall','date_text':'2026-11-01'}
  self.assertEqual(server.score_pair(l,f)[0],0)
 def test_same_category_score_positive(self):
  l={'kind':'lost','category':'phone','description':'black phone','color':'black','brand':'','location':'hall','date_text':'2026-11-01'}
  f={'kind':'found','category':'phone','description':'black phone','color':'black','brand':'','location':'hall','date_text':'2026-11-02'}
  self.assertGreaterEqual(server.score_pair(l,f)[0],45)
 def test_old_dates_rejected(self):
  l={'kind':'lost','category':'phone','description':'black phone','color':'black','brand':'','location':'hall','date_text':'2026-01-01'}
  f={'kind':'found','category':'phone','description':'black phone','color':'black','brand':'','location':'hall','date_text':'2026-03-15'}
  self.assertEqual(server.score_pair(l,f)[0],0)
if __name__=='__main__': unittest.main()
