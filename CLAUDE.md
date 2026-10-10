# JS8toHRD — contexte du projet

Application Windows (Python 3 + tkinter, empaquetée avec PyInstaller + Inno Setup) qui envoie
automatiquement les QSO loggés dans **JS8Call** vers **HRD Logbook** (Ham Radio Deluxe). Interface et
docs en français (+ anglais). Auteur : F4MAJ / Jean-Bernard, licence MIT, dépôt public
`LesF4/js8-hrd-bridge`.

## Architecture

- `js8hrd/core.py` : logique sans interface.
  - `JS8Client` (thread) se connecte à l'**API TCP de JS8Call** (127.0.0.1:2242, JSON une ligne par
    message, reconnexion toutes les 5 s). Message `LOG.QSO` : ADIF dans `value`, champs dans `params`.
  - `qso_from_js8_message()` + `normalize()` : mode `MFSK` + sous-mode `JS8` (norme ADIF) ou `JS8`,
    bande calculée depuis la fréquence.
  - `send_to_hrd()` : ADIF en **UDP vers la réception de HRD** (QSO Forwarding, port 2333, comme la
    diffusion N1MM de WSJT-X), encodé en cp1252.
  - `hrd_listening()` : HRD est « détecté » si le port UDP est déjà occupé (test de `bind`).
  - File d'attente si HRD est fermé, anti-doublons, sauvegarde ADIF `%APPDATA%\JS8toHRD\`.
- `js8hrd/app.py` : fenêtre, voyants JS8Call / HRD, réglages, icône (pystray), démarrage auto,
  instance unique (JS8Call n'accepte qu'**une** connexion API).
- `js8hrd/i18n.py` : textes FR/EN.

## Points d'attention

- Dans JS8Call, laisser **décoché** « Broadcast to N1MM », sinon chaque QSO arrive deux fois dans HRD.
- Ne jamais envoyer de faux QSO dans le vrai log : tester avec `tests/simulate.py` (faux JS8Call +
  faux HRD sur d'autres ports).
- Projet complémentaire : `LesF4/hrd-wavelog-bridge` (HRD ⇄ Wavelog) ; il utilise aussi la réception
  UDP 2333 de HRD, sans conflit.

## Tests, construction, publication

```bash
python -m unittest tests.test_core
pip install pyinstaller pystray pillow
python packaging/build.py --portable --installer
```

Publier : mettre à jour `APP_VERSION` (`js8hrd/core.py`) et `CHANGELOG.md`, commit, tag `vX.Y.Z`, push
du tag → GitHub Actions construit l'installeur et la version portable et les attache à la Release.
Avant tout push : aucune donnée personnelle dans les fichiers ni dans l'historique git.
