# YouTube Transcripts Extractor

First time only:

Right-click setup_and_run.ps1 → Run with PowerShell. It will install youtube-transcript-api and launch the server.
Run server.py after. It will launch into a browser window where you can download your transcripts.


How it works:

server.py is a tiny local web server (no Flask, no extra installs beyond the transcript library)
index.html is the UI — paste links, hit the button, watch each one resolve in real time
Transcripts land in a transcripts/ folder right next to the scripts, and the UI tells you the exact path
