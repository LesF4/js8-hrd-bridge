"""Simulateur pour tester l'app sans toucher au vrai log.

Lance un faux JS8Call (API TCP) qui envoie des LOG.QSO, et un faux HRD (UDP)
qui affiche ce qu'il reçoit. Régler l'app sur ces ports (par défaut 2250 / 2350).
"""
import json
import socket
import sys
import threading
import time

JS8_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 2250
HRD_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 2350
HRD_DELAY = float(sys.argv[3]) if len(sys.argv) > 3 else 0  # simule HRD ouvert plus tard
CALLS = ["EA4XY", "DL1ABC", "G4XYZ", "ON4AA"]


def fake_hrd():
    time.sleep(HRD_DELAY)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", HRD_PORT))
    while True:
        data, _ = s.recvfrom(65536)
        print("[faux HRD] reçu :", data.decode("cp1252"), flush=True)


def fake_js8():
    srv = socket.socket()
    srv.bind(("127.0.0.1", JS8_PORT))
    srv.listen(1)
    conn, _ = srv.accept()
    print("[faux JS8Call] app connectée", flush=True)
    conn.sendall(b'{"type":"STATION.CALLSIGN","value":"F4MAJ","params":{}}\n')
    for i, call in enumerate(CALLS):
        time.sleep(2)
        now = int(time.time() * 1000)
        msg = {"type": "LOG.QSO", "value": "", "params": {
            "CALL": call, "GRID": "JN18", "FREQ": 7078000 + i * 500, "MODE": "MFSK", "SUBMODE": "JS8",
            "RPT.SENT": "-10", "RPT.RECV": "-05", "NAME": "Test", "COMMENTS": "simulation",
            "STATION.CALL": "F4MAJ", "STATION.GRID": "JN37QS", "UTC.ON": now - 600000, "UTC.OFF": now}}
        conn.sendall((json.dumps(msg) + "\n").encode())
        print("[faux JS8Call] LOG.QSO", call, flush=True)
    time.sleep(1)
    conn.sendall((json.dumps(msg) + "\n").encode())  # doublon volontaire
    print("[faux JS8Call] doublon", call, flush=True)
    time.sleep(3 + HRD_DELAY)


threading.Thread(target=fake_hrd, daemon=True).start()
fake_js8()
