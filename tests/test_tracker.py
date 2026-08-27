# -*- coding: utf-8 -*-
"""Tests hors-ligne : aucune requete reseau."""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tracker import filters, parser as rss, scoring, state  # noqa: E402

FLUX = """<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>BMW 325i E91 218ch 3.0 essence 2009 - Leboncoin</title>
<link>https://news.google.com/rss/articles/AAA?oc=5</link>
<guid isPermaLink="false">GUID_A</guid>
<pubDate>Wed, 26 Aug 2026 07:59:34 GMT</pubDate>
<source url="https://www.leboncoin.fr">Leboncoin</source></item>
<item><title>Cardan e90 325i - Leboncoin</title>
<link>https://news.google.com/rss/articles/BBB?oc=5</link>
<guid isPermaLink="false">GUID_B</guid>
<pubDate>Wed, 26 Aug 2026 08:00:00 GMT</pubDate>
<source url="https://www.leboncoin.fr">Leboncoin</source></item>
</channel></rss>"""


class TestParser(unittest.TestCase):
    def test_parse(self):
        a = rss.parser(FLUX)
        self.assertEqual(len(a), 2)
        self.assertEqual(a[0]["guid"], "GUID_A")
        self.assertEqual(a[0]["domaine"], "leboncoin.fr")
        # le suffixe " - Leboncoin" doit etre retire
        self.assertNotIn("- Leboncoin", a[0]["titre"])

    def test_xml_malforme(self):
        self.assertEqual(rss.parser("<rss><item>casse"), [])

    def test_extraction(self):
        self.assertEqual(rss.annee("BMW 325i 2009 essence"), 2009)
        self.assertIsNone(rss.annee("BMW 325i essence"))
        self.assertEqual(rss.kilometrage("BMW 325i 188 000 km"), 188000)
        self.assertEqual(rss.prix("BMW 325i 11 980 €"), 11980)
        self.assertEqual(rss.prix("BMW 325i 9 490 EUR"), 9490)
        self.assertIsNone(rss.prix("BMW 325i 218 ch"))
        self.assertEqual(rss.carburant("BMW 325i essence"), "essence")


class TestFiltre(unittest.TestCase):
    def test_pieces(self):
        for t in ["Cardan e90 325i", "Ligne bmw 325i/330i e90",
                  "Moteur bmw 325i 330i e90", "Lot 4 jantes BMW e90",
                  "Annonces bmw 325 touring d'occasion - Voitures"]:
            self.assertTrue(filters.est_piece(t), t)

    def test_vehicules(self):
        for t in ["BMW 325i E90 218ch 3.0l LCI", "BMW e90 325i 2011",
                  "BMW Serie 3 325i Pack Ligne Luxe 2009 essence"]:
            self.assertFalse(filters.est_piece(t), t)


class TestScoring(unittest.TestCase):
    def cas(self, titre, attendu, **kw):
        kw["titre"] = titre
        s, _ = scoring.scorer(kw)
        self.assertEqual(scoring.verdict(s), attendu,
                         "{} -> {} ({})".format(titre, scoring.verdict(s), s))

    def test_cible(self):
        self.cas("BMW E91 325i N53 3.0", "NOTIFIER", carburant="essence", annee=2008)
        self.cas("BMW 325i E90 LCI 218ch", "NOTIFIER", carburant="essence", annee=2009)

    def test_pre_lci_ecarte(self):
        self.cas("BMW 325i E90 2.5 218ch", "IGNORER", annee=2005)

    def test_hors_cible(self):
        self.cas("BMW 325d E91 Touring", "IGNORER", carburant="diesel", annee=2009)
        self.cas("BMW 320i E90", "IGNORER", carburant="essence", annee=2009)
        self.cas("BMW 325i E46", "IGNORER", annee=2003)

    def test_ambigu_va_en_a_revoir(self):
        self.cas("BMW e90 325i", "A_REVOIR")


class TestEtat(unittest.TestCase):
    def test_cycle(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "seen.json")
            e = state.charger(p)
            self.assertTrue(state.est_nouvelle(e, "X"))
            state.marquer(e, "X")
            state.sauvegarder(e, p)
            self.assertFalse(state.est_nouvelle(state.charger(p), "X"))

    def test_livraison_par_destinataire(self):
        """Un destinataire en echec doit etre re-cible, pas l'autre."""
        erwan, nick = "7193762179", "7701794823"
        tous = [erwan, nick]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "seen.json")
            e = state.charger(p)
            self.assertEqual(state.destinataires_manquants(e, "AD", tous), tous)
            state.marquer(e, "AD", livre_a=[erwan])
            self.assertEqual(state.destinataires_manquants(e, "AD", tous), [nick])
            self.assertTrue(state.deja_livre(e, "AD", erwan))
            state.marquer(e, "AD", livre_a=[nick])
            self.assertEqual(state.destinataires_manquants(e, "AD", tous), [])

    def test_entrees_historiques_non_renvoyees(self):
        """Le passif de l'amorce (format str) ne doit pas etre re-notifie."""
        e = state.charger(os.path.join(tempfile.gettempdir(), "_absent.json"))
        e["vues"]["VIEILLE"] = "2026-08-27T07:48:36Z"
        self.assertEqual(
            state.destinataires_manquants(e, "VIEILLE", ["1", "2"]), [])

    def test_purge_gere_les_deux_formats(self):
        e = state.charger(os.path.join(tempfile.gettempdir(), "_absent2.json"))
        e["vues"]["A"] = "2020-01-01T00:00:00Z"
        e["vues"]["B"] = {"vu": "2020-01-01T00:00:00Z", "livre": ["1"]}
        e["vues"]["C"] = {"vu": "2099-01-01T00:00:00Z", "livre": []}
        self.assertEqual(state.purger(e, jours=30), 2)
        self.assertEqual(sorted(e["vues"]), ["C"])

    def test_fichier_corrompu(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "seen.json")
            with open(p, "w") as f:
                f.write("{pas du json")
            self.assertEqual(state.charger(p)["vues"], {})


class TestDestinataires(unittest.TestCase):
    """Parsing de TELEGRAM_CHAT_ID : un seul secret, plusieurs destinataires."""

    def _avec(self, valeur):
        import os as _os
        from tracker import notify
        ancien = _os.environ.get("TELEGRAM_CHAT_ID")
        _os.environ["TELEGRAM_CHAT_ID"] = valeur
        try:
            return notify.destinataires()
        finally:
            if ancien is None:
                _os.environ.pop("TELEGRAM_CHAT_ID", None)
            else:
                _os.environ["TELEGRAM_CHAT_ID"] = ancien

    def test_deux_destinataires(self):
        self.assertEqual(self._avec("7193762179,7701794823"),
                         ["7193762179", "7701794823"])

    def test_espaces_et_vides_ignores(self):
        self.assertEqual(self._avec(" 111 , 222 ,, "), ["111", "222"])

    def test_retrocompatible_un_seul(self):
        self.assertEqual(self._avec("7193762179"), ["7193762179"])

    def test_vide(self):
        self.assertEqual(self._avec(""), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
