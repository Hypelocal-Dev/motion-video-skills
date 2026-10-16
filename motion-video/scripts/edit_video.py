#!/usr/bin/env python3
"""Open a local editor to watch a render and leave timed notes for Claude.

The editor is a page served from this machine only (127.0.0.1). Pause on a frame, type a
note, drag a box to mark an area, and drop in an image or GIF. Notes are saved in the
project's review/notes.json, with a still of each noted frame in review/frames/. Files
you drop in are saved to assets/incoming/. Clicking "Send to Claude" releases `wait`.

Examples:
  edit_video.py open ~/videos/spring-launch     # start the editor if needed and open it
  edit_video.py wait ~/videos/spring-launch     # block until notes are sent, then print them
  edit_video.py notes ~/videos/spring-launch    # print open notes (--all for every note)
  edit_video.py reply ~/videos/spring-launch 3 "Moved the logo up 40px." --done
  edit_video.py stop ~/videos/spring-launch
"""

from __future__ import annotations

import argparse
import base64
import contextlib
import fcntl
import json
import mimetypes
import os
import re
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

UI = Path(__file__).resolve().parent / "edit_video.html"
PORTS = range(4400, 4500)
VIDEO = {".mp4", ".mov", ".webm", ".m4v"}
ATTACHABLE = VIDEO | {".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".svg",
                      ".wav", ".mp3", ".m4a", ".aac", ".ogg"}
MAX_UPLOAD = 200 * 1024 * 1024
MAX_JSON = 20 * 1024 * 1024
SKIP_DIRS = {"review", "renders", "node_modules", ".hyperframes", "incoming", ".git"}
_probes: dict[tuple, dict] = {}


# ---------------------------------------------------------------- project files

def project(path: str) -> Path:
    root = Path(path).expanduser().resolve()
    if not (root / "index.html").exists():
        sys.exit(f"{root} is not a video project (no index.html)")
    return root


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n")
    os.replace(tmp, path)


def read_doc(root: Path) -> dict:
    path = root / "review" / "notes.json"
    try:
        doc = json.loads(path.read_text())
    except FileNotFoundError:
        return {"version": 1, "sent": None, "picked": None, "notes": []}
    except json.JSONDecodeError as e:
        raise ValueError(f"{path} is not valid JSON ({e}); fix it or move it aside") from e
    doc.setdefault("notes", [])
    return doc


@contextlib.contextmanager
def locked(root: Path):
    (root / "review").mkdir(exist_ok=True)
    with open(root / "review" / ".lock", "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        yield


def update_doc(root: Path, change):
    """Read, change and save notes.json under a lock shared by the server and the CLI."""
    with locked(root):
        doc = read_doc(root)
        result = change(doc)
        write_json(root / "review" / "notes.json", doc)
        return result


def find_note(doc: dict, note_id: int) -> dict | None:
    return next((n for n in doc["notes"] if n.get("id") == note_id), None)


def pending(doc: dict) -> bool:
    return bool(doc.get("sent")) and (not doc.get("picked") or doc["sent"] > doc["picked"])


def probe(path: Path) -> dict | None:
    """Size, fps and duration of a render, or None while it is still being written."""
    st = path.stat()
    key = (str(path), st.st_mtime, st.st_size)
    if key in _probes:
        return _probes[key]
    info: dict | None = {}
    if shutil.which("ffprobe"):
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate:format=duration", "-of", "json", str(path)],
            capture_output=True, text=True,
        )
        try:
            data = json.loads(out.stdout)
            stream = data["streams"][0]
            num, _, den = stream["r_frame_rate"].partition("/")
            info = {"width": stream["width"], "height": stream["height"],
                    "fps": round(float(num) / float(den or 1), 3), "duration": float(data["format"]["duration"])}
        except (ValueError, KeyError, IndexError, ZeroDivisionError):
            info = None
    _probes[key] = info
    return info


def renders(root: Path) -> list[dict]:
    folder = root / "renders"
    if not folder.is_dir():
        return []
    out = []
    for p in folder.iterdir():
        if p.suffix.lower() not in VIDEO or not p.is_file():
            continue
        st = p.stat()
        if time.time() - st.st_mtime < 2:  # still being written
            continue
        info = probe(p)
        if info is None:
            continue
        out.append({"name": p.name, "mtime": st.st_mtime, "size": st.st_size, **info})
    return sorted(out, key=lambda r: r["mtime"], reverse=True)


