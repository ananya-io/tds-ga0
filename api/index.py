import json
import math
from http.server import BaseHTTPRequestHandler

DATA = {
    "apac": {
        "lat": [188.22, 222.74, 210.99, 178.25, 186.69, 163.99, 114.98, 138.32, 181.21, 156.59, 160.78, 121.04],
        "up": [97.794, 99.471, 97.409, 97.17, 99.173, 97.4, 99.453, 99.406, 98.1, 98.163, 98.665, 98.895],
    },
    "emea": {
        "lat": [212.5, 201.33, 110.07, 108.92, 208.39, 123.48, 209.52, 197.5, 203.31, 121.28, 222.26, 120.86],
        "up": [99.189, 97.191, 99.477, 98.043, 99.098, 98.679, 98.962, 97.665, 98.286, 98.408, 97.441, 97.61],
    },
    "amer": {
        "lat": [129.66, 239.93, 146.43, 120.82, 125.17, 107.23, 215.55, 167.39, 209.34, 172.98, 187.97, 198.51],
        "up": [97.497, 99.085, 98.053, 97.286, 98.369, 97.562, 99.274, 97.51, 97.875, 97.991, 98.772, 98.143],
    },
}


def percentile(values, q):
    """Linear-interpolation percentile, matching numpy's default method."""
    ordered = sorted(values)
    rank = (len(ordered) - 1) * q
    low = math.floor(rank)
    frac = rank - low
    if low + 1 < len(ordered):
        return ordered[low] + frac * (ordered[low + 1] - ordered[low])
    return ordered[low]


def summarise(regions, threshold_ms):
    out = []
    for region in regions:
        bucket = DATA.get(region)
        if not bucket:
            continue
        lat = bucket["lat"]
        up = bucket["up"]
        out.append({
            "region": region,
            "avg_latency": round(sum(lat) / len(lat), 2),
            "p95_latency": round(percentile(lat, 0.95), 2),
            "avg_uptime": round(sum(up) / len(up), 3),
            "breaches": sum(1 for v in lat if v > threshold_ms),
        })
    return out


class handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS, GET")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Max-Age", "86400")

    def _json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        self._json({"status": "ok", "regions": list(DATA.keys())})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw) if raw.strip() else {}
        except ValueError:
            payload = {}
        regions = payload.get("regions") or list(DATA.keys())
        threshold = payload.get("threshold_ms", 180)
        self._json({"regions": summarise(regions, threshold)})
