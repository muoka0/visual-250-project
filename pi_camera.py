"""
ClothingID — Raspberry Pi camera node  (HTTP edition)
Runs on the Pi (same WiFi as the server).

Flow:
  1. Poll GET /trigger-check on the server every PI_POLL_INTERVAL seconds
  2. When trigger fires → capture JPEG with Picamera2 (falls back to OpenCV)
  3. POST base64 image to /analyze → server runs Claude + SerpApi
  4. Print result to terminal + drive OLED if attached

Trigger sources:
  • Dashboard "Capture" button  (POST /trigger → server sets flag → Pi picks up)
  • Physical Pi GPIO button      (set GPIO_BUTTON_PIN below; 0 = disabled)
  • Direct keyboard              (Ctrl-T in this terminal when GPIO disabled)

Install deps (Pi):
  pip install requests pillow picamera2
  # OpenCV fallback:  pip install opencv-python-headless
  # OLED (optional):  pip install luma.oled
"""

import base64, io, json, logging, sys, time, threading
import requests
from config import SERVER_IP, FLASK_PORT, PI_POLL_INTERVAL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [Pi] %(message)s")
log = logging.getLogger(__name__)

SERVER_BASE     = f"http://{SERVER_IP}:{FLASK_PORT}"
GPIO_BUTTON_PIN = 0    # BCM pin number; 0 = disabled (use dashboard trigger)


# ── Camera backend ────────────────────────────────────────
def capture_jpeg(quality: int = 85) -> bytes:
    try:
        from picamera2 import Picamera2
        cam = Picamera2()
        cam.configure(cam.create_still_configuration(main={"size": (1280, 720)}))
        cam.start()
        time.sleep(0.5)
        buf = io.BytesIO()
        cam.capture_file(buf, format="jpeg")
        cam.stop(); cam.close()
        return buf.getvalue()
    except ImportError:
        log.warning("picamera2 not found, trying OpenCV…")

    try:
        import cv2
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        time.sleep(0.3)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise RuntimeError("OpenCV failed to grab frame")
        _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes()
    except ImportError:
        raise RuntimeError("No camera library found — install picamera2 or opencv-python-headless")


# ── OLED helper ───────────────────────────────────────────
def oled_show(text: str):
    try:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        from luma.core.render import canvas
        dev = ssd1306(i2c(port=1, address=0x3C), width=128, height=64)
        with canvas(dev) as draw:
            for i, line in enumerate(text.split("\n")[:4]):
                draw.text((0, i * 16), line[:21], fill="white")
    except Exception:
        pass


# ── Capture → upload ──────────────────────────────────────
def scan():
    log.info("Capturing image…")
    oled_show("Scanning…")
    try:
        jpeg = capture_jpeg()
        b64  = base64.b64encode(jpeg).decode()
        log.info("Uploading %d KB to %s/analyze…", len(jpeg) // 1024, SERVER_BASE)
        oled_show("Uploading…")
        resp = requests.post(
            f"{SERVER_BASE}/analyze",
            json={"image": b64, "media_type": "image/jpeg"},
            timeout=60,
        )
        resp.raise_for_status()
        result = resp.json()
        _print_result(result)
        oled_show(f"{result.get('item_name','?')[:20]}\n"
                  f"{result.get('price_range','')}\n"
                  f"{', '.join(result.get('tags',[])[:2])}")
    except Exception as e:
        log.exception("Scan failed")
        oled_show(f"Error:\n{str(e)[:40]}")


def _print_result(r: dict):
    w = 56
    bar = "━" * w
    log.info(bar)
    log.info("  %-12s %s", "Item:",   r.get("item_name", "?"))
    log.info("  %-12s %s", "Price:",  r.get("price_range", ""))
    log.info("  %-12s %s", "Style:",  r.get("style_description", "")[:80])
    log.info("  %-12s %s", "Tags:",   ", ".join(r.get("tags", [])[:5]))
    log.info("  %-12s %s", "Brands:", ", ".join(r.get("brand_guesses", [])))
    for h in r.get("shopping_results", [])[:3]:
        log.info("  🛍  %-42s %s", h["title"][:42], h["price"])
    log.info(bar)


# ── GPIO button (optional) ────────────────────────────────
def _gpio_watcher():
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        log.info("GPIO button watcher active on BCM pin %d", GPIO_BUTTON_PIN)
        last = True
        while True:
            state = GPIO.input(GPIO_BUTTON_PIN)
            if state == GPIO.LOW and last == GPIO.HIGH:
                log.info("GPIO button pressed")
                scan()
                time.sleep(0.5)
            last = state
            time.sleep(0.05)
    except Exception as e:
        log.warning("GPIO watcher error: %s", e)


# ── Main loop ─────────────────────────────────────────────
def main():
    log.info("Pi node started — server: %s", SERVER_BASE)
    log.info("Polling /trigger-check every %ds. Use dashboard or GPIO button to scan.", PI_POLL_INTERVAL)

    if GPIO_BUTTON_PIN:
        threading.Thread(target=_gpio_watcher, daemon=True).start()

    while True:
        try:
            r = requests.get(f"{SERVER_BASE}/trigger-check", timeout=5)
            if r.status_code == 200 and r.json().get("trigger"):
                scan()
        except requests.RequestException as e:
            log.warning("Server unreachable (%s) — retrying…", e)
        except KeyboardInterrupt:
            log.info("Exiting.")
            sys.exit(0)

        time.sleep(PI_POLL_INTERVAL)


if __name__ == "__main__":
    main()
