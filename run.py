#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tracker BMW 325i E90/E91 3.0 essence — point d'entree.

Chaine : Google News RSS -> parsing -> filtre pieces -> scoring -> dedup -> Telegram

Premiere execution (« amorce ») : tout le passif est marque comme deja vu et
AUCUNE notification n'est envoyee. Sans ca, le premier run enverrait ~450
messages d'un coup. Les executions suivantes ne notifient que le nouveau.
"""
import argparse
import sys
import time
from datetime import datetime, timezone

from tracker import filters, notify, parser as rss, scoring, sources, state

PAUSE_ENTRE_ENVOIS = 1.0     # respecte la limite de debit de Telegram
MAX_ENVOIS_PAR_RUN = 15      # garde-fou anti-avalanche


def log(msg):
    print(msg, flush=True)


def collecter_annonces(mode_test=False):
    """Renvoie (annonces_uniques, echecs)."""
    if mode_test:
        xmls, echecs = {}, []
        for r in sources.requetes()[:3]:
            x = sources.recuperer(r)
            if x:
                xmls[r] = x
            else:
                echecs.append(r)
            time.sleep(sources.DELAI_ENTRE_REQUETES)
    else:
        xmls, echecs = sources.collecter(journal=log)

    par_guid = {}
    for requete, xml in xmls.items():
        for a in rss.parser(xml):
            par_guid.setdefault(a["guid"], a)
    return list(par_guid.values()), echecs


def enrichir(a):
    a["annee"] = rss.annee(a["titre"])
    a["kilometrage"] = rss.kilometrage(a["titre"])
    a["prix"] = rss.prix(a["titre"])
    a["carburant"] = rss.carburant(a["titre"])
    return a


def ping(chat_id_cible=None, texte_force=None):
    """Envoi de controle.

    Sans --ping-chat-id : envoie a TOUS les destinataires configures
    (TELEGRAM_CHAT_ID) le message de controle standard.

    Avec --ping-chat-id : envoie UNIQUEMENT a ce chat_id, en ignorant
    totalement destinataires(). Sert a valider un chat_id avant de
    l'ajouter a la configuration reelle -- aucune ecriture d'etat, aucun
    passage par main(), donc aucune notification "reelle" declenchee.
    """
    token_ok = bool(notify._token())
    if chat_id_cible:
        if not token_ok:
            log("ERREUR : TELEGRAM_BOT_TOKEN absent.")
            return 1
    elif not notify.disponible():
        log("ERREUR : TELEGRAM_BOT_TOKEN ou TELEGRAM_CHAT_ID absent.")
        return 1

    if texte_force:
        texte = texte_force
    else:
        horodatage = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        exemple = {
            "titre": "BMW 325i E91 Touring 218ch 3.0 essence",
            "annee": 2009, "prix": 11980, "kilometrage": 146050,
            "carburant": "essence", "source": "Leboncoin",
            "lien": "https://github.com/erwanmichelbusiness-bit/e90-tracker",
        }
        texte = ("\u2705 <b>e90-tracker op\u00e9rationnel</b>\n"
                 "Contr\u00f4le du " + horodatage + "\n"
                 "Voici \u00e0 quoi ressemblera une vraie alerte :\n\n"
                 + notify.formater(exemple, 117, "NOTIFIER"))

    if chat_id_cible:
        rep = notify.envoyer_a(chat_id_cible, texte)
        if rep.get("ok"):
            log("Message de test envoye au chat_id {}.".format(chat_id_cible))
            return 0
        log("ECHEC pour {} : {}".format(chat_id_cible, rep.get("description")))
        return 1

    rep = notify.envoyer(texte)
    if rep["ok"]:
        log("Message de controle envoye a : {}".format(", ".join(rep["reussites"])))
        if rep["echecs"]:
            log("  ECHEC pour : {}".format(", ".join(rep["echecs"])))
        return 0
    log("ECHEC pour tous les destinataires : {}".format(rep["detail"]))
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="n'envoie rien et n'ecrit pas l'etat")
    ap.add_argument("--test", action="store_true",
                    help="3 requetes seulement, pour un essai rapide")
    ap.add_argument("--force-amorce", action="store_true",
                    help="refait l'amorce (re-marque tout comme vu)")
    ap.add_argument("--ping", action="store_true",
                    help="envoie un unique message de controle et sort")
    ap.add_argument("--ping-chat-id", metavar="ID", default=None,
                    help="teste UN chat_id precis, sans toucher a la config reelle")
    ap.add_argument("--ping-text", metavar="TEXTE", default=None,
                    help="texte personnalise pour --ping / --ping-chat-id")
    args = ap.parse_args()

    if args.ping or args.ping_chat_id:
        return ping(chat_id_cible=args.ping_chat_id, texte_force=args.ping_text)

    debut = time.time()
    log("=== Tracker E90 — {} ===".format(
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")))

    etat = state.charger()
    amorce = args.force_amorce or not etat.get("amorce")
    if amorce:
        log("MODE AMORCE : le passif est marque comme vu, aucune notification.")

    log("Collecte ({} requetes)...".format(
        3 if args.test else len(sources.requetes())))
    annonces, echecs = collecter_annonces(mode_test=args.test)
    log("  -> {} annonces uniques, {} requete(s) en echec".format(len(annonces), len(echecs)))

    if echecs and len(echecs) == (3 if args.test else len(sources.requetes())):
        log("ERREUR : toutes les requetes ont echoue. Source injoignable.")
        return 1

    pieces = [a for a in annonces if filters.est_piece(a["titre"])]
    vehicules = [a for a in annonces if not filters.est_piece(a["titre"])]
    log("  -> {} pieces detachees ecartees, {} vehicules candidats".format(
        len(pieces), len(vehicules)))

    a_envoyer = []
    nouvelles = 0
    for a in vehicules:
        if not state.est_nouvelle(etat, a["guid"]):
            continue
        nouvelles += 1
        enrichir(a)
        s, raisons = scoring.scorer(a)
        v = scoring.verdict(s)
        if v in ("NOTIFIER", "A_REVOIR"):
            a_envoyer.append((s, v, a, raisons))

    log("  -> {} nouvelles depuis la derniere execution".format(nouvelles))
    a_envoyer.sort(key=lambda x: -x[0])
    log("  -> {} au-dessus du seuil de notification".format(len(a_envoyer)))

    if amorce:
        for a in vehicules + pieces:
            state.marquer(etat, a["guid"])
        etat["amorce"] = True
        log("Amorce terminee : {} annonces marquees comme vues.".format(len(etat["vues"])))
    else:
        envoyes = 0
        for s, v, a, raisons in a_envoyer:
            if envoyes >= MAX_ENVOIS_PAR_RUN:
                log("  garde-fou atteint ({} envois), le reste au prochain run".format(
                    MAX_ENVOIS_PAR_RUN))
                break
            texte = notify.formater(a, s, v)
            if args.dry_run or not notify.disponible():
                log("  [SIMULATION] {} score={} {}".format(v, s, a["titre"][:60]))
                envoyes += 1
            else:
                rep = notify.envoyer(texte)
                if rep.get("ok"):
                    state.marquer(etat, a["guid"])
                    envoyes += 1
                    log("  [ENVOYE] {} score={} {}".format(v, s, a["titre"][:60]))
                else:
                    log("  [ECHEC TELEGRAM] {}".format(rep.get("description")))
                time.sleep(PAUSE_ENTRE_ENVOIS)
        # Tout est marque comme vu, SAUF la file d'attente non envoyee :
        # ces annonces doivent repasser au prochain run.
        en_attente = {x[2]["guid"] for x in a_envoyer[envoyes:]}
        for a in vehicules + pieces:
            if a["guid"] not in en_attente:
                state.marquer(etat, a["guid"])

    purges = state.purger(etat)
    etat["derniere_execution"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if purges:
        log("  -> {} entrees purgees (> {} jours)".format(purges, state.RETENTION_JOURS))

    if not args.dry_run:
        state.sauvegarder(etat)
        log("Etat sauvegarde : {} annonces connues.".format(len(etat["vues"])))

    log("Termine en {:.1f} s".format(time.time() - debut))
    return 0


if __name__ == "__main__":
    sys.exit(main())
