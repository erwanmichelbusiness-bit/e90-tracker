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


def _maintenant():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _entree(etat, guid):
    """Normalise une entree. Deux formats coexistent :
      - str  : format historique, signifie « traitee, livree a tous »
      - dict : {"vu": horodatage, "livre": [chat_id, ...]}
    Le format historique est conserve tel quel pour eviter une migration
    des ~2000 entrees deja en place.
    """
    valeur = etat["vues"].get(guid)
    if valeur is None:
        return None
    if isinstance(valeur, str):
        return {"vu": valeur, "livre": None}  # None = considere livre a tous
    return valeur


def deja_livre(etat, guid, chat_id):
    e = _entree(etat, guid)
    if e is None:
        return False
    if e.get("livre") is None:
        return True
    return chat_id in e["livre"]


def destinataires_manquants(etat, guid, tous):
    """Destinataires qui n'ont pas encore recu cette annonce."""
    return [c for c in tous if not deja_livre(etat, guid, c)]


def marquer(etat, guid, livre_a=None):
    """Marque l'annonce comme traitee.

    livre_a=None  -> annonce ecartee (sous le seuil, piece, amorce) :
                     format compact, aucune livraison a suivre.
    livre_a=[...] -> ajoute ces destinataires a la liste des livraisons,
                     sans ecraser celles deja enregistrees.
    """
    if livre_a is None:
        if guid not in etat["vues"]:
            etat["vues"][guid] = _maintenant()
        return
    e = _entree(etat, guid) or {"vu": _maintenant(), "livre": []}
    if e.get("livre") is None:
        return  # deja livre a tous (format historique)
    e["livre"] = sorted(set(e["livre"]) | set(livre_a))
    e.setdefault("vu", _maintenant())
    etat["vues"][guid] = e


def purger(etat, jours=RETENTION_JOURS):
    """Supprime les entrees plus anciennes que `jours`. Renvoie le nombre purge."""
    limite = datetime.now(timezone.utc) - timedelta(days=jours)
    a_supprimer = []
    for guid, valeur in etat["vues"].items():
        vu_le = valeur if isinstance(valeur, str) else valeur.get("vu")
        try:
            d = datetime.strptime(vu_le, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
        if d < limite:
            a_supprimer.append(guid)
    for guid in a_supprimer:
        del etat["vues"][guid]
    return len(a_supprimer)