def next_render(root: Path) -> str:
    taken = [int(m.group(1)) for p in (root / "renders").glob("edit-*.mp4")
             if (m := re.fullmatch(r"edit-(\d+)\.mp4", p.name))]
    return f"renders/edit-{max(taken, default=0) + 1}.mp4"


def source_mtime(root: Path) -> float:
    newest = 0.0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for f in filenames:
            if f.endswith(".md") or f.startswith("."):
                continue
            with contextlib.suppress(OSError):
                newest = max(newest, os.stat(os.path.join(dirpath, f)).st_mtime)
    return newest


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def listening(root: Path) -> bool:
    try:
        return alive(json.loads((root / "review" / "listener.json").read_text())["pid"])
    except (OSError, ValueError, KeyError):
        return False


def running(root: Path) -> dict | None:
    """The editor server for this project, if one is up."""
    try:
        info = json.loads((root / "review" / "server.json").read_text())
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(info["url"] + "api/ping", timeout=1) as r:
            if json.loads(r.read()).get("root") == str(root):
                return info
    except (OSError, ValueError, KeyError):
        pass
    return None


def safe_name(name: str) -> str:
    stem, ext = os.path.splitext(os.path.basename(name))
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-.") or "file"
    return stem[:80] + ext.lower()


# ---------------------------------------------------------------- server

