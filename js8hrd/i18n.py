"""Textes de l'interface en français et en anglais."""

import sys

LANGUAGES = ("fr", "en")

TEXTS = {
    "fr": {
        "status_sent": "✔ Envoyé à HRD",
        "status_pending": "⏳ En attente de HRD",
        "status_error": "✖ Erreur d'envoi",
        "js8_connected": "● JS8Call : connecté",
        "js8_disconnected": "● JS8Call : non connecté (port {port})",
        "hrd_ready": "● HRD Logbook : prêt (UDP {port})",
        "hrd_absent": "● HRD Logbook : pas détecté (UDP {port})",
        "btn_settings": "Réglages…",
        "btn_about": "À propos",
        "btn_resend": "Renvoyer la sélection à HRD",
        "btn_open_folder": "Ouvrir le dossier de sauvegarde",
        "btn_quit": "Quitter",
        "col_utc": "Date / UTC", "col_call": "Indicatif", "col_freq": "Fréquence",
        "col_band": "Bande", "col_mode": "Mode", "col_sent": "Env.", "col_rcvd": "Reçu",
        "col_grid": "Grille", "col_name": "Nom", "col_status": "Statut",
        "log_start": "Démarrage. Sauvegarde ADIF : {path}",
        "log_js8_connected": "Connecté à JS8Call ({host}:{port}).",
        "log_js8_lost": "JS8Call non joignable — nouvel essai toutes les 5 s. "
                        "(JS8Call lancé ? API TCP activée ?)",
        "log_no_call": "Message LOG.QSO reçu sans indicatif, ignoré.",
        "log_dup_sent": "QSO {call} déjà envoyé à HRD, doublon ignoré.",
        "log_dup_pending": "QSO {call} déjà en attente, doublon ignoré.",
        "log_backup_error": "Impossible d'écrire la sauvegarde ADIF : {err}",
        "log_pending": "HRD Logbook n'est pas ouvert : QSO {call} mis en attente, "
                       "il sera envoyé dès son ouverture.",
        "log_send_error": "Erreur d'envoi de {call} : {err}",
        "log_hrd_detected": "HRD Logbook détecté.",
        "log_hrd_absent": "HRD Logbook n'écoute pas sur le port UDP {port}.",
        "log_pending_flushed": "{n} QSO en attente envoyé(s) à HRD.",
        "log_settings_saved": "Réglages enregistrés.",
        "notify_sent": "QSO avec {call} envoyé à HRD Logbook",
        "notify_pending": "HRD fermé : QSO {call} en attente",
        "resend_none": "Sélectionne d'abord un ou plusieurs QSO dans la liste.",
        "resend_confirm": "Renvoyer {n} QSO à HRD Logbook ?\n\n"
                          "Attention : s'ils sont déjà dans le log, HRD peut créer un doublon.",
        "settings_title": "Réglages",
        "s_js8": "JS8Call — API TCP",
        "s_hrd": "HRD Logbook — réception UDP (QSO Forwarding)",
        "s_address": "Adresse",
        "s_port": "Port",
        "s_mode": "Mode enregistré",
        "mode_mfsk": "MFSK + sous-mode JS8 (norme ADIF)",
        "s_language": "Langue",
        "lang_auto": "Automatique (langue de Windows)",
        "s_autostart": "Lancer automatiquement au démarrage de Windows",
        "s_minimized": "Démarrer réduit",
        "s_tray": "La croix ✕ réduit dans la zone de notification (au lieu de quitter)",
        "s_save": "Enregistrer",
        "s_cancel": "Annuler",
        "err_ports": "Les ports doivent être des nombres.",
        "err_autostart": "Démarrage automatique impossible : {err}",
        "tray_open": "Ouvrir",
        "tray_quit": "Quitter",
        "tray_hint": "L'app continue de tourner ici. Clic droit > Quitter pour l'arrêter.",
        "already_running": "L'application est déjà lancée "
                           "(regarde près de l'horloge, dans la zone de notification).",
        "about_text": "Envoie automatiquement les QSO loggés dans JS8Call vers HRD Logbook.\n\n"
                      "Version {version}\n© 2026 F4MAJ / Jean-Bernard — licence MIT\n\n{url}",
        "backup_header": "Sauvegarde des QSO JS8Call envoyés à HRD",
    },
    "en": {
        "status_sent": "✔ Sent to HRD",
        "status_pending": "⏳ Waiting for HRD",
        "status_error": "✖ Send error",
        "js8_connected": "● JS8Call: connected",
        "js8_disconnected": "● JS8Call: not connected (port {port})",
        "hrd_ready": "● HRD Logbook: ready (UDP {port})",
        "hrd_absent": "● HRD Logbook: not detected (UDP {port})",
        "btn_settings": "Settings…",
        "btn_about": "About",
        "btn_resend": "Resend selection to HRD",
        "btn_open_folder": "Open backup folder",
        "btn_quit": "Quit",
        "col_utc": "Date / UTC", "col_call": "Call", "col_freq": "Frequency",
        "col_band": "Band", "col_mode": "Mode", "col_sent": "Sent", "col_rcvd": "Rcvd",
        "col_grid": "Grid", "col_name": "Name", "col_status": "Status",
        "log_start": "Started. ADIF backup: {path}",
        "log_js8_connected": "Connected to JS8Call ({host}:{port}).",
        "log_js8_lost": "Cannot reach JS8Call — retrying every 5 s. "
                        "(Is JS8Call running? Is the TCP API enabled?)",
        "log_no_call": "LOG.QSO message without a callsign, ignored.",
        "log_dup_sent": "QSO {call} already sent to HRD, duplicate ignored.",
        "log_dup_pending": "QSO {call} already waiting, duplicate ignored.",
        "log_backup_error": "Cannot write the ADIF backup: {err}",
        "log_pending": "HRD Logbook is not open: QSO {call} queued, "
                       "it will be sent as soon as HRD starts.",
        "log_send_error": "Error sending {call}: {err}",
        "log_hrd_detected": "HRD Logbook detected.",
        "log_hrd_absent": "HRD Logbook is not listening on UDP port {port}.",
        "log_pending_flushed": "{n} queued QSO(s) sent to HRD.",
        "log_settings_saved": "Settings saved.",
        "notify_sent": "QSO with {call} sent to HRD Logbook",
        "notify_pending": "HRD closed: QSO {call} queued",
        "resend_none": "First select one or more QSOs in the list.",
        "resend_confirm": "Resend {n} QSO(s) to HRD Logbook?\n\n"
                          "Warning: if they are already in the log, HRD may create a duplicate.",
        "settings_title": "Settings",
        "s_js8": "JS8Call — TCP API",
        "s_hrd": "HRD Logbook — UDP receive (QSO Forwarding)",
        "s_address": "Address",
        "s_port": "Port",
        "s_mode": "Logged mode",
        "mode_mfsk": "MFSK + JS8 submode (ADIF standard)",
        "s_language": "Language",
        "lang_auto": "Automatic (Windows language)",
        "s_autostart": "Start automatically with Windows",
        "s_minimized": "Start minimized",
        "s_tray": "The ✕ button minimizes to the notification area (instead of quitting)",
        "s_save": "Save",
        "s_cancel": "Cancel",
        "err_ports": "Ports must be numbers.",
        "err_autostart": "Cannot set up automatic start: {err}",
        "tray_open": "Open",
        "tray_quit": "Quit",
        "tray_hint": "The app keeps running here. Right-click > Quit to stop it.",
        "already_running": "The application is already running "
                           "(look near the clock, in the notification area).",
        "about_text": "Automatically sends QSOs logged in JS8Call to HRD Logbook.\n\n"
                      "Version {version}\n© 2026 F4MAJ / Jean-Bernard — MIT licence\n\n{url}",
        "backup_header": "Backup of JS8Call QSOs sent to HRD",
    },
}

_lang = "en"


def system_language():
    """'fr' si Windows est en français, sinon 'en'."""
    if sys.platform == "win32":
        try:
            import ctypes
            return "fr" if ctypes.windll.kernel32.GetUserDefaultUILanguage() & 0x3FF == 0x0C else "en"
        except (AttributeError, OSError):
            pass
    import locale
    return "fr" if (locale.getlocale()[0] or "").lower().startswith("fr") else "en"


def set_language(choice):
    global _lang
    _lang = choice if choice in LANGUAGES else system_language()


def t(key, **kwargs):
    text = TEXTS[_lang].get(key) or TEXTS["en"][key]
    return text.format(**kwargs) if kwargs else text
