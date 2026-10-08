"""Interface graphique (tkinter) du pont JS8Call -> HRD Logbook."""

import os
import queue
import sys
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, ttk

from . import core
from .i18n import set_language, t

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont, ImageTk
except ImportError:  # l'app fonctionne aussi sans icône de notification
    pystray = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
GREEN, RED, ORANGE = "#1a7f37", "#c62828", "#b26a00"


# --------------------------------------------------------------------------- utilitaires Windows

def make_icon_image(size=64):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = size // 6
    d.rounded_rectangle((0, 0, size - 1, size - 1), radius=r, fill=(21, 101, 192, 255))
    try:
        big = ImageFont.truetype("arialbd.ttf", int(size * 0.36))
        small = ImageFont.truetype("arialbd.ttf", int(size * 0.24))
    except OSError:
        big = small = ImageFont.load_default()
    d.text((size / 2, size * 0.36), "JS8", font=big, fill="white", anchor="mm")
    d.text((size / 2, size * 0.74), "HRD", font=small, fill=(255, 214, 0, 255), anchor="mm")
    return img


def single_instance():
    """Empêche de lancer l'app deux fois (JS8Call n'accepte qu'une connexion API)."""
    if sys.platform != "win32":
        return True
    import ctypes
    ctypes.windll.kernel32.CreateMutexW(None, False, "Global\\JS8toHRD_single_instance")
    return ctypes.windll.kernel32.GetLastError() != 183  # ERROR_ALREADY_EXISTS


def autostart_command():
    if getattr(sys, "frozen", False):
        return '"%s" --minimized' % sys.executable
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "JS8toHRD.pyw"))
    return '"%s" "%s" --minimized' % (pythonw, script)


def get_autostart():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, core.APP_NAME)
            return True
    except OSError:
        return False


def set_autostart(enabled):
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
        if enabled:
            winreg.SetValueEx(k, core.APP_NAME, 0, winreg.REG_SZ, autostart_command())
        else:
            try:
                winreg.DeleteValue(k, core.APP_NAME)
            except FileNotFoundError:
                pass


def refresh_autostart():
    """Si le démarrage auto est actif, le fait pointer vers l'exe actuel (après une mise à jour)."""
    try:
        if get_autostart():
            set_autostart(True)
    except OSError:
        pass


# --------------------------------------------------------------------------- application

