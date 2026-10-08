"""Capture la fenêtre de l'app pour la doc : python packaging/screenshot.py fr|en sortie.png

À lancer avec un APPDATA de test et tests/simulate.py en parallèle (voir packaging/README.md).
"""
import os
import sys
import tkinter as tk

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import ImageGrab  # noqa: E402

from js8hrd import app  # noqa: E402

lang, out = sys.argv[1], sys.argv[2]
root = tk.Tk()
a = app.App(root)
a.cfg["language"] = lang
app.set_language(lang)
a.rebuild_ui()
root.attributes("-topmost", True)


def shot():
    root.update()
    x, y = root.winfo_rootx(), root.winfo_rooty()
    w, h = root.winfo_width(), root.winfo_height()
    ImageGrab.grab((x, y, x + w, y + h), all_screens=True).save(out)
    a.quit()


root.after(10500, shot)
root.mainloop()
