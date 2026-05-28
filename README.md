# RandomFlow

Stimulus de **flux optique** paramétrable : points lumineux sur fond sombre, avec une proportion de mouvement cohérent (centre → bords) et du bruit (brownien ou inverse). Conçu pour des expériences de perception où l’observateur classe chaque scène comme **bruit** ou **mouvement**.

## Prérequis

- Python **≥ 3.10**
- [uv](https://docs.astral.sh/uv/) (recommandé) ou `pip`

## Installation

### Avec uv (recommandé)

```bash
cd randomflow
uv sync
```

### Avec pip

```bash
pip install -r requirements.txt
```

### Windows

Si `python` n'est pas reconnu, utiliser le lanceur Python Windows :

```bat
py -m pip install -r requirements.txt
py optical_flow.py
```

Avec `uv`, rester dans le même dossier et lancer :

```bat
uv sync
uv run optical-flow
```

Ne pas mélanger les environnements : si le script est lancé avec `py optical_flow.py`, installer `pygame` avec `py -m pip install -r requirements.txt`. Si le script est lancé avec `uv run optical-flow`, installer avec `uv sync`.

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
| **Espace** | Fixation initiale : démarrer la manip ; entre stimuli : passer après le temps minimum |
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
      "dot_speed": 1.2,
      "dot_color": [255, 255, 255],
      "dot_number": 200,
      "dot_coherence": 0.8,
      "spawn_radius": 120,
      "brownian_sigma": 1.2,
      "perspective_strength": 2.5,
      "size_depth_scale": 0.35,
      "noise_mode": "brownian"
    }
  ],
  "key_noise": "b",
  "key_motion": "m",
  "output_file": "responses.json",
  "loop": 1,
  "warmup_loops": 120,
  "fixation_min_ms": 500,
  "fixation_timeout_ms": 5000,
  "fixation_size": 5,
  "fixation_color": [255, 255, 255]
}
```

### Paramètres principaux

| Paramètre | Rôle |
|-----------|------|
| `dot_coherence` | Fraction de points en flux concentrique (0–1) |
| `spawn_radius` | Disque central : spawn des points cohérents, disparition des points reverse |
| `perspective_strength` | Intensité de l’effet profondeur (accélération vers les bords) |
| `size_depth_scale` | Variation de taille selon la distance au centre |
| `noise_mode` | `"brownian"` (marche aléatoire) ou `"reverse"` (bord → centre) |
| `loop` | Nombre de passages sur toute la liste de configs |
| `warmup_loops` | Frames de simulation avant affichage de chaque scène |
| `fixation_min_ms` | Temps minimum du point de fixation entre deux stimuli |
| `fixation_timeout_ms` | Timeout du point de fixation avant passage automatique |

Documentation détaillée :

- [Référence configuration](docs/CONFIGURATION.md)
- [Comportement des points](docs/COMPORTEMENT.md)

## Résultats

À la fin de la session, un fichier JSON horodaté est créé. Avec la valeur par défaut `responses.json`, le fichier aura par exemple ce nom :

```text
responses_20260526_125430.json
```

Il contient :

```json
{
  "trials": [
    {
      "config": { "...": "..." },
      "response": "motion",
      "response_time_ms": 2340,
      "fixation_after_ms": 850
    }
  ]
}
```

Ces fichiers sont ignorés par git (voir `.gitignore`).

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
