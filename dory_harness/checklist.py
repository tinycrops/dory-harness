"""A daily checklist: things that must have happened by a time. Each item is checked by a function you supply (`status(item) -> 'ok'|'failed'|None`),
so it works over any job runner. Reports only NEW misses once per day so a log is not nagged."""
import datetime as dt, json
from pathlib import Path

def check(items, status, now=None):
    """items: [{name, by: 'HH:MM'}]. -> [{name, state: ok|pending|missed|failed}]"""
    now = now or dt.datetime.now(); out = []
    for it in items:
        s = status(it)
        due = dt.datetime.combine(now.date(), dt.time.fromisoformat(it["by"]))
        out.append(dict(name=it["name"], state=s if s in ("ok", "failed") else ("missed" if now > due else "pending")))
    return out

def summary(results):
    bad = [r for r in results if r["state"] in ("missed", "failed")]
    if not bad: return f"All {len(results)} daily things are done or still on time."
    return "Not done: " + "; ".join(f"{r['name']} ({r['state']})" for r in bad) + "."

def new_problems(results, seen_path, today=None):
    """Return problems not yet reported today, and remember them."""
    today = (today or dt.date.today()).isoformat(); p = Path(seen_path)
    seen = json.loads(p.read_text()) if p.exists() else {}
    if seen.get("day") != today: seen = dict(day=today, names=[])
    new = [r for r in results if r["state"] in ("missed", "failed") and r["name"] not in seen["names"]]
    seen["names"] += [r["name"] for r in new]; p.write_text(json.dumps(seen)); return new
