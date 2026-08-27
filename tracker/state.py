# -*- coding: utf-8 -*-
"""Etat persistant : quelles annonces ont deja ete notifiees.

Stocke dans le depot (state/seen.json) plutot que dans le cache Actions :
le cache est purge apres 7 jours sans acces et ses entrees sont immuables.
Le commit a aussi un effet utile : il compte comme activite du depot, ce qui
empeche GitHub de desactiver le cron apres 60 jours d'inactivite.
"""
import json
import os
from datetime import datetime, timedelta, timezone

CHEMIN_DEFAUT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "state", "seen.json"
)
RETENTION_JOURS = 30


def charger(chemin=CHEMIN_DEFAUT):
    try:
        with open(chemin, encoding="utf-8") as f:
            donnees = json.load(f)
    except (OSError, ValueError):
        donnees = {}
    if not isinstance(donnees, dict):
        donnees = {}
    donnees.setdefault("vues", {})
    donnees.setdefault("amorce", False)
    donnees.setdefault("derniere_execution", None)
    return donnees


def sauvegarder(etat, chemin=CHEMIN_DEFAUT):
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    tmp = chemin + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(etat, f, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, chemin)


def est_nouvelle(etat, guid):
    return guid not in etat["vues"]


def marquer(etat, guid):
    etat["vues"][guid] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def purger(etat, jours=RETENTION_JOURS):
    """Supprime les entrees plus anciennes que `jours`. Renvoie le nombre purge."""
    limite = datetime.now(timezone.utc) - timedelta(days=jours)
    a_supprimer = []
    for guid, vu_le in etat["vues"].items():
        try:
            d = datetime.strptime(vu_le, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        if d < limite:
            a_supprimer.append(guid)
    for guid in a_supprimer:
        del etat["vues"][guid]
    return len(a_supprimer)
