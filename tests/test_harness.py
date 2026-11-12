import sys, tempfile, unittest, datetime as dt
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dory_harness import conversation, router, checklist

class T(unittest.TestCase):
    def setUp(self): self.h = router.Harness({"brains": {}})
    def test_day_requests(self):
        self.assertTrue(conversation.day_requested("What got done today?"))
        self.assertFalse(conversation.day_requested("I had a strange day today"))
    def test_routing(self):
        self.assertEqual(self.h.route("nice weather")[0], "light")
        self.assertEqual(self.h.route("explain why the sky is blue")[0], "strong")
        self.assertEqual(self.h.route("word " * 25)[0], "strong")
    def test_sticky_and_busy(self):
        self.h.last.update(brain="strong", t=100.0); self.assertEqual(self.h.route("ok cool", now=150.0)[0], "strong"); self.assertEqual(self.h.route("ok cool", now=400.0)[0], "light")
        self.assertEqual(router.Harness({}, busy=lambda: True).route("hi")[0], "strong")
    def test_wake_and_followup(self):
        w = router.wake_re(["dory"]); self.assertTrue(router.addressed(w, "hey dory", 0)); self.assertTrue(router.addressed(w, "okay computer", 0))
        self.assertFalse(router.addressed(w, "random tv talk", 0, 3.0, now=1000.0)); self.assertTrue(router.addressed(w, "and then?", 990.0, 3.0, now=1000.0))
        self.assertFalse(router.addressed(w, "long ramble", 990.0, 12.0, now=1000.0))
    def test_trim_ground(self):
        self.assertEqual(router.trim("One two. " * 40, 10), "One two. One two. One two. One two. One two.".replace("One two. One two. One two. One two. One two.", "One two. One two. One two. One two. One two."))
        self.assertEqual(router.ground("I do music myself."), "I don't know that.")
    def test_checklist(self):
        now = dt.datetime(2026, 1, 1, 12, 0); r = checklist.check([{"name": "a", "by": "06:00"}, {"name": "b", "by": "18:00"}, {"name": "c", "by": "06:00"}], lambda i: "ok" if i["name"] == "c" else None, now)
        self.assertEqual([x["state"] for x in r], ["missed", "pending", "ok"])
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"; self.assertEqual(len(checklist.new_problems(r, p, now.date())), 1); self.assertEqual(len(checklist.new_problems(r, p, now.date())), 0)
if __name__ == "__main__": unittest.main()
