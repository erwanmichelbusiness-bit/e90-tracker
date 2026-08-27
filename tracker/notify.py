# -*- coding: utf-8 -*-
"""Notification Telegram.

Le lien transmis pointe vers news.google.com : le GUID du flux encode un
jeton opaque et l'URL reelle n'est pas extractible cote serveur. Verifie
pendant l'audit : ce lien se resout bien vers l'annonce dans un navigateur.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/{methode}"


def _config():
    return os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")


def disponible():
    token, chat = _config()
    return bool(token and chat)


def _appeler(methode, params):
    token, _ = _config()
    url = API.format(token=token, methode=methode)
    donnees = urllib.parse.urlencode(params).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=donnees), timeout=20) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            return json.load(e)
        except ValueError:
            return {"ok": False, "description": "HTTP {}".format(e.code)}
    except (urllib.error.URLError, OSError) as e:
        return {"ok": False, "description": str(e)}


def _echapper(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def formater(annonce, score, verdict_):
    entete = "🚨 <b>NOUVELLE ANNONCE</b>" if verdict_ == "NOTIFIER" \
        else "👀 <b>À VÉRIFIER</b> (correspondance partielle)"
    inconnu = "non précisé"
    lignes = [
        entete,
        "",
        "<b>{}</b>".format(_echapper(annonce["titre"])),
        "",
        "Année : {}".format(annonce.get("annee") or inconnu),
        "Prix : {}".format(
            "{} €".format(annonce["prix"]) if annonce.get("prix") else inconnu),
        "Kilométrage : {}".format(
            "{} km".format(annonce["kilometrage"]) if annonce.get("kilometrage") else inconnu),
        "Carburant : {}".format(annonce.get("carburant") or inconnu),
        "Score : {}/150".format(score),
        "Source : {}".format(_echapper(annonce.get("source") or annonce.get("domaine") or "?")),
        "",
        annonce.get("lien") or "",
    ]
    return "\n".join(lignes)


def envoyer(texte):
    _, chat = _config()
    return _appeler("sendMessage", {
        "chat_id": chat,
        "text": texte,
        "parse_mode": "HTML",
        "disable_web_page_preview": "false",
    })
