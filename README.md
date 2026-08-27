# e90-tracker

Surveillance automatique d'annonces **BMW 325i E90/E91 3.0 essence** (N53B30UL).
Fonctionne 24/7 sur GitHub Actions, notifie par Telegram, coût 0 €/mois.

Projet totalement indépendant. Aucun lien avec un autre dépôt.

## Chaîne

```
Google News RSS (35 requêtes ciblées, 5 plateformes)
  -> parsing RSS 2.0
  -> filtre pièces détachées
  -> scoring E90/E91 3.0
  -> déduplication par GUID
  -> Telegram
```

## Le piège que ce tracker gère

« 325i » recouvre **deux moteurs différents** :

| Période | Moteur | Cylindrée | Puissance |
|---|---|---|---|
| 2005 → ~09/2007 (pré-LCI) | N52B25 | **2.5 L** | 218 ch |
| ~09/2007 → 2011 (LCI) | N53B30UL | **3.0 L** | 218 ch |

La cible est la **3.0**, donc les LCI de fin 2007 et après. Presque aucune
annonce ne précise le code moteur : **l'année est le seul discriminant fiable**.
Une annonce sans année reste indécidable et part en « à revoir » plutôt que
d'être jetée.

## Décisions de conception

- **Recherche large, filtrage intelligent.** 7 gabarits de requête par
  plateforme. Le recouvrement mesuré entre gabarits est faible (10 annonces
  sur 12 n'apparaissaient que dans une seule variante), d'où la redondance.
- **Le flux plafonne à 100 items par requête.** Une requête large est donc
  noyée : `BMW site:leboncoin.fr` ne remonte aucun 325i. Seules des requêtes
  ciblées fonctionnent.
- **Faux positifs assumés.** Mieux vaut quelques annonces inutiles qu'une
  vraie 325i ratée. Seuils : notification ≥ 70, « à revoir » 40-69.
- **État dans le dépôt**, pas dans le cache Actions (purgé à 7 jours). Effet
  utile : le commit compte comme activité et empêche GitHub de désactiver le
  cron après 60 jours.

## Limites connues

- **Fraîcheur 2 à 8 h.** Le flux dépend de l'indexation Google. Un cron plus
  serré n'y changerait rien.
- **Le lien pointe vers `news.google.com`.** Le GUID encode un jeton opaque,
  l'URL réelle n'est pas extractible côté serveur. Vérifié : le lien se
  résout correctement vers l'annonce dans un navigateur.
- **Zone grise CGU.** Interroger un flux RSS public est l'usage prévu d'un
  RSS, mais les conditions de Google interdisent « l'accès par moyens
  automatisés ». Usage personnel, faible volume, requêtes espacées de 1,2 s.

## Configuration

Deux secrets GitHub (Settings → Secrets → Actions) :

| Secret | Obtention |
|---|---|
| `TELEGRAM_BOT_TOKEN` | `@BotFather` → `/newbot` |
| `TELEGRAM_CHAT_ID` | envoyer un message au bot, puis `getUpdates` |

## Usage local

```bash
python3 run.py --test --dry-run   # 3 requêtes, aucun envoi, aucune écriture
python3 run.py --dry-run          # tout, sans envoi
python3 -m unittest discover -s tests
```

Le **premier run réel** est une amorce : tout le passif est marqué comme vu
et rien n'est envoyé. Sans ça, il partirait ~450 messages d'un coup.
