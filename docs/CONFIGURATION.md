# Référence de configuration

Fichier principal : `config.json` à la racine du projet.

## Structure globale

```json
{
  "configs": [ /* ... */ ],
  "key_noise": "b",
  "key_motion": "m",
  "output_file": "responses.json",
  "loop": 1,
  "warmup_loops": 120
}
```

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `configs` | liste | — | Liste des scènes à présenter (obligatoire en mode session). |
| `key_noise` | string | `"b"` | Touche pour classer la scène comme **bruit**. |
| `key_motion` | string | `"m"` | Touche pour classer la scène comme **mouvement**. |
| `output_file` | string | `"responses.json"` | Base du fichier JSON de sortie (relatif au dossier du config). Un timestamp est ajouté automatiquement. |
| `loop` | entier | `1` | Nombre de passages complets sur la liste `configs` (ordre mélangé à chaque lancement). |
| `warmup_loops` | entier | `60` | Nombre de mises à jour de simulation **sans affichage** avant chaque scène. |

## Paramètres par scène (`configs[]`)

Chaque élément de `configs` est un objet avec les champs suivants :

| Paramètre | Type | Défaut | Description |
|-----------|------|--------|-------------|
| `dot_size` | entier | `4` | Rayon des points en pixels. |
| `dot_speed` | float | `1.2` | Vitesse des points en mouvement cohérent ou reverse (px / frame). |
| `dot_color` | `[R,G,B]` | `[255,255,255]` | Couleur RGB (0–255). Hex `#RRGGBB` accepté. |
| `dot_number` | entier | `200` | Nombre total de points à l’écran. |
| `dot_coherence` | float | `0.8` | Proportion de points **concentriques** (0.0–1.0). Le reste est du bruit (brownien ou reverse). |
| `spawn_radius` | float | `80` | Rayon du disque central : zone d’apparition des points concentriques (distance au centre tirée uniformément dans ce rayon) et de disparition des points excentriques reverse. |
| `brownian_sigma` | float | `1.2` | Écart-type du déplacement aléatoire par frame (mode `brownian` uniquement). |
| `perspective_strength` | float | `2.5` | Intensité de l’effet profondeur : plus la valeur est grande, plus les points accélèrent loin du centre. |
| `size_depth_scale` | float | `0.35` | Augmentation visuelle de la taille des points avec la distance au centre. |
| `noise_mode` | string | `"brownian"` | Mode des points non cohérents : `"brownian"` ou `"reverse"`. |
| `warmup_loops` | entier | (global) | Surcharge optionnelle du warmup pour cette scène seule. |

### `noise_mode`

- **`brownian`** : marche aléatoire (bruit), wrap toroidal aux bords.
- **`reverse`** : naissance sur le bord de l’écran, mouvement radial vers le centre ; franchit le périmètre de `spawn_radius`, disparaît à une profondeur aléatoire dans cette aire, puis respawn au bord.

## Fichier de sortie (`responses_YYYYMMDD_HHMMSS.json`)

Le nom indiqué par `output_file` sert de base. Par exemple, avec `"output_file": "responses.json"`, la session écrit un fichier du type :

```text
responses_20260526_125430.json
```

Cela évite d’écraser les réponses des sessions précédentes.

```json
{
  "trials": [
    {
      "config": { "dot_size": 4, "dot_coherence": 0.8, "noise_mode": "brownian", ... },
      "response": "motion",
      "response_time_ms": 2340
    }
  ]
}
```

| Champ | Description |
|-------|-------------|
| `config` | Copie exacte de la config présentée. |
| `response` | `"noise"` ou `"motion"`. |
| `response_time_ms` | Délai entre le début de la scène (après warmup) et la touche pressée. |

## Exemple minimal

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
  "warmup_loops": 120
}
```
