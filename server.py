#!/usr/bin/env python3
"""
YouTube Transcript Downloader — local server
Run:  python server.py
Then open:  http://localhost:7842
"""

import http.server
import socketserver
import json
import os
import re
import sys
import webbrowser
import threading

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import (
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
        YouTubeTranscriptApiException,
    )
except ImportError:
    print("\nERROR: youtube-transcript-api is not installed.")
    print("Run:  pip install youtube-transcript-api\n")
    sys.exit(1)

PORT = 7842
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "transcripts")


# ── Helpers (same logic as yt_transcripts.py, kept in sync) ──────────────────

def extract_video_id(url: str) -> str | None:
    url = url.strip()
    patterns = [
        r"(?:v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]{11}", url):
        return url
    return None


def sanitize_filename(name: str, max_length: int = 80) -> str:
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    name = name.replace("\n", " ").replace("\r", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return name[:max_length] if name else "transcript"


def get_unique_path(directory: str, base_name: str) -> str:
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{base_name}.txt")
    counter = 2
    while os.path.exists(path):
        path = os.path.join(directory, f"{base_name}_{counter}.txt")
        counter += 1
    return path


def fetch_and_save(url: str) -> dict:
    """
    Fetch transcript for one URL. Returns a result dict:
      { ok: bool, url: str, filename: str|None, error: str|None }
    """
    video_id = extract_video_id(url)
    if video_id is None:
        return {"ok": False, "url": url, "filename": None,
                "error": "Could not parse a video ID from this URL."}

    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)

        # Prefer manual EN → auto EN → any language
        try:
            transcript = transcript_list.find_manually_created_transcript(["en"])
        except Exception:
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
            except Exception:
                transcript = next(iter(transcript_list))

        fetched = transcript.fetch()
        lines = [s.text.strip() for s in fetched if s.text.strip()]
        text = "\n".join(lines)

        file_name_base = sanitize_filename(video_id)
        file_path = get_unique_path(OUTPUT_DIR, file_name_base)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text)

        return {"ok": True, "url": url,
                "filename": os.path.basename(file_path), "error": None}

    except TranscriptsDisabled:
        return {"ok": False, "url": url, "filename": None,
                "error": "Transcripts are disabled for this video."}
    except VideoUnavailable:
        return {"ok": False, "url": url, "filename": None,
                "error": "Video is unavailable (private, deleted, or invalid ID)."}
    except NoTranscriptFound:
        return {"ok": False, "url": url, "filename": None,
                "error": "No transcript found in any language."}
    except YouTubeTranscriptApiException as exc:
        return {"ok": False, "url": url, "filename": None,
                "error": str(exc).splitlines()[0]}
    except Exception as exc:
        return {"ok": False, "url": url, "filename": None,
                "error": f"Unexpected error: {exc}"}


# ── HTTP Handler ──────────────────────────────────────────────────────────────

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        # Suppress default access log noise
        pass

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: str, mime: str):
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            index_path = os.path.join(BASE_DIR, "index.html")
            if os.path.exists(index_path):
                self._send_file(index_path, "text/html; charset=utf-8")
            else:
                self.send_error(404, "index.html not found")
        elif self.path == "/output-dir":
            self._send_json({"dir": OUTPUT_DIR})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/transcripts":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            payload = json.loads(body.decode("utf-8"))
            urls = payload.get("urls", [])
            if not isinstance(urls, list):
                raise ValueError("'urls' must be a list")
        except (json.JSONDecodeError, ValueError) as exc:
            self._send_json({"error": str(exc)}, status=400)
            return

        results = [fetch_and_save(u) for u in urls if u.strip()]
        self._send_json({"results": results})


# ── Entry point ───────────────────────────────────────────────────────────────

class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    server = ThreadedServer(("127.0.0.1", PORT), Handler)
    url = f"http://localhost:{PORT}"

    print(f"\n  YouTube Transcript Downloader")
    print(f"  ─────────────────────────────")
    print(f"  Server running at {url}")
    print(f"  Transcripts saved to: {OUTPUT_DIR}")
    print(f"\n  Opening browser... (Ctrl+C to stop)\n")

    # Open browser after a short delay so the server is ready
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.\n")


if __name__ == "__main__":
    main()