class App:
    def __init__(self, root, start_minimized=False):
        self.root = root
        self.cfg = core.load_config()
        set_language(self.cfg["language"])
        self.history = core.History()
        self.events = queue.Queue()
        self.client = None
        self.tray = None
        self.js8_ok = False
        self.hrd_ok = None
        self.station = ""
        self.tray_hint_shown = False

        root.title("%s  v%s" % (core.APP_TITLE, core.APP_VERSION))
        root.geometry("900x520")
        root.minsize(700, 380)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        if pystray:
            self._icon_img = make_icon_image(64)
            self._tk_icon = ImageTk.PhotoImage(self._icon_img)
            root.iconphoto(True, self._tk_icon)

        self.build_ui()
        self.refresh_tree()
        self.start_tray()
        self.start_client()
        refresh_autostart()

        self.log(t("log_start", path=os.path.join(core.data_dir(), "js8call_qsos_backup.adi")))
        root.after(200, self.poll_events)
        root.after(500, self.check_hrd)
        if start_minimized or self.cfg["start_minimized"]:
            root.after(100, self.hide)

    # ----------------------------------------------------------------- UI
    def build_ui(self):
        style = ttk.Style()
        style.configure("Treeview", rowheight=22)

        top = ttk.Frame(self.root, padding=(10, 8))
        top.pack(fill="x")
        self.js8_lbl = tk.Label(top, text="● JS8Call …", font=("Segoe UI", 10, "bold"), fg=ORANGE)
        self.js8_lbl.pack(side="left")
        self.hrd_lbl = tk.Label(top, text="● HRD Logbook …", font=("Segoe UI", 10, "bold"), fg=ORANGE)
        self.hrd_lbl.pack(side="left", padx=(24, 0))
        ttk.Button(top, text=t("btn_about"), command=self.about).pack(side="right")
        ttk.Button(top, text=t("btn_settings"), command=self.open_settings).pack(side="right", padx=6)

        cols = [("utc", 120), ("call", 90), ("freq", 85), ("band", 55), ("mode", 80), ("sent", 50),
                ("rcvd", 50), ("grid", 60), ("name", 100), ("status", 150)]
        frame = ttk.Frame(self.root, padding=(10, 0))
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=[c[0] for c in cols], show="headings", selectmode="extended")
        for cid, width in cols:
            self.tree.heading(cid, text=t("col_" + cid))
            self.tree.column(cid, width=width, anchor="w", stretch=cid in ("name", "status"))
        self.tree.tag_configure("sent", foreground=GREEN)
        self.tree.tag_configure("pending", foreground=ORANGE)
        self.tree.tag_configure("error", foreground=RED)
        sb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        bar = ttk.Frame(self.root, padding=(10, 6))
        bar.pack(fill="x")
        ttk.Button(bar, text=t("btn_resend"), command=self.resend_selected).pack(side="left")
        ttk.Button(bar, text=t("btn_open_folder"),
                   command=lambda: os.startfile(core.data_dir())).pack(side="left", padx=6)
        ttk.Button(bar, text=t("btn_quit"), command=self.quit).pack(side="right")

        self.logbox = tk.Text(self.root, height=6, state="disabled", font=("Consolas", 9),
                              bg="#f6f6f6", relief="flat", padx=6, pady=4)
        self.logbox.pack(fill="x", padx=10, pady=(0, 10))

    def rebuild_ui(self):
        """Reconstruit la fenêtre (changement de langue) en gardant le journal."""
        old_log = self.logbox.get("1.0", "end-1c")
        for w in self.root.winfo_children():
            if not isinstance(w, tk.Toplevel):
                w.destroy()
        self.build_ui()
        self.logbox.configure(state="normal")
        self.logbox.insert("end", old_log + ("\n" if old_log else ""))
        self.logbox.configure(state="disabled")
        self.refresh_tree()
        self.set_indicators()

    def log(self, text):
        line = "%s  %s\n" % (datetime.now().strftime("%H:%M:%S"), text)
        self.logbox.configure(state="normal")
        self.logbox.insert("end", line)
        lines = int(self.logbox.index("end-1c").split(".")[0])
        if lines > 300:
            self.logbox.delete("1.0", "%d.0" % (lines - 300))
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        for idx, item in enumerate(self.history.items):
            f = item["fields"]
            d, tm = f.get("QSO_DATE", ""), f.get("TIME_ON", "")
            utc = "%s-%s-%s %s:%s" % (d[0:4], d[4:6], d[6:8], tm[0:2], tm[2:4]) if len(d) == 8 else ""
            mode = f.get("SUBMODE") and "%s/%s" % (f.get("MODE", ""), f["SUBMODE"]) or f.get("MODE", "")
            self.tree.insert("", 0, iid=str(idx), tags=(item["status"],), values=(
                utc, f.get("CALL", ""), f.get("FREQ", ""), f.get("BAND", ""), mode,
                f.get("RST_SENT", ""), f.get("RST_RCVD", ""), f.get("GRIDSQUARE", ""),
                f.get("NAME", ""), t("status_" + item["status"])))

    def set_indicators(self):
        if self.js8_ok:
            self.js8_lbl.config(text=t("js8_connected") + (" (%s)" % self.station if self.station else ""),
                                fg=GREEN)
        else:
            self.js8_lbl.config(text=t("js8_disconnected", port=self.cfg["js8_port"]), fg=RED)
        if self.hrd_ok:
            self.hrd_lbl.config(text=t("hrd_ready", port=self.cfg["hrd_port"]), fg=GREEN)
        else:
            self.hrd_lbl.config(text=t("hrd_absent", port=self.cfg["hrd_port"]), fg=RED)
        if self.tray:
            self.tray.title = "JS8 → HRD — JS8Call %s — HRD %s" % (
                "✔" if self.js8_ok else "✖", "✔" if self.hrd_ok else "✖")

    def about(self):
        messagebox.showinfo(core.APP_TITLE, t("about_text", version=core.APP_VERSION, url=core.APP_URL))

    # ----------------------------------------------------------------- JS8Call
    def start_client(self):
        if self.client:
            self.client.stop()
        self.client = core.JS8Client(
            self.cfg["js8_host"], self.cfg["js8_port"],
            on_message=lambda m: self.events.put(("msg", m)),
            on_status=lambda ok, err: self.events.put(("js8", ok, err)))
        self.client.start()

    def poll_events(self):
        try:
            while True:
                ev = self.events.get_nowait()
                if ev[0] == "msg":
                    self.handle_message(ev[1])
                elif ev[0] == "js8":
                    self.handle_js8_status(ev[1])
                elif ev[0] == "show":
                    self.show()
                elif ev[0] == "quit":
                    self.quit()
                    return
        except queue.Empty:
            pass
        self.root.after(200, self.poll_events)

    def handle_js8_status(self, ok):
        if ok != self.js8_ok:
            if ok:
                self.log(t("log_js8_connected", host=self.cfg["js8_host"], port=self.cfg["js8_port"]))
            else:
                self.log(t("log_js8_lost"))
        self.js8_ok = ok
        self.set_indicators()

    def handle_message(self, msg):
        mtype = msg.get("type", "")
        if mtype == "STATION.CALLSIGN":
            self.station = str(msg.get("value", "")).upper()
            self.set_indicators()
        elif mtype == "LOG.QSO":
            fields = core.qso_from_js8_message(msg, self.cfg["mode_style"])
            if fields:
                self.process_qso(fields)
            else:
                self.log(t("log_no_call"))

    # ----------------------------------------------------------------- envoi HRD
    def process_qso(self, fields):
        key = core.qso_key(fields)
        previous = self.history.find(key)
        if previous and previous["status"] == "sent":
            self.log(t("log_dup_sent", call=fields["CALL"]))
            return
        if previous and previous["status"] == "pending":
            self.log(t("log_dup_pending", call=fields["CALL"]))
            return
        try:
            core.append_backup(fields)
        except OSError as e:
            self.log(t("log_backup_error", err=e))
        status = self.try_send(fields)
        self.history.add(fields, status)
        self.refresh_tree()
        if status == "sent":
            self.notify(t("notify_sent", call=fields["CALL"]))
        elif status == "pending":
            self.log(t("log_pending", call=fields["CALL"]))
            self.notify(t("notify_pending", call=fields["CALL"]))

    def try_send(self, fields):
        if not core.hrd_listening(self.cfg["hrd_host"], self.cfg["hrd_port"]):
            return "pending"
        try:
            core.send_to_hrd(fields, self.cfg["hrd_host"], self.cfg["hrd_port"])
        except OSError as e:
            self.log(t("log_send_error", call=fields.get("CALL"), err=e))
            return "error"
        self.log("→ HRD : %s  %s %s  %s  %s/%s" % (
            fields.get("CALL"), fields.get("FREQ", "?"), fields.get("BAND", ""),
            fields.get("MODE"), fields.get("RST_SENT", "-"), fields.get("RST_RCVD", "-")))
        return "sent"

    def check_hrd(self):
        ok = core.hrd_listening(self.cfg["hrd_host"], self.cfg["hrd_port"])
        if ok != self.hrd_ok:
            if self.hrd_ok is not None or not ok:
                self.log(t("log_hrd_detected") if ok else t("log_hrd_absent", port=self.cfg["hrd_port"]))
            self.hrd_ok = ok
            self.set_indicators()
        if ok:
            pend = self.history.pending()
            if pend:
                for item in pend:
                    item["status"] = self.try_send(item["fields"])
                self.history.save()
                self.refresh_tree()
                self.log(t("log_pending_flushed", n=len(pend)))
        self.root.after(5000, self.check_hrd)

    def resend_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo(core.APP_TITLE, t("resend_none"))
            return
        if not messagebox.askyesno(core.APP_TITLE, t("resend_confirm", n=len(sel))):
            return
        for iid in sel:
            item = self.history.items[int(iid)]
            item["status"] = self.try_send(item["fields"])
        self.history.save()
        self.refresh_tree()

    # ----------------------------------------------------------------- réglages
    def open_settings(self):
        win = tk.Toplevel(self.root)
        win.title(t("settings_title"))
        win.transient(self.root)
        win.resizable(False, False)
        frm = ttk.Frame(win, padding=14)
        frm.pack()

        v = {k: tk.StringVar(value=str(self.cfg[k])) for k in ("js8_host", "js8_port", "hrd_host", "hrd_port")}
        modes = {"mfsk": t("mode_mfsk"), "js8": "JS8"}
        langs = {"auto": t("lang_auto"), "fr": "Français", "en": "English"}
        mode_var = tk.StringVar(value=modes.get(self.cfg["mode_style"], modes["mfsk"]))
        lang_var = tk.StringVar(value=langs.get(self.cfg["language"], langs["auto"]))
        autostart_var = tk.BooleanVar(value=get_autostart())
        minimized_var = tk.BooleanVar(value=self.cfg["start_minimized"])
        tray_var = tk.BooleanVar(value=self.cfg["close_to_tray"])
        bold = ("Segoe UI", 9, "bold")

        r = 0
        ttk.Label(frm, text=t("s_js8"), font=bold).grid(row=r, column=0, columnspan=4, sticky="w")
        r += 1
        ttk.Label(frm, text=t("s_address")).grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=v["js8_host"], width=18).grid(row=r, column=1, sticky="w")
        ttk.Label(frm, text=t("s_port")).grid(row=r, column=2, padx=(10, 2))
        ttk.Entry(frm, textvariable=v["js8_port"], width=7).grid(row=r, column=3)
        r += 1
        ttk.Label(frm, text=t("s_hrd"), font=bold).grid(row=r, column=0, columnspan=4, sticky="w", pady=(12, 0))
        r += 1
        ttk.Label(frm, text=t("s_address")).grid(row=r, column=0, sticky="w")
        ttk.Entry(frm, textvariable=v["hrd_host"], width=18).grid(row=r, column=1, sticky="w")
        ttk.Label(frm, text=t("s_port")).grid(row=r, column=2, padx=(10, 2))
        ttk.Entry(frm, textvariable=v["hrd_port"], width=7).grid(row=r, column=3)
        r += 1
        ttk.Label(frm, text=t("s_mode")).grid(row=r, column=0, sticky="w", pady=(12, 0))
        ttk.Combobox(frm, textvariable=mode_var, state="readonly", width=36,
                     values=list(modes.values())).grid(row=r, column=1, columnspan=3, sticky="w", pady=(12, 0))
        r += 1
        ttk.Label(frm, text=t("s_language")).grid(row=r, column=0, sticky="w", pady=(6, 0))
        ttk.Combobox(frm, textvariable=lang_var, state="readonly", width=36,
                     values=list(langs.values())).grid(row=r, column=1, columnspan=3, sticky="w", pady=(6, 0))
        r += 1
        ttk.Checkbutton(frm, text=t("s_autostart"), variable=autostart_var).grid(
            row=r, column=0, columnspan=4, sticky="w", pady=(12, 0))
        r += 1
        ttk.Checkbutton(frm, text=t("s_minimized"), variable=minimized_var).grid(
            row=r, column=0, columnspan=4, sticky="w")
        r += 1
        ttk.Checkbutton(frm, text=t("s_tray"), variable=tray_var).grid(row=r, column=0, columnspan=4, sticky="w")
        r += 1

        def save():
            try:
                js8_port, hrd_port = int(v["js8_port"].get()), int(v["hrd_port"].get())
            except ValueError:
                messagebox.showerror(t("settings_title"), t("err_ports"), parent=win)
                return
            old_js8 = (self.cfg["js8_host"], self.cfg["js8_port"])
            old_lang = self.cfg["language"]
            self.cfg.update(
                js8_host=v["js8_host"].get().strip(), js8_port=js8_port,
                hrd_host=v["hrd_host"].get().strip(), hrd_port=hrd_port,
                mode_style=next(k for k, lbl in modes.items() if lbl == mode_var.get()),
                language=next(k for k, lbl in langs.items() if lbl == lang_var.get()),
                start_minimized=minimized_var.get(), close_to_tray=tray_var.get())
            core.save_config(self.cfg)
            try:
                if autostart_var.get() != get_autostart():
                    set_autostart(autostart_var.get())
            except OSError as e:
                messagebox.showerror(t("settings_title"), t("err_autostart", err=e), parent=win)
            win.destroy()
            if self.cfg["language"] != old_lang:
                set_language(self.cfg["language"])
                self.rebuild_ui()
                self.restart_tray()
            if (self.cfg["js8_host"], self.cfg["js8_port"]) != old_js8:
                self.js8_ok = False
                self.start_client()
            self.hrd_ok = None
            self.set_indicators()
            self.log(t("log_settings_saved"))

        btns = ttk.Frame(frm)
        btns.grid(row=r, column=0, columnspan=4, sticky="e", pady=(14, 0))
        ttk.Button(btns, text=t("s_cancel"), command=win.destroy).pack(side="right")
        ttk.Button(btns, text=t("s_save"), command=save).pack(side="right", padx=6)
        win.grab_set()

    # ----------------------------------------------------------------- zone de notification
    def start_tray(self):
        if not pystray:
            return
        menu = pystray.Menu(
            pystray.MenuItem(t("tray_open"), lambda: self.events.put(("show",)), default=True),
            pystray.MenuItem(t("tray_quit"), lambda: self.events.put(("quit",))))
        self.tray = pystray.Icon(core.APP_NAME, self._icon_img, "JS8 → HRD", menu)
        self.tray.run_detached()

    def restart_tray(self):
        if self.tray:
            self.tray.stop()
            self.tray = None
            self.start_tray()

    def notify(self, text):
        if self.tray and not self.root.winfo_viewable():
            try:
                self.tray.notify(text, "JS8 → HRD")
            except Exception:
                pass

    def hide(self):
        if self.tray:
            self.root.withdraw()
        else:
            self.root.iconify()

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def on_close(self):
        if self.cfg["close_to_tray"] and self.tray:
            self.hide()
            if not self.tray_hint_shown:
                self.tray_hint_shown = True
                self.tray.notify(t("tray_hint"), "JS8 → HRD")
        else:
            self.quit()

    def quit(self):
        if self.client:
            self.client.stop()
        if self.tray:
            self.tray.stop()
        self.root.destroy()


def main():
    if not single_instance():
        set_language(core.load_config()["language"])
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(core.APP_TITLE, t("already_running"))
        return
    root = tk.Tk()
    App(root, start_minimized="--minimized" in sys.argv)
    root.mainloop()
