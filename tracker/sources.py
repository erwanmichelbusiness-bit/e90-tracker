# -*- coding: utf-8 -*-
"""Sources : flux RSS publics Google News, restreints par `site:`.

Constat de l'audit : sans restriction `site:`, le flux se comporte comme un
index d'actualites et ne remonte aucune annonce. Avec `site:`, il remonte de
vraies annonces des 5 plateformes. Le flux plafonne a 100 items par requete,
donc une requete large est noyee : il faut plusieurs requetes ciblees.
"""
import time
import urllib.error
import urllib.parse
import urllib.request

PLATEFORMES = [
    "leboncoin.fr",
    "lacentrale.fr",
    "autoscout24.fr",
    "paruvendu.fr",
    "largus.fr",
]

# Filet de rappel : chaque gabarit attrape une facon differente d'ecrire
# l'annonce. Le recouvrement mesure entre gabarits est faible (10 annonces
# sur 12 n'apparaissaient que dans une seule variante), d'ou la redondance.
GABARITS = [
    '"325i" site:{d}',
    '"325 i" site:{d}',
    '"325i" E90 site:{d}',
    '"325i" E91 site:{d}',
    'BMW 325 site:{d} when:7d',
    'BMW "3.0" essence site:{d} when:7d',
    'BMW 218 ch site:{d} when:7d',
]

BASE = "https://news.google.com/rss/search"
UA = "e90-tracker/1.0 (+usage personnel, faible volume)"
DELAI_ENTRE_REQUETES = 1.2  # politesse : ~1 requete/seconde maximum


def requetes():
    """Toutes les requetes a executer, ordre stable."""
    return [g.format(d=d) for d in PLATEFORMES for g in GABARITS]


def url_flux(requete):
    params = urllib.parse.urlencode(
        {"q": requete, "hl": "fr", "gl": "FR", "ceid": "FR:fr"}
    )
    return "{}?{}".format(BASE, params)


def recuperer(requete, timeout=25, essais=2):
    """Renvoie le XML brut, ou None si la source est injoignable."""
    url = url_flux(requete)
    for tentative in range(essais):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=timeout) as rep:
                return rep.read(1_500_000).decode("utf-8", "replace")
        except (urllib.error.URLError, OSError):
            if tentative + 1 >= essais:
                return None
            time.sleep(2)
    return None


def collecter(journal=None):
    """Execute toutes les requetes. Renvoie (xml_par_requete, echecs)."""
    resultats, echecs = {}, []
    for i, r in enumerate(requetes()):
        xml = recuperer(r)
        if xml is None:
            echecs.append(r)
        else:
            resultats[r] = xml
        if journal:
            journal("  [{}/{}] {} -> {}".format(
                i + 1, len(requetes()), r, "OK" if xml else "ECHEC"))
        time.sleep(DELAI_ENTRE_REQUETES)
    return resultats, echecs
