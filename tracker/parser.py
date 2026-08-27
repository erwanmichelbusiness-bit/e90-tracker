# -*- coding: utf-8 -*-
"""Parsing du flux RSS 2.0 de Google News.

Le lien du flux pointe vers news.google.com et non vers l'annonce : le GUID
encode un jeton opaque non decodable cote serveur. Verifie pendant l'audit :
ce lien se resout correctement vers l'annonce dans un navigateur reel, donc
il reste utilisable tel quel dans la notification Telegram.
"""
import html
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime


def _texte(element):
    return html.unescape(element.text or "").strip() if element is not None else ""


def parser(xml_brut):
    """Renvoie une liste d'annonces brutes. Tolere un XML malforme."""
    try:
        racine = ET.fromstring(xml_brut)
    except ET.ParseError:
        return []

    annonces = []
    for item in racine.iter("item"):
        guid = _texte(item.find("guid"))
        titre = _texte(item.find("title"))
        lien = _texte(item.find("link"))

        source_el = item.find("source")
        source = _texte(source_el)
        domaine = ""
        if source_el is not None:
            domaine = (source_el.get("url") or "").replace("https://", "")
            domaine = domaine.replace("http://", "").replace("www.", "").strip("/")

        date = None
        brut_date = _texte(item.find("pubDate"))
        if brut_date:
            try:
                date = parsedate_to_datetime(brut_date)
            except (TypeError, ValueError):
                date = None

        # Google suffixe le titre par " - <Source>" : on le retire.
        if source and titre.endswith(" - " + source):
            titre = titre[: -(len(source) + 3)].strip()

        if not guid or not titre:
            continue

        annonces.append({
            "guid": guid,
            "titre": titre,
            "lien": lien,
            "source": source,
            "domaine": domaine,
            "date": date,
        })
    return annonces


# --- Extraction opportuniste depuis le titre (seule donnee disponible) ---

def annee(titre):
    for m in re.finditer(r"\b(19[89]\d|20[0-2]\d)\b", titre):
        val = int(m.group(1))
        if 1985 <= val <= 2026:
            return val
    return None


_SEP = "[ \u00a0\u202f.]"  # espace, insecable, fine insecable, point


def kilometrage(titre):
    m = re.search(r"\b(\d{1,3}(?:" + _SEP + r"?\d{3})+)\s*(?:km|kms)\b", titre, re.I)
    if m:
        val = int(re.sub(r"[^\d]", "", m.group(1)))
        return val if 100 <= val <= 999999 else None
    return None


def prix(titre):
    # Pas de \b apres le symbole euro : ce n'est pas un caractere de mot,
    # la limite de mot ne peut donc pas s'appliquer en fin de chaine.
    m = re.search(r"(\d{1,3}(?:" + _SEP + r"?\d{3})+)\s*(?:\u20ac|euros?\b|eur\b)",
                  titre, re.I)
    if m:
        val = int(re.sub(r"[^\d]", "", m.group(1)))
        return val if 500 <= val <= 200000 else None
    return None


def carburant(titre):
    t = titre.lower()
    if re.search(r"\bessence\b|\bpetrol\b", t):
        return "essence"
    if re.search(r"\bdiesel\b|\bgazole\b|\btdi\b|\bhdi\b", t):
        return "diesel"
    return ""