class Handler(BaseHTTPRequestHandler):
    server_version = "edit-video"

    @property
    def root(self) -> Path:
        return self.server.root  # type: ignore[attr-defined]

    def log_message(self, fmt, *args):  # keep the log to errors
        pass

    # --- plumbing

    def _host_ok(self) -> bool:
        port = self.server.server_port
        return self.headers.get("Host", "") in {f"127.0.0.1:{port}", f"localhost:{port}"}

    def _write_ok(self) -> bool:
        # A custom header forces a CORS preflight, which this server never answers, so other
        # websites open in the same browser can't post notes or files here.
        origin = self.headers.get("Origin")
        return self._host_ok() and self.headers.get("X-Editor") == "1" and (
            origin is None or origin == f"http://{self.headers.get('Host')}")

    def _json(self, data, status: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _error(self, status: int, message: str) -> None:
        self._json({"error": message}, status)

    def _body(self, limit: int = MAX_JSON) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > limit:
            raise ValueError("too large")
        return self.rfile.read(length)

    def _send_file(self, path: Path, extra: dict | None = None) -> None:
        size = path.stat().st_size
        start, end = 0, size - 1
        rng = re.fullmatch(r"bytes=(\d*)-(\d*)", self.headers.get("Range", ""))
        if rng and (rng.group(1) or rng.group(2)):
            if rng.group(1):
                start = int(rng.group(1))
                end = min(int(rng.group(2)), size - 1) if rng.group(2) else size - 1
            else:
                start = max(0, size - int(rng.group(2)))
            if start > end or start >= size:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Cache-Control", "no-cache")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        with open(path, "rb") as fh:
            fh.seek(start)
            left = end - start + 1
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                while left > 0:
                    chunk = fh.read(min(256 * 1024, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)

    def _route(self) -> tuple[str, list[str]]:
        path = unquote(urlparse(self.path).path)
        return path, [p for p in path.split("/") if p]

    # --- reads

    def do_GET(self):
        if not self._host_ok():
            return self._error(403, "use http://127.0.0.1")
        path, parts = self._route()
        try:
            if path == "/":
                body = UI.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            elif path == "/api/ping":
                self._json({"root": str(self.root)})
            elif path == "/api/state":
                rs = renders(self.root)
                self._json({
                    "project": self.root.name,
                    "root": str(self.root),
                    "renders": rs,
                    "nextRender": next_render(self.root),
                    "stale": bool(rs) and source_mtime(self.root) > rs[0]["mtime"],
                    "listening": listening(self.root),
                    "doc": read_doc(self.root),
                })
            elif len(parts) == 2 and parts[0] == "renders":
                target = self.root / "renders" / parts[1]
                if "/" in parts[1] or parts[1].startswith(".") or not target.is_file():
                    return self._error(404, "no such render")
                self._send_file(target)
            elif parts and parts[0] == "files":
                rel = "/".join(parts[1:])
                target = (self.root / rel).resolve()
                allowed = [(self.root / "review").resolve(), (self.root / "assets" / "incoming").resolve()]
                if not any(target.is_relative_to(a) for a in allowed) or not target.is_file():
                    return self._error(404, "not found")
                self._send_file(target, {"X-Content-Type-Options": "nosniff",
                                         "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'"})
            else:
                self._error(404, "not found")
        except ValueError as e:
            self._error(500, str(e))

    # --- writes

    def do_POST(self):
        if not self._write_ok():
            return self._error(403, "forbidden")
        path, parts = self._route()
        try:
            if path == "/api/notes":
                return self._json(self._create(json.loads(self._body())))
            if len(parts) == 4 and parts[:2] == ["api", "notes"] and parts[3] == "replies":
                return self._json(self._reply(int(parts[2]), json.loads(self._body())))
            if path == "/api/upload":
                return self._json(self._upload())
            if path == "/api/send":
                def send(doc):
                    doc["sent"] = now()
                    return doc
                return self._json(update_doc(self.root, send))
            self._error(404, "not found")
        except (ValueError, KeyError, TypeError) as e:
            self._error(400, str(e))

    def do_PATCH(self):
        if not self._write_ok():
            return self._error(403, "forbidden")
        _, parts = self._route()
        if len(parts) != 3 or parts[:2] != ["api", "notes"]:
            return self._error(404, "not found")
        try:
            note_id, body = int(parts[2]), json.loads(self._body())

            def change(doc):
                note = find_note(doc, note_id)
                if note is None:
                    raise KeyError(f"no note {note_id}")
                if body.get("status") in ("open", "done"):
                    if body["status"] == "open" and note.get("status") == "done":
                        note["reopened"] = now()  # the page counts a reopened note as unsent
                    note["status"] = body["status"]
                if isinstance(body.get("text"), str) and body["text"].strip():
                    note["text"] = body["text"].strip()
                return note
            self._json(update_doc(self.root, change))
        except (ValueError, KeyError) as e:
            self._error(400, str(e))

    def do_DELETE(self):
        if not self._write_ok():
            return self._error(403, "forbidden")
        _, parts = self._route()
        if len(parts) != 3 or parts[:2] != ["api", "notes"] or not parts[2].isdigit():
            return self._error(404, "not found")
        note_id = int(parts[2])

        def remove(doc):
            doc["notes"] = [n for n in doc["notes"] if n.get("id") != note_id]
        update_doc(self.root, remove)
        with contextlib.suppress(OSError):
            (self.root / "review" / "frames" / f"{note_id}.jpg").unlink()
        self._json({"ok": True})

    def _create(self, body: dict) -> dict:
        text = str(body.get("text", "")).strip()
        if not text:
            raise ValueError("a note needs some text")
        fps = float(body.get("fps") or 30)
        frame = int(body.get("frame", 0))
        end = body.get("end")
        region = body.get("region")
        if region is not None:
            region = {k: round(float(region[k])) for k in ("x", "y", "w", "h")}
        files = [str(f) for f in body.get("files", []) if isinstance(f, str)]
        snapshot = body.get("snapshot")

        def add(doc):
            note_id = max((n.get("id", 0) for n in doc["notes"]), default=0) + 1
            note = {
                "id": note_id,
                "render": str(body.get("render", "")),
                "time": round(frame / fps, 3),
                "end": round(float(end), 3) if end is not None else None,
                "frame": frame,
                "fps": fps,
                "size": body.get("size"),
                "region": region,
                "text": text,
                "files": files,
                "snapshot": None,
                "status": "open",
                "created": now(),
                "replies": [],
            }
            if isinstance(snapshot, str) and snapshot.startswith("data:image/jpeg;base64,"):
                frames = self.root / "review" / "frames"
                frames.mkdir(parents=True, exist_ok=True)
                (frames / f"{note_id}.jpg").write_bytes(base64.b64decode(snapshot.split(",", 1)[1]))
                note["snapshot"] = f"review/frames/{note_id}.jpg"
            doc["notes"].append(note)
            return note
        return update_doc(self.root, add)

    def _reply(self, note_id: int, body: dict) -> dict:
        text = str(body.get("text", "")).strip()
        if not text:
            raise ValueError("empty reply")

        def add(doc):
            note = find_note(doc, note_id)
            if note is None:
                raise KeyError(f"no note {note_id}")
            note.setdefault("replies", []).append({"by": "you", "text": text, "at": now()})
            note["status"] = "open"  # replying to a done note reopens it
            return note
        return update_doc(self.root, add)

    def _upload(self) -> dict:
        name = safe_name(unquote(self.headers.get("X-Filename", "file")))
        stem, ext = os.path.splitext(name)
        if ext not in ATTACHABLE:
            raise ValueError(f"{ext or 'that file type'} isn't supported; attach an image, GIF, video or audio file")
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_UPLOAD:
            raise ValueError("files over 200 MB aren't supported")
        folder = self.root / "assets" / "incoming"
        folder.mkdir(parents=True, exist_ok=True)
        target, n = folder / name, 2
        while target.exists():
            target, n = folder / f"{stem}-{n}{ext}", n + 1
        with open(target, "wb") as fh:
            left = length
            while left > 0:
                chunk = self.rfile.read(min(256 * 1024, left))
                if not chunk:
                    break
                fh.write(chunk)
                left -= len(chunk)
        return {"path": str(target.relative_to(self.root)), "name": target.name}


def serve(root: Path, port: int | None) -> None:
    server = None
    for p in [port] if port else PORTS:
        try:
            server = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            break
        except OSError:
            continue
    if server is None:
        sys.exit("no free port between 4400 and 4499")
    server.daemon_threads = True
    server.root = root  # type: ignore[attr-defined]
    url = f"http://127.0.0.1:{server.server_port}/"
    info_path = root / "review" / "server.json"
    write_json(info_path, {"pid": os.getpid(), "port": server.server_port, "url": url, "started": now()})
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    print(f"editor running at {url} for {root}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        with contextlib.suppress(OSError, ValueError, KeyError):
            if json.loads(info_path.read_text())["pid"] == os.getpid():
                info_path.unlink()


# ---------------------------------------------------------------- text output

def fmt_time(t: float) -> str:
    cs = round(t * 100)
    return f"{cs // 6000}:{cs % 6000 / 100:05.2f}"


def describe(doc: dict, root: Path, show_all: bool) -> str:
    notes = [n for n in doc["notes"] if show_all or n.get("status") != "done"]
    rs = renders(root)
    lines = [f"Project: {root}"]
    if rs:
        r = rs[0]
        lines.append(f"Newest render: renders/{r['name']} ({r.get('width')}x{r.get('height')}, "
                     f"{r.get('fps')} fps, {r.get('duration', 0):.2f}s). Next render: {next_render(root)}")
    open_count = sum(1 for n in doc["notes"] if n.get("status") != "done")
    lines.append(f"{open_count} open, {len(doc['notes']) - open_count} done.")
    if not notes:
        lines.append("No notes to show.")
    for n in notes:
        span = f"{n['time']:.2f}s (frame {n['frame']})"
        if n.get("end") is not None:
            span += f" to {n['end']:.2f}s"
        status = " [done]" if n.get("status") == "done" else ""
        lines += ["", f"#{n['id']} at {span}, shown as {fmt_time(n['time'])} in the editor, "
                      f"left on {n.get('render') or '?'}{status}"]
        lines += [f"  {line}" for line in n["text"].splitlines()]
        if n.get("region"):
            g, size = n["region"], n.get("size") or ["?", "?"]
            lines.append(f"  Area: x={g['x']} y={g['y']} w={g['w']} h={g['h']} px in the {size[0]}x{size[1]} frame")
        for f in n.get("files") or []:
            lines.append(f"  File: {f}")
        if n.get("snapshot"):
            lines.append(f"  Still: {n['snapshot']}")
        for r in n.get("replies") or []:
            who = "Claude" if r.get("by") == "claude" else "Reviewer"
            lines.append(f"  {who}: {r['text']}")
    lines += ["", "Reply to each note: edit_video.py reply <dir> <id> \"what changed\" --done"]
    return "\n".join(lines)


# ---------------------------------------------------------------- commands

def cmd_open(args) -> None:
    root = project(args.dir)
    info = running(root)
    if info is None:
        (root / "review").mkdir(exist_ok=True)
        with open(root / "review" / "server.log", "a") as log:
            subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "serve", str(root)],
                             stdin=subprocess.DEVNULL, stdout=log, stderr=log, cwd=root, start_new_session=True)
        for _ in range(50):
            time.sleep(0.2)
            if (info := running(root)) is not None:
                break
        else:
            sys.exit(f"the editor didn't start; see {root / 'review' / 'server.log'}")
    url = info["url"]
    if not args.no_open:
        webbrowser.open(url)
    print(f"editor: {url}")
    rs = renders(root)
    if not rs:
        print(f"no render yet. Render one to {next_render(root)} and the editor loads it.")
    else:
        print(f"newest render: renders/{rs[0]['name']}")
        if source_mtime(root) > rs[0]["mtime"]:
            print(f"the composition changed after that render. Render again to {next_render(root)}.")
    doc = read_doc(root)
    print(f"notes: {sum(1 for n in doc['notes'] if n.get('status') != 'done')} open")


def _pick(doc: dict) -> bool:
    if pending(doc):
        doc["picked"] = doc["sent"]
        return True
    return False


def cmd_wait(args) -> None:
    root = project(args.dir)
    listener = root / "review" / "listener.json"
    write_json(listener, {"pid": os.getpid(), "since": now()})
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    deadline = time.time() + args.timeout if args.timeout else None
    try:
        while True:
            if pending(read_doc(root)) and update_doc(root, _pick):
                print(describe(read_doc(root), root, show_all=False))
                return
            if deadline and time.time() > deadline:
                sys.exit("no notes were sent before the timeout")
            time.sleep(1)
    finally:
        with contextlib.suppress(OSError, ValueError, KeyError):
            if json.loads(listener.read_text())["pid"] == os.getpid():
                listener.unlink()


def cmd_notes(args) -> None:
    root = project(args.dir)
    doc = read_doc(root)
    print(json.dumps(doc, indent=2) if args.json else describe(doc, root, args.all))


def cmd_reply(args) -> None:
    root = project(args.dir)

    def add(doc):
        note = find_note(doc, args.id)
        if note is None:
            sys.exit(f"no note #{args.id}")
        note.setdefault("replies", []).append({"by": "claude", "text": args.text.strip(), "at": now()})
        if args.done:
            note["status"] = "done"
    update_doc(root, add)
    print(f"replied to #{args.id}" + (" and marked it done" if args.done else ""))


def cmd_stop(args) -> None:
    root = project(args.dir)
    info = running(root)
    if info is None:
        print("the editor isn't running")
        return
    os.kill(info["pid"], signal.SIGTERM)
    print(f"stopped the editor at {info['url']}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open", help="start the editor if needed and open it in the browser")
    o.add_argument("dir", nargs="?", default=".")
    o.add_argument("--no-open", action="store_true", help="print the address without opening a browser")
    s = sub.add_parser("serve", help="run the editor in the foreground")
    s.add_argument("dir", nargs="?", default=".")
    s.add_argument("--port", type=int)
    w = sub.add_parser("wait", help="block until notes are sent from the editor, then print them")
    w.add_argument("dir", nargs="?", default=".")
    w.add_argument("--timeout", type=float, default=0, help="give up after this many seconds (default: never)")
    n = sub.add_parser("notes", help="print the notes")
    n.add_argument("dir", nargs="?", default=".")
    n.add_argument("--all", action="store_true", help="include done notes")
    n.add_argument("--json", action="store_true", help="print the raw notes.json")
    r = sub.add_parser("reply", help="reply to a note as Claude")
    r.add_argument("dir")
    r.add_argument("id", type=int)
    r.add_argument("text")
    r.add_argument("--done", action="store_true", help="mark the note done")
    t = sub.add_parser("stop", help="stop the editor")
    t.add_argument("dir", nargs="?", default=".")
    args = p.parse_args()

    try:
        if args.cmd == "serve":
            serve(project(args.dir), args.port)
        else:
            commands = {"open": cmd_open, "wait": cmd_wait, "notes": cmd_notes, "reply": cmd_reply, "stop": cmd_stop}
            commands[args.cmd](args)
    except ValueError as e:  # a broken notes.json
        sys.exit(str(e))


if __name__ == "__main__":
    main()
