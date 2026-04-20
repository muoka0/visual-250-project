# ClothingID — EE250 Vision System (SSE edition)

Three-node IoT pipeline: Pi camera → Flask server → browser/terminal display.
No MQTT broker needed. No ESP32 required.

## Architecture

```
[Pi camera node]
   pi_camera.py
       │ polls /trigger-check (HTTP GET, every 2s)
       │ uploads image (HTTP POST /analyze)
       ▼
[Flask server — 10.23.198.21:5000]
   server.py
       │ calls Claude vision API
       │ calls SerpApi (Google Shopping)
       │ broadcasts result via Server-Sent Events
       ├─► GET /stream  ──────────────────────────► [Node 3B — browser]
       │                                                dashboard.html
       └─► GET /latest  ──────────────────────────► [Node 3A — terminal]
                                                        display.py
```

**Why SSE over MQTT?**
SSE is HTTP-native (no broker process, no extra library), inherently one-directional
(server→client — exactly what a display node needs), and auto-reconnects on drop.
Simpler dependency graph, easier to explain in a write-up.

---

## Quick-start

### 1. Edit `config.py` — two lines only

```python
ANTHROPIC_API_KEY = "sk-ant-..."        # ← paste your key
# SERVER_IP is already set to 10.23.198.21
```

### 2. Install server deps (laptop)

```bash
pip install flask anthropic "serpapi[google_search_results]"
```

### 3. Install Pi deps

```bash
pip install requests pillow picamera2
# OLED optional: pip install luma.oled
# OpenCV fallback: pip install opencv-python-headless
```

### 4. Run

```bash
# Laptop — terminal 1
python server.py
# → http://10.23.198.21:5000  (dashboard)

# Pi — terminal
python pi_camera.py

# Node 3A — any laptop on same WiFi
python display.py

# Node 3B — open in any browser
open http://10.23.198.21:5000
```

### 5. Trigger a scan

- **Dashboard** → click the **▶ Capture** button (sets server flag → Pi picks it up)
- **GPIO button** → set `GPIO_BUTTON_PIN` in `pi_camera.py` to your BCM pin
- **curl** → `curl -X POST http://10.23.198.21:5000/trigger`

### 6. Curl test (no Pi needed)

```bash
B64=$(base64 -i test.jpg)
curl -X POST http://10.23.198.21:5000/analyze \
     -H "Content-Type: application/json" \
     -d "{\"image\":\"$B64\"}" | python -m json.tool
```

---

## File map

```
VisualProject/
├── index.html       standalone browser demo (webcam → Claude direct)
├── config.py        all configuration — edit once
├── server.py        Flask + SSE + Claude + SerpApi
├── pi_camera.py     Node 1 — Pi capture → HTTP POST
├── display.py       Node 3A — terminal OLED mimic
├── dashboard.html   Node 3B — browser dashboard (served by Flask at /)
└── README.md
```

## Protocol reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Serve dashboard.html |
| `/analyze` | POST | Upload image (base64 JSON) → get analysis JSON |
| `/stream` | GET | SSE stream — subscribe for live results |
| `/latest` | GET | Most recent result as JSON (polling fallback) |
| `/trigger` | POST | Signal Pi to capture (dashboard button → Pi poll) |
| `/trigger-check` | GET | Pi calls this; returns `{trigger: true/false}` |
| `/health` | GET | Server status + connected SSE client count |
