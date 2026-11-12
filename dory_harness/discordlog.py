"""Chat log -> a Discord webhook. The URL comes from the DISCORD_WEBHOOK environment variable, never from code.
Posting runs on a background thread and never raises, so Discord being slow cannot delay a reply. No mentions are ever parsed."""
import json, mimetypes, os, threading, urllib.request, uuid
from pathlib import Path
UA = {"User-Agent": "dory-harness/1.0"}

def _send(req_fn):
    url = os.environ.get("DISCORD_WEBHOOK")
    if not url: return
    try: urllib.request.urlopen(req_fn(url), timeout=60).read()
    except Exception: pass

def post(content):
    body = json.dumps(dict(content=content[:1990], allowed_mentions=dict(parse=[]))).encode()
    t = threading.Thread(target=_send, args=(lambda u: urllib.request.Request(u, body, {"Content-Type": "application/json", **UA}),), daemon=True); t.start(); return t

def exchange(heard, say, brain="assistant", route=None):
    post(f"**User:** {heard}\n**{brain}:** {say}" + (f"\n-# route: {route}" if route else ""))

def post_file(path, content="", name=None):
    """Attach a file (<= 10 MB, Discord's limit) to a message."""
    p = Path(path); data = p.read_bytes(); name = name or p.name
    if len(data) > 10 * 1024 * 1024: raise ValueError(f"{name} is over Discord's 10 MB limit")
    b = uuid.uuid4().hex; ct = mimetypes.guess_type(name)[0] or "application/octet-stream"
    payload = json.dumps(dict(content=content[:1990], allowed_mentions=dict(parse=[]))).encode()
    body = (f'--{b}\r\nContent-Disposition: form-data; name="payload_json"\r\nContent-Type: application/json\r\n\r\n').encode() + payload + \
           (f'\r\n--{b}\r\nContent-Disposition: form-data; name="files[0]"; filename="{name}"\r\nContent-Type: {ct}\r\n\r\n').encode() + data + f'\r\n--{b}--\r\n'.encode()
    t = threading.Thread(target=_send, args=(lambda u: urllib.request.Request(u, body, {"Content-Type": f"multipart/form-data; boundary={b}", **UA}),)); t.start(); return t
