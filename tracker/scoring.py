# -*- coding: utf-8 -*-
"""Scoring BMW 325i E90/E91 3.0 essence (N53B30UL).

Point cle etabli pendant l'audit : « 325i » recouvre DEUX moteurs.
  - avant ~09/2007 : N52B25, 2.5 L, 218 ch  -> HORS CIBLE
  - a partir du LCI : N53B30UL, 3.0 L, 218 ch -> CIBLE
Quasi aucune annonce ne precise le code moteur : l'annee est le seul
discriminant fiable. Une annonce sans annee reste donc indecidable et part
en « a revoir » plutot que d'etre jetee.
"""
import re
import unicodedata

SEUIL_NOTIFIER = 70
SEUIL_A_REVOIR = 40


def normaliser(texte):
    t = unicodedata.normalize("NFKD", texte or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def scorer(annonce):
    """annonce : dict avec titre, annee, carburant, kilometrage (optionnels).
    Renvoie (score, [raisons])."""
    t = normaliser(annonce.get("titre", ""))
    score, raisons = 0, []

    def add(points, motif):
        nonlocal score
        score += points
        raisons.append("{:+d} {}".format(points, motif))

    # --- Badge modele
    if re.search(r"\b325\s*i\b", t):
        add(45, "badge 325i")
    elif re.search(r"\b325\b", t):
        add(25, "badge 325 (i non explicite)")

    # --- Chassis
    if re.search(r"\be90\b", t):
        add(20, "chassis E90 (berline)")
    if re.search(r"\be91\b", t):
        add(20, "chassis E91 (touring)")

    # --- Signaux moteur 3.0
    if re.search(r"\bn53\b", t):
        add(30, "code moteur N53 = 3.0 LCI")
    if re.search(r"\b3\s*0\s*(l|i|litres?)\b", t):
        add(18, "cylindree 3.0 annoncee")
    if re.search(r"\b218\s*(ch|cv)\b", t):
        add(12, "218 ch")
    if re.search(r"\b(6|six)\s*cylindres?\b", t):
        add(10, "6 cylindres")

    # --- Carburant
    carb = normaliser(annonce.get("carburant", ""))
    if "essence" in carb or re.search(r"\bessence\b", t):
        add(15, "essence")
    elif "diesel" in carb:
        add(-60, "carburant diesel")

    # --- Discriminant critique 2.5 (N52) vs 3.0 (N53)
    annee = annonce.get("annee")
    if annee:
        if annee >= 2008:
            add(25, "annee {} -> LCI = N53 3.0".format(annee))
        elif annee == 2007:
            add(5, "2007 = annee charniere, a verifier")
        else:
            add(-50, "annee {} -> pre-LCI = N52 2.5".format(annee))

    # Mention explicite d'une 2.5 : « 2.5 », « 2,5 », « 2.5l », « 2500 »
    if re.search(r"\b2\s*[.,]?\s*5\s*(l|litres?|i)?\b", t) or re.search(r"\bn52\b", t):
        add(-35, "indice cylindree 2.5 / N52")

    # --- Exclusions
    exclusions = [
        (r"\b325\s*d\b", "325d = diesel", -70),
        (r"\b3(20|18|16|30|35)\s*[id]?\b", "autre motorisation de la gamme", -40),
        (r"\be9[23]\b", "E92/E93 = coupe/cabriolet, pas E90/E91", -40),
        (r"\be(46|36|30|21)\b", "generation anterieure", -60),
        (r"\bpour\s+pieces?\b|\bepave\b|\baccidente\b|\bmoteur\s+hs\b", "vehicule HS", -45),
        (r"\bxdrive\b", "xDrive (souvent hors cible)", -10),
    ]
    for motif, libelle, points in exclusions:
        if re.search(motif, t):
            add(points, libelle)

    return score, raisons


def verdict(score):
    if score >= SEUIL_NOTIFIER:
        return "NOTIFIER"
    if score >= SEUIL_A_REVOIR:
        return "A_REVOIR"
    return "IGNORER"
