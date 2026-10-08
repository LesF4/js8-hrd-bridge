# Journal des versions / Changelog

## 1.0.0 — 2026-10-08

Première version publique / First public release.

- Envoi automatique des QSO loggés dans JS8Call (API TCP, `LOG.QSO`) vers HRD Logbook (ADIF en UDP).
- Mode `MFSK` + sous-mode `JS8` (norme ADIF) ou `JS8`, bande calculée depuis la fréquence.
- File d'attente si HRD est fermé, doublons ignorés, sauvegarde ADIF de tous les QSO.
- Fenêtre avec voyants JS8Call / HRD, liste des QSO, renvoi manuel, icône dans la zone de notification.
- Démarrage automatique avec Windows (optionnel), interface français / anglais.
- Installeur Windows (sans droits administrateur) et version portable.
