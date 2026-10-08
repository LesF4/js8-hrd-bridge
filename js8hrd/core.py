"""Logique du pont JS8Call -> HRD Logbook (sans interface graphique).

JS8Call publie chaque QSO loggé sur son API TCP (JSON, un message par ligne,
type "LOG.QSO" : "value" contient l'enregistrement ADIF, "params" les champs).
HRD Logbook reçoit des enregistrements ADIF bruts en UDP (port 2333 par défaut,
« QSO Forwarding » > réception UDP), le même format que la diffusion N1MM de WSJT-X.
"""

import json
import os
import re
import socket
import threading
import time
from datetime import datetime, timezone

from .i18n import t

APP_NAME = "JS8toHRD"
APP_TITLE = "JS8Call → HRD Logbook"
APP_VERSION = "1.0.0"
APP_URL = "https://github.com/LesF4/js8-hrd-bridge"

DEFAULT_CONFIG = {
    "js8_host": "127.0.0.1",
    "js8_port": 2242,
    "hrd_host": "127.0.0.1",
    "hrd_port": 2333,
    # "mfsk" : MODE=MFSK + SUBMODE=JS8 (norme ADIF 3) ; "js8" : MODE=JS8
    "mode_style": "mfsk",
    "start_minimized": False,
    "close_to_tray": True,
    "language": "auto",  # "auto", "fr" ou "en"
}

BANDS = [
    ("2190M", 0.1357, 0.1378), ("630M", 0.472, 0.479), ("160M", 1.8, 2.0),
    ("80M", 3.5, 4.0), ("60M", 5.06, 5.45), ("40M", 7.0, 7.3),
    ("30M", 10.1, 10.15), ("20M", 14.0, 14.35), ("17M", 18.068, 18.168),
    ("15M", 21.0, 21.45), ("12M", 24.89, 24.99), ("10M", 28.0, 29.7),
    ("6M", 50.0, 54.0), ("4M", 70.0, 71.0), ("2M", 144.0, 148.0),
    ("1.25M", 222.0, 225.0), ("70CM", 420.0, 450.0),
]

_TAG_RE = re.compile(r"<([A-Za-z0-9_]+)(?::(\d+))?(?::[A-Za-z])?>")


# --------------------------------------------------------------------------- dossiers / config

