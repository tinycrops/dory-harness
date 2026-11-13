"""Chat log -> a Discord webhook. The URL comes from the DISCORD_WEBHOOK environment variable, never from code.
Every post asks Discord to return the message (`wait=true`), so delivery is proven by a message id, not assumed. Mentions are never parsed.
  post(text, block=False)        exchange(heard, say, brain, route)        post_file(path, text, block=False)
With block=True the call returns the message dict ({"id", "channel_id", ...}) or raises; otherwise it runs on a background thread and failures go to the `errors` list."""
import json, mimetypes, os, threading, urllib.request, uuid
from pathlib import Path
UA = {"User-Agent": "dory-harness/1.1"}
errors = []                                   # background failures land here instead of vanishing
LIMIT = 10 * 1024 * 1024                      # Discord's per-file limit

def _url():
    u = os.environ.get("DISCORD_WEBHOOK")
    if not u: raise RuntimeError("DISCORD_WEBHOOK is not set")
    return u + ("&" if "?" in u else "?") + "wait=true"

def _run(make_req, block):
    def go():
        try: return json.load(urllib.request.urlopen(make_req(_url()), timeout=60))
        except Exception as e:
            errors.append(str(e)); raise
    if block: return go()
    t = threading.Thread(target=lambda: _swallow(go), daemon=True); t.start(); return t
def _swallow(f):
    try: f()
    except Exception: pass

def post(content, block=False):
    body = json.dumps(dict(content=content[:1990], allowed_mentions=dict(parse=[]))).encode()
    return _run(lambda u: urllib.request.Request(u, body, {"Content-Type": "application/json", **UA}), block)

def exchange(heard, say, brain="assistant", route=None, block=False):
    return post(f"**User:** {heard}\n**{brain}:** {say}" + (f"\n-# route: {route}" if route else ""), block)

def post_file(path, content="", name=None, block=False):
    p = Path(path); data = p.read_bytes(); name = name or p.name
    if len(data) > LIMIT: raise ValueError(f"{name} is over Discord's 10 MB limit")
    b = uuid.uuid4().hex; ct = mimetypes.guess_type(name)[0] or "application/octet-stream"
    payload = json.dumps(dict(content=content[:1990], allowed_mentions=dict(parse=[]))).encode()
    body = (f'--{b}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n').encode() + payload + \
           (f'\r\n--{b}\r\nContent-Disposition: form-data; name="files[0]"; filename="{name}"\r\nContent-Type: {ct}\r\n\r\n').encode() + data + f'\r\n--{b}--\r\n'.encode()
    return _run(lambda u: urllib.request.Request(u, body, {"Content-Type": f"multipart/form-data; boundary={b}", **UA}), block)
