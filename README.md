# RandomFlow

Stimulus de **flux optique** paramétrable : points lumineux sur fond sombre, avec une proportion de mouvement cohérent (centre → bords) et du bruit (brownien ou inverse). Conçu pour des expériences de perception où l’observateur classe chaque scène comme **bruit** ou **mouvement**.

## Prérequis

- Python **≥ 3.10**
- [uv](https://docs.astral.sh/uv/) (recommandé) ou `pip`

## Installation

### Avec uv (recommandé)

```bash
git clone https://github.com/ROSITO/randomflow.git
cd randomflow
uv sync
```

### Avec pip

```bash
pip install -r requirements.txt
```

## Lancement

```bash
# Session complète (liste de configs dans config.json)
uv run optical-flow

# Fichier de config personnalisé
uv run optical-flow mon_experiment.json

# Équivalent pip
python optical_flow.py
```

## Contrôles

| Touche | Action |
|--------|--------|
| **B** (défaut) | Réponse : **bruit** — passage à la scène suivante |
| **M** (défaut) | Réponse : **mouvement** — passage à la scène suivante |
| **Échap** | Quitter et enregistrer les réponses déjà données |
| Fermer la fenêtre | Quitter |

Les touches sont configurables via `key_noise` et `key_motion` dans `config.json`.

## Configuration

Le fichier `config.json` contient :

- une liste **`configs`** : scènes à présenter ;
- des options de session : touches, fichier de sortie, répétitions, warmup.

Exemple :

```json
{
  "configs": [
    {
      "dot_size": 4,
      "dot_speed": 2.0,
      "dot_color": [255, 255, 255],
      "dot_number": 200,
      "dot_coherence": 0.8,
      "spawn_radius": 120,
      "brownian_sigma": 1.2,
      "noise_mode": "brownian"
    }
  ],
  "key_noise": "b",
  "key_motion": "m",
  "output_file": "responses.json",
  "loop": 1,
  "warmup_loops": 120
}
```

### Paramètres principaux

| Paramètre | Rôle |
|-----------|------|
| `dot_coherence` | Fraction de points en flux concentrique (0–1) |
| `spawn_radius` | Disque central : spawn des points cohérents, disparition des points reverse |
| `noise_mode` | `"brownian"` (marche aléatoire) ou `"reverse"` (bord → centre) |
| `loop` | Nombre de passages sur toute la liste de configs |
| `warmup_loops` | Frames de simulation avant affichage de chaque scène |

Documentation détaillée :

- [Référence configuration](docs/CONFIGURATION.md)
- [Comportement des points](docs/COMPORTEMENT.md)

## Résultats

À la fin de la session, un fichier JSON (par défaut `responses.json`) contient :

```json
{
  "trials": [
    {
      "config": { "...": "..." },
      "response": "motion",
      "response_time_ms": 2340
    }
  ]
}
```

Ce fichier est ignoré par git (voir `.gitignore`).

## Structure du projet

```
randomflow/
├── optical_flow.py      # Moteur d’affichage et session
├── config.json          # Configurations d’expérience
├── pyproject.toml       # Métadonnées et dépendances (uv)
├── uv.lock
├── requirements.txt     # Dépendances pip
├── README.md
└── docs/
    ├── CONFIGURATION.md
    └── COMPORTEMENT.md
```

## Dépendances

- **pygame** ≥ 2.6.1 — affichage et entrées clavier

Voir `requirements.txt` ou `pyproject.toml`.

## Licence

Projet expérimental — voir le dépôt pour les conditions d’utilisation.
