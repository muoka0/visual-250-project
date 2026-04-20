"""
ClothingID — Node 3A  terminal display
Run this on any laptop on the same WiFi as the server.

Polls GET /latest every 3 seconds and redraws a box that mimics the
128×64 OLED readout. ANSI colours; works in any modern terminal.

Usage:
  python display.py
  python display.py --server 10.23.198.21 --port 5000

Install deps:
  pip install requests
"""

import argparse, json, os, sys, time
import requests

# ── ANSI helpers ──────────────────────────────────────────
ESC   = "\033["
RESET = ESC + "0m"
CLEAR = "\033[2J\033[H"

def fg(r, g, b):     return f"{ESC}38;2;{r};{g};{b}m"
def bold():          return ESC + "1m"
def dim():           return ESC + "2m"

GREEN   = fg(74, 222, 128)
CYAN    = fg(103, 232, 249)
YELLOW  = fg(250, 204, 21)
MAGENTA = fg(232, 121, 249)
MUTED   = fg(120, 120, 150)
WHITE   = fg(230, 230, 240)


def _box(lines: list[str], width: int = 50) -> str:
    tl, tr, bl, br = "╔", "╗", "╚", "╝"
    h, v = "═", "║"
    top    = tl + h * (width - 2) + tr
    bottom = bl + h * (width - 2) + br
    rows   = [top]
    for line in lines:
        # strip ANSI for length calculation
        import re
        plain = re.sub(r'\033\[[^m]*m', '', line)
        pad   = max(0, width - 2 - len(plain))
        rows.append(v + line + " " * pad + v)
    rows.append(bottom)
    return "\n".join(rows)


def render(result: dict):
    W = 54
    rows = []

    # Header
    item  = result.get("item_name", "—")[:W-4]
    price = result.get("price_range", "")
    ts    = result.get("timestamp", "")
    rows.append(f"  {bold()}{GREEN}{item}{RESET}")
    rows.append(f"  {YELLOW}{price}{RESET}   {MUTED}{ts}{RESET}")
    rows.append(f"  {MUTED}{'─' * (W-4)}{RESET}")

    # Style (word-wrapped to W-4 chars)
    desc  = result.get("style_description", "")
    chunk = W - 6
    for i in range(0, min(len(desc), chunk * 2), chunk):
        rows.append(f"  {MUTED}{desc[i:i+chunk]}{RESET}")
    rows.append("")

    # Tags
    tags = result.get("tags", [])[:5]
    if tags:
        rows.append(f"  {CYAN}{'  '.join('#' + t for t in tags)}{RESET}")
        rows.append("")

    # Brands
    brands = result.get("brand_guesses", [])
    if brands:
        rows.append(f"  {MUTED}Brands: {WHITE}{', '.join(brands)}{RESET}")
        rows.append("")

    # Shopping hits
    hits = result.get("shopping_results", [])[:3]
    if hits:
        rows.append(f"  {bold()}{MAGENTA}Top results{RESET}")
        for h in hits:
            title = h.get("title", "")[:W-18]
            price_h = h.get("price", "")[:8]
            rows.append(f"  {WHITE}{title:<{W-18}}{RESET} {YELLOW}{price_h}{RESET}")
    rows.append("")

    # Search queries
    queries = result.get("search_queries", [])[:3]
    if queries:
        rows.append(f"  {MUTED}Search queries:{RESET}")
        for i, q in enumerate(queries, 1):
            rows.append(f"  {MUTED}{i}. {q[:W-6]}{RESET}")

    print(CLEAR, end="")
    print(_box(rows, width=W + 2))


def poll(server: str, port: int, interval: int):
    url      = f"http://{server}:{port}/latest"
    last_ts  = None
    spinner  = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    tick     = 0

    print(f"{GREEN}ClothingID terminal display{RESET}")
    print(f"{MUTED}Polling {url} every {interval}s — Ctrl-C to quit{RESET}\n")

    while True:
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                ts   = data.get("timestamp")
                if ts != last_ts:
                    last_ts = ts
                    render(data)
                    print(f"\n{MUTED}  Last update: {ts}  |  waiting for next scan…{RESET}")
                else:
                    sp = spinner[tick % len(spinner)]
                    sys.stdout.write(f"\r{MUTED}  {sp}  waiting…{RESET}   ")
                    sys.stdout.flush()
            elif r.status_code == 204:
                sys.stdout.write(f"\r{MUTED}  No results yet — is the server running?{RESET}   ")
                sys.stdout.flush()
        except requests.RequestException as e:
            sys.stdout.write(f"\r{MUTED}  Server unreachable: {e}{RESET}   ")
            sys.stdout.flush()
        except KeyboardInterrupt:
            print(f"\n{RESET}Exited.")
            sys.exit(0)

        tick += 1
        time.sleep(interval)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="ClothingID terminal display")
    ap.add_argument("--server",   default="10.23.198.21")
    ap.add_argument("--port",     type=int, default=5000)
    ap.add_argument("--interval", type=int, default=3, help="poll interval (seconds)")
    args = ap.parse_args()
    poll(args.server, args.port, args.interval)
