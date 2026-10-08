import json
import os
import socket
import sys
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from js8hrd import core  # noqa: E402

# Message tel qu'émis par JS8Call (LOG.QSO) : ADIF dans "value", champs dans "params".
SAMPLE = {
    "type": "LOG.QSO",
    "value": "<call:5>EA4XY <gridsquare:4>IN80 <mode:4>MFSK <submode:3>JS8 <rst_sent:3>-12 "
             "<rst_rcvd:3>-08 <qso_date:8>20261008 <time_on:6>143015 <qso_date_off:8>20261008 "
             "<time_off:6>144500 <band:3>40m <freq:8>7.079500 <station_callsign:5>F4MAJ "
             "<my_gridsquare:6>JN37QS <name:5>Pédro <comment:10>Super QSO! <eor>",
    "params": {"CALL": "EA4XY", "GRID": "IN80", "FREQ": 7079500, "MODE": "MFSK", "SUBMODE": "JS8",
               "RPT.SENT": "-12", "RPT.RECV": "-08", "NAME": "Pédro", "COMMENTS": "Super QSO!",
               "STATION.CALL": "F4MAJ", "STATION.GRID": "JN37QS",
               "UTC.ON": 1791469815000, "UTC.OFF": 1791470700000, "_ID": 1},
}


class CoreTests(unittest.TestCase):
    def test_parse_and_build_roundtrip(self):
        f = core.parse_adif_record(SAMPLE["value"])
        self.assertEqual(f["CALL"], "EA4XY")
        self.assertEqual(f["NAME"], "Pédro")
        self.assertEqual(f["COMMENT"], "Super QSO!")
        self.assertEqual(core.parse_adif_record(core.build_adif_record(f)), f)

    def test_parse_skips_header(self):
        f = core.parse_adif_record("JS8Call <adif_ver:5>3.1.0 <eoh>\n<call:4>K1AB <eor>")
        self.assertEqual(f, {"CALL": "K1AB"})

    def test_message_from_value(self):
        f = core.qso_from_js8_message(SAMPLE)
        self.assertEqual((f["MODE"], f["SUBMODE"], f["BAND"]), ("MFSK", "JS8", "40m"))
        self.assertEqual((f["RST_SENT"], f["RST_RCVD"]), ("-12", "-08"))
        self.assertEqual(f["TIME_ON"], "143015")

    def test_message_params_only(self):
        msg = {"type": "LOG.QSO", "value": "", "params": dict(SAMPLE["params"], CALL="ea4xy")}
        f = core.qso_from_js8_message(msg)
        self.assertEqual(f["CALL"], "EA4XY")
        self.assertEqual(f["FREQ"], "7.079500")
        self.assertEqual(f["BAND"], "40M")
        self.assertEqual(f["GRIDSQUARE"], "IN80")
        self.assertEqual(len(f["QSO_DATE"]), 8)

    def test_mode_js8_style(self):
        f = core.qso_from_js8_message(SAMPLE, "js8")
        self.assertEqual(f["MODE"], "JS8")
        self.assertNotIn("SUBMODE", f)
        f = core.normalize({"CALL": "K1AB", "MODE": "JS8"}, "mfsk")
        self.assertEqual((f["MODE"], f["SUBMODE"]), ("MFSK", "JS8"))

    def test_no_call_is_ignored(self):
        self.assertIsNone(core.qso_from_js8_message({"type": "LOG.QSO", "value": "", "params": {}}))

    def test_send_udp(self):
        rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        rx.bind(("127.0.0.1", 0))
        rx.settimeout(2)
        port = rx.getsockname()[1]
        self.assertTrue(core.hrd_listening("127.0.0.1", port))
        f = core.qso_from_js8_message(SAMPLE)
        core.send_to_hrd(f, "127.0.0.1", port)
        data = rx.recv(4096).decode("cp1252")
        rx.close()
        self.assertTrue(data.endswith("<EOR>"))
        self.assertEqual(core.parse_adif_record(data)["NAME"], "Pédro")
        self.assertFalse(core.hrd_listening("127.0.0.1", port))

    def test_js8_client_receives_log_qso(self):
        srv = socket.socket()
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        got = threading.Event()
        received = []

        def serve():
            conn, _ = srv.accept()
            conn.recv(1024)  # STATION.GET_CALLSIGN
            conn.sendall((json.dumps(SAMPLE) + "\n").encode())
            got.wait(3)
            conn.close()

        threading.Thread(target=serve, daemon=True).start()
        client = core.JS8Client("127.0.0.1", srv.getsockname()[1],
                                lambda m: (received.append(m), got.set()), lambda ok, e: None)
        client.start()
        self.assertTrue(got.wait(3))
        client.stop()
        srv.close()
        self.assertEqual(received[0]["type"], "LOG.QSO")


class I18nTests(unittest.TestCase):
    def test_same_keys_in_all_languages(self):
        from js8hrd import i18n
        self.assertEqual(set(i18n.TEXTS["fr"]), set(i18n.TEXTS["en"]))

    def test_format(self):
        from js8hrd import i18n
        i18n.set_language("en")
        self.assertEqual(i18n.t("log_dup_sent", call="K1AB"), "QSO K1AB already sent to HRD, duplicate ignored.")
        i18n.set_language("fr")
        self.assertIn("doublon", i18n.t("log_dup_sent", call="K1AB"))


if __name__ == "__main__":
    unittest.main()
