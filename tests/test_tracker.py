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

    def test_fichier_corrompu(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "seen.json")
            with open(p, "w") as f:
                f.write("{pas du json")
            self.assertEqual(state.charger(p)["vues"], {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
