# -*- coding: utf-8 -*-
"""Filtre pieces detachees.

22 % des resultats mesures pendant l'audit etaient des pieces et non des
vehicules. Un cas est passe au travers d'une premiere version du filtre
(« Arbre de transmission BMW SERIE 3 E90 E91 325i 3.0i 218 cv ») : la liste
ci-dessous a ete elargie en consequence.
"""
import re
import unicodedata

_PIECES = r"""
arbre\s+de\s+transmission|cardan|transmission\s+avant|boite\s+de\s+vitesse|
boitier|ligne\s+d.?echappement|echappement|silencieux|catalyseur|collecteur|
turbo|injecteur|pompe\s+(?:a\s+)?(?:eau|huile|injection|carburant)|
radiateur|intercooler|durite|thermostat|calorstat|
jante|jantes|pneu|pneus|enjoliveur|roue\s+de\s+secours|
phare|feu\s+arriere|optique|clignotant|ampoule|xenon\s+seul|
retroviseur|pare.?choc|pare.?brise|capot|aile\s+avant|aile\s+arriere|hayon|
portiere|porte\s+avant|porte\s+arriere|coffre\s+seul|
siege|sieges|banquette|volant|pommeau|levier|tapis|garniture|accoudoir|
compteur|calculateur|ecu|boitier\s+electronique|faisceau|
alternateur|demarreur|batterie|bobine|bougie|
embrayage|volant\s+moteur|amortisseur|ressort|suspension|triangle|rotule|
biellette|silentbloc|barre\s+stabilisatrice|
disque\s+de\s+frein|plaquette|etrier|maitre.?cylindre|
culasse|vilebrequin|piston|bielle|joint\s+de\s+culasse|carter|
filtre\s+(?:a\s+)?(?:air|huile|habitacle|gasoil)|courroie|distribution|galet|
sonde|capteur|debitmetre|vanne\s+egr|papillon|
kit\s+(?:de\s+)?|support\s+moteur|silentblocs|
piece|pieces|detachee|detachees|casse\s+auto|
autoradio|gps\s+seul|antenne|haut.?parleur|amplificateur|
moteur\s+nu|moteur\s+seul|bloc\s+moteur|culbuteur|
becquet|aileron|bas\s+de\s+caisse|calandre|logo|embleme|badge\s+coffre|
housse|couvre|protection|attelage|barre\s+de\s+toit|coffre\s+de\s+toit
"""
_RE_PIECES = re.compile("|".join(p.strip() for p in _PIECES.split("|") if p.strip()),
                        re.I | re.X)

# Un titre qui ressemble a un vehicule complet (prix, km, annee, mentions
# administratives) beneficie du doute meme si un mot de piece y figure.
_RE_VEHICULE = re.compile(
    r"\b(\d{2,3}\s*000\s*km|\d{1,3}[ .]\d{3}\s*km|"
    r"controle\s+technique|\bct\s+ok\b|carte\s+grise|premiere\s+main|"
    r"\d{1,2}\s*\d{3}\s*€|non\s+roulante|entretien\s+complet|full\s+options?)\b",
    re.I,
)


def _norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip()


# Certains mots ne designent une piece que s'ils ouvrent le titre
# (« Ligne bmw 325i » = ligne d'echappement ; « ... Pack Ligne Luxe » = finition).
_RE_PIECE_EN_TETE = re.compile(
    r"^\s*(ligne|linge|paire|lot|jeu|moteur|boite|boitier|kit|pack\s+de)\b", re.I
)

# Pages de categorie / listes de resultats, pas des annonces individuelles.
_RE_PAGE_LISTE = re.compile(
    r"^\s*annonces?\s+\w+|"
    r"\b(d.?occasion|neuves?)\s*[-–]\s*voitures?\s*$|"
    r"\bacheter\s+une?\b|\bfiche\s+technique\b|\bargus\b|"
    r"\bcote\s+auto\b|\bprevente\b|\ble\s+parking\b",
    re.I,
)


def est_piece(titre):
    """True si le titre designe une piece detachee plutot qu'un vehicule."""
    t = _norm(titre)
    if _RE_PAGE_LISTE.search(t):
        return True
    if not _RE_PIECES.search(t) and not _RE_PIECE_EN_TETE.search(t):
        return False
    # Signal vehicule fort -> on ne jette pas (on prefere un faux positif).
    return not _RE_VEHICULE.search(t)
