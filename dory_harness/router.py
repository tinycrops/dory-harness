"""Wake-word gating, routing, fallback and the call log.
Brains are any two OpenAI-compatible chat endpoints (config.json): "light" (e.g. a small local model) and "strong" (hosted).
Light chat goes to the light brain; harder turns go to the strong one; each falls back to the other. Every call is appended to a
JSONL dataset (messages in, raw reply out) so a smaller model can be fine-tuned later."""
import datetime as dt, json, re, time, urllib.request
from pathlib import Path
from . import conversation

HARD = re.compile(r"\b(why|how (do|does|did|would|could|can|should)|explain|compare|difference between|plan|figure out|help me|"
                  r"think (about|through|hard)|what should|walk me through|step by step|pros and cons|debug|analy[sz]e|summari[sz]e|"
                  r"write (me|a|an|up)|draft|and then|and also|do both)\b", re.I)
LOOKUP = re.compile(r"\b(look (it |that |this |something )?up|research|search)\b", re.I)
HARD_WORDS, STICKY_S, FOLLOW_MAX_S, LEAVING_MAX_S = 22, 120, 8, 5
LEAVING = re.compile(r"\b(be right back|brb|back in a (minute|sec|second|bit)|getting a (drink|coffee)|stepping away)\b", re.I)
BIO = re.compile(r"\b(i (also )?(do|make|play|write) music|i('m| am) a (musician|coder)|coding session)\b", re.I)  # invented self-descriptions

def wake_re(names, phrases=("computer",)):
    n = "|".join(re.escape(x) for x in names); p = "|".join(re.escape(x) for x in phrases)
    return re.compile(rf"\b({n})\b|(\b(hey|hi|hello|ok|okay|yo)[\s,.!]+({p})\b)|(^\W*({p})\b)", re.I)

def addressed(wake, text, last_spoke, dur=0.0, now=None):
    """Wake word, or a short follow-up within 60 s of the last reply, or a short send-off."""
    now = now or time.time()
    return bool(wake.search(text) or (now - last_spoke < 60 and dur <= FOLLOW_MAX_S) or (dur <= LEAVING_MAX_S and LEAVING.search(text)))

def trim(say, words=60):
    """Keep whole sentences up to the spoken-length limit."""
    if len(say.split()) <= words: return say
    out = ""
    for s in re.split(r"(?<=[.!?])\s+", say):
        if out and len((out + " " + s).split()) > words: break
        out = (out + " " + s).strip()
    return out or " ".join(say.split()[:words])

def ground(say):
    """Drop sentences that invent a biography; the model only knows this conversation."""
    kept = [x for x in re.split(r"(?<=[.!?])\s+", (say or "").strip()) if x and not BIO.search(x)]
    return " ".join(kept).strip() or "I don't know that."

class Harness:
    def __init__(self, config, dataset=None, busy=lambda: False):
        self.cfg, self.busy = config, busy
        self.dataset = Path(dataset) if dataset else None
        self.last = dict(brain=None, t=0.0)

    def route(self, text, now=None):
        """-> (brain, reason): 'strong' for harder turns, 'light' for chat."""
        now = now or time.time()
        if self.busy(): return "strong", "local machine busy"
        if conversation.day_requested(text): return "strong", "the day's log"
        if LOOKUP.search(text): return "strong", "research"
        m = HARD.search(text)
        if m: return "strong", "hard: " + m.group(0).lower()
        if len(text.split()) >= HARD_WORDS: return "strong", f"long ({len(text.split())} words)"
        if self.last["brain"] == "strong" and now - self.last["t"] < STICKY_S: return "strong", "same thread"
        return "light", "light chat"

    def _post(self, brain, msgs, max_tokens, timeout):
        b = self.cfg["brains"][brain]
        body = dict(model=b["model"], messages=msgs, **{b.get("max_tokens_key", "max_tokens"): max_tokens})
        h = {"Content-Type": "application/json"}
        if b.get("key_env"):
            import os; h["Authorization"] = "Bearer " + os.environ[b["key_env"]]
        t0 = time.time()
        r = json.load(urllib.request.urlopen(urllib.request.Request(b["url"], json.dumps(body).encode(), h), timeout=timeout))
        c = r["choices"][0]["message"]["content"]
        self.log(brain, msgs, c, round((time.time() - t0) * 1000))
        return c

    def log(self, brain, msgs, reply, ms):
        if not self.dataset: return
        try:
            self.dataset.parent.mkdir(parents=True, exist_ok=True)
            with open(self.dataset, "a") as f:
                f.write(json.dumps(dict(t=dt.datetime.now().isoformat(timespec="seconds"), brain=brain, messages=msgs, reply=reply, ms=ms), ensure_ascii=False) + "\n")
        except Exception: pass

    def reply(self, text, history=(), system=""):
        """-> dict(say, brain, route[, fallback]). Tries the routed brain, then the other."""
        msgs = [dict(role="system", content=(system + " " + conversation.guidance(text)).strip())]
        msgs += [dict(role=r, content=t) for r, t in list(history)[-16:]] + [dict(role="user", content=text)]
        first, reason = self.route(text)
        order = [first] + [b for b in ("light", "strong") if b != first]
        if self.busy(): order = ["strong"]
        why = []
        for brain in order:
            try:
                b = self.cfg["brains"][brain]
                say = ground(trim(self._post(brain, msgs, b.get("max_tokens", 200), b.get("timeout", 25)).strip()))
                self.last.update(brain=brain, t=time.time())
                d = dict(say=say, brain=brain, route=reason)
                if why: d["fallback"] = "; ".join(why)
                return d
            except Exception as e: why.append(f"{brain}: {str(e)[:80]}")
        raise RuntimeError("; ".join(why))
