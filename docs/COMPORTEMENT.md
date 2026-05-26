# Comportement des points

## Vue d’ensemble

L’écran affiche `dot_number` points blancs sur fond sombre. Une fraction `dot_coherence` suit un **flux concentrique** (centre → bords). Les autres constituent le **bruit** selon `noise_mode`.

```
                    ┌─────────────────────────┐
                    │      bord écran         │
                    │   ← reverse (excentrique)│
                    │         ╭───╮           │
                    │         │ S │ spawn     │
                    │         ╰───╯           │
                    │    concentrique →       │
                    └─────────────────────────┘
                              S = spawn_radius
```

## Points concentriques (cohérents)

- **Proportion** : `dot_coherence` × `dot_number` (arrondi).
- **Mouvement** : direction radiale **du centre vers l’extérieur** (comme s’ils partaient du centre), avec une vitesse qui augmente avec la distance au centre pour créer l’effet profondeur / “vitesse lumière”.
- **Position initiale** : répartis uniformément sur tout l’écran (déjà « déployés » à la frame 0).
- **Respawn** : lorsqu’un point sort de l’écran, il réapparaît à une position aléatoire **dans le disque** `spawn_radius`, avec une distance au centre tirée uniformément entre 0 et `spawn_radius` (pour éviter une concentration visible sur le périmètre), puis une nouvelle direction radiale vers l’extérieur.
- **Trajet** : du disque central jusqu’au **bord de l’écran**, sans être recyclé avant.
- **Profondeur** : `perspective_strength` contrôle l’accélération radiale, et `size_depth_scale` augmente légèrement la taille des points en périphérie.

## Points excentriques — mode `brownian`

- **Mouvement** : déplacement gaussien indépendant en x et y (`brownian_sigma` par frame).
- **Bords** : wrap toroidal (réapparition de l’autre côté).
- **Indépendance** : ne sont pas liés au disque `spawn_radius`.

## Points excentriques — mode `reverse`

- **Naissance** : sur un **bord** aléatoire de l’écran.
- **Mouvement** : ligne droite vers le centre, avec la même perspective inversée : rapide près du bord, plus lent près du centre.
- **Disparition** : après avoir franchi le périmètre de `spawn_radius`, chaque point disparaît à une profondeur aléatoire **dans** ce disque, puis respawne sur un bord avec une nouvelle trajectoire vers le centre.

## Warmup

Avant l’affichage de chaque scène, la simulation exécute `warmup_loops` mises à jour **sans dessiner**. Cela stabilise la distribution des points et évite l’effet de « démarrage à froid ».

## Session expérimentale

1. Les configs sont mélangées aléatoirement (`loop` répète la liste entière).
2. L’utilisateur observe le flux et appuie sur **bruit** ou **mouvement**.
3. Passage **immédiat** à la config suivante (pas de coupure du flux).
4. À la fin (ou sur Échap), écriture de `responses.json`.