def data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    path = os.path.join(base, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(os.path.join(data_dir(), "config.json"), encoding="utf-8") as f:
            cfg.update({k: v for k, v in json.load(f).items() if k in DEFAULT_CONFIG})
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    with open(os.path.join(data_dir(), "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# --------------------------------------------------------------------------- ADIF

def parse_adif_record(text):
    """Retourne les champs du premier enregistrement ADIF de `text` (clés en majuscules)."""
    low = text.lower()
    eoh = low.find("<eoh>")
    if eoh >= 0:
        text = text[eoh + 5:]
    fields = {}
    pos = 0
    while True:
        m = _TAG_RE.search(text, pos)
        if not m:
            break
        name = m.group(1).upper()
        if name == "EOR":
            break
        length = int(m.group(2) or 0)
        value = text[m.end():m.end() + length]
        pos = m.end() + length
        if m.group(2) is not None:
            fields[name] = value
    return fields


def build_adif_record(fields):
    parts = ["<%s:%d>%s" % (k, len(v), v) for k, v in fields.items() if v != ""]
    return " ".join(parts) + " <EOR>"


def band_for_mhz(mhz):
    for name, lo, hi in BANDS:
        if lo <= mhz <= hi:
            return name
    return ""


def _fmt_utc(ms):
    dt = datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc)
    return dt.strftime("%Y%m%d"), dt.strftime("%H%M%S")


def fields_from_js8_params(params):
    """Construit les champs ADIF à partir des « params » d'un message LOG.QSO."""
    f = {}

    def put(key, val):
        if val not in (None, ""):
            f[key] = str(val).strip()

    put("CALL", params.get("CALL"))
    put("GRIDSQUARE", params.get("GRID"))
    put("MODE", params.get("MODE"))
    put("SUBMODE", params.get("SUBMODE"))
    put("RST_SENT", params.get("RPT.SENT"))
    put("RST_RCVD", params.get("RPT.RECV"))
    put("NAME", params.get("NAME"))
    put("COMMENT", params.get("COMMENTS"))
    put("OPERATOR", params.get("STATION.OP"))
    put("STATION_CALLSIGN", params.get("STATION.CALL"))
    put("MY_GRIDSQUARE", params.get("STATION.GRID"))
    freq = params.get("FREQ")
    if freq not in (None, ""):
        try:
            hz = float(freq)
            put("FREQ", "%.6f" % (hz / 1e6 if hz > 1e5 else hz))
        except ValueError:
            pass
    if params.get("UTC.ON"):
        f["QSO_DATE"], f["TIME_ON"] = _fmt_utc(params["UTC.ON"])
    if params.get("UTC.OFF"):
        f["QSO_DATE_OFF"], f["TIME_OFF"] = _fmt_utc(params["UTC.OFF"])
    return f


def normalize(fields, mode_style="mfsk"):
    """Nettoie un QSO avant envoi à HRD (mode JS8, bande, majuscules)."""
    f = {k.upper(): str(v).strip() for k, v in fields.items() if str(v).strip() != ""}
    for key in ("CALL", "STATION_CALLSIGN", "OPERATOR"):
        if key in f:
            f[key] = f[key].upper()

    mode, sub = f.get("MODE", "").upper(), f.get("SUBMODE", "").upper()
    is_js8 = mode == "JS8" or sub == "JS8" or not mode
    if is_js8:
        if mode_style == "js8":
            f["MODE"] = "JS8"
            f.pop("SUBMODE", None)
        else:
            f["MODE"], f["SUBMODE"] = "MFSK", "JS8"

    if "BAND" not in f and "FREQ" in f:
        try:
            band = band_for_mhz(float(f["FREQ"]))
            if band:
                f["BAND"] = band
        except ValueError:
            pass
    if "QSO_DATE" not in f or "TIME_ON" not in f:
        now = datetime.now(timezone.utc)
        f.setdefault("QSO_DATE", now.strftime("%Y%m%d"))
        f.setdefault("TIME_ON", now.strftime("%H%M%S"))
    return f


def qso_from_js8_message(msg, mode_style="mfsk"):
    """Message LOG.QSO JSON -> champs ADIF normalisés (ou None si pas d'indicatif)."""
    params = msg.get("params") or {}
    value = msg.get("value") or ""
    fields = parse_adif_record(value) if "<" in value else {}
    for k, v in fields_from_js8_params(params).items():
        fields.setdefault(k, v)
    if not fields.get("CALL"):
        return None
    return normalize(fields, mode_style)


def qso_key(f):
    return "%s|%s|%s|%s" % (f.get("CALL", ""), f.get("QSO_DATE", ""),
                            f.get("TIME_ON", "")[:4], f.get("BAND", ""))


# --------------------------------------------------------------------------- HRD (UDP)

def send_to_hrd(fields, host, port):
    payload = build_adif_record(fields).encode("cp1252", errors="replace")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.sendto(payload, (host, int(port)))


def is_local(host):
    return host.strip().lower() in ("127.0.0.1", "localhost", "::1", "0.0.0.0", "")


def hrd_listening(host, port):
    """Vrai si un programme écoute déjà le port UDP (HRD lancé). Toujours vrai pour un hôte distant."""
    if not is_local(host):
        return True
    # On tente d'occuper le port : si c'est refusé, quelqu'un (HRD) l'écoute déjà.
    for addr in ("0.0.0.0", "127.0.0.1"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.bind((addr, int(port)))
        except OSError:
            return True
        finally:
            s.close()
    return False


def append_backup(fields):
    path = os.path.join(data_dir(), "js8call_qsos_backup.adi")
    new = not os.path.exists(path)
    with open(path, "a", encoding="utf-8") as f:
        if new:
            f.write(t("backup_header") + "\n"
                    "<ADIF_VER:5>3.1.4 <PROGRAMID:%d>%s <EOH>\n" % (len(APP_NAME), APP_NAME))
        f.write(build_adif_record(fields) + "\n")
    return path


# --------------------------------------------------------------------------- historique

class History:
    """Derniers QSO traités, persistés sur disque (pour la liste et les doublons)."""

    MAX = 500

    def __init__(self):
        self.path = os.path.join(data_dir(), "history.json")
        self.lock = threading.Lock()
        try:
            with open(self.path, encoding="utf-8") as f:
                self.items = json.load(f)
        except (OSError, ValueError):
            self.items = []

    def save(self):
        with self.lock:
            data = self.items[-self.MAX:]
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, self.path)

    def find(self, key):
        with self.lock:
            for item in reversed(self.items):
                if item["key"] == key:
                    return item
        return None

    def add(self, fields, status):
        item = {"key": qso_key(fields), "fields": fields, "status": status,
                "received": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        with self.lock:
            self.items.append(item)
            self.items = self.items[-self.MAX:]
        self.save()
        return item

    def pending(self):
        with self.lock:
            return [i for i in self.items if i["status"] == "pending"]


# --------------------------------------------------------------------------- client JS8Call

class JS8Client(threading.Thread):
    """Se connecte à l'API TCP de JS8Call et reconnecte automatiquement."""

    def __init__(self, host, port, on_message, on_status):
        super().__init__(daemon=True)
        self.host, self.port = host, int(port)
        self.on_message, self.on_status = on_message, on_status
        self._stop_evt = threading.Event()
        self._sock = None

    def stop(self):
        self._stop_evt.set()
        if self._sock:
            try:
                self._sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def run(self):
        while not self._stop_evt.is_set():
            try:
                self._sock = socket.create_connection((self.host, self.port), timeout=3)
                self._sock.settimeout(None)
                self.on_status(True, "")
                self._sock.sendall(b'{"type":"STATION.GET_CALLSIGN","value":"","params":{}}\n')
                buf = b""
                while not self._stop_evt.is_set():
                    data = self._sock.recv(65536)
                    if not data:
                        break
                    buf += data
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            self.on_message(json.loads(line.decode("utf-8", "replace")))
                        except ValueError:
                            pass
            except OSError as e:
                if not self._stop_evt.is_set():
                    self.on_status(False, str(e))
            finally:
                if self._sock:
                    try:
                        self._sock.close()
                    except OSError:
                        pass
                    self._sock = None
            if not self._stop_evt.is_set():
                self.on_status(False, "")
                self._stop_evt.wait(5)
