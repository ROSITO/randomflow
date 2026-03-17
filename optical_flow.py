#!/usr/bin/env python3
"""
Flux optique de points : lecture des paramètres depuis un fichier JSON,
affichage de dot_number points dont une proportion dot_coherence se déplace
du centre vers les bords de l'écran.
"""

import json
import math
import random
import sys
from pathlib import Path

try:
    import pygame
except ImportError:
    print("Installez pygame : pip install pygame")
    sys.exit(1)


def load_config(config_path: str) -> dict:
    """Charge les paramètres depuis le fichier JSON (objet unique)."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier de config introuvable : {config_path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config_list(config_path: str) -> tuple[list[dict], str, str, str, int]:
    """Charge la liste de configs + options (touches, fichier de sortie, loop)."""
    data = load_config(config_path)
    configs = data.get("configs", [])
    if not configs:
        raise ValueError("Le fichier doit contenir une liste 'configs' non vide.")
    key_noise = str(data.get("key_noise", "b")).lower()
    key_motion = str(data.get("key_motion", "m")).lower()
    output_file = str(data.get("output_file", "responses.json"))
    loop = max(1, int(data.get("loop", 1)))
    return configs, key_noise, key_motion, output_file, loop


def parse_color(color) -> tuple:
    """Convertit dot_color (liste ou tuple RGB) en tuple (r, g, b)."""
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        return (int(color[0]), int(color[1]), int(color[2]))
    if isinstance(color, str) and color.startswith("#"):
        color = color.lstrip("#")
        return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
    return (255, 255, 255)


def random_point_in_circle(cx: float, cy: float, radius: float) -> tuple[float, float]:
    """Point aléatoire uniforme dans le disque (cx, cy) de rayon radius."""
    angle = random.uniform(0, 2 * math.pi)
    r = math.sqrt(random.uniform(0, 1)) * radius  # sqrt pour distribution uniforme
    return (cx + r * math.cos(angle), cy + r * math.sin(angle))


class Dot:
    """Un point : soit fixe, soit en mouvement du centre vers le bord."""

    __slots__ = ("x", "y", "vx", "vy", "moving", "angle", "speed")

    def __init__(self, x: float, y: float, moving: bool, angle: float, speed: float):
        self.x = x
        self.y = y
        self.moving = moving
        self.angle = angle
        self.speed = speed
        if moving:
            self.vx = speed * math.cos(angle)
            self.vy = speed * math.sin(angle)
        else:
            self.vx = 0.0
            self.vy = 0.0

    def update(
        self,
        width: int,
        height: int,
        center_x: float,
        center_y: float,
        spawn_radius: float,
        brownian_sigma: float,
    ) -> bool:
        """Met à jour la position. Retourne True si le point est encore visible."""
        if not self.moving:
            # Mouvement brownien (bruit) pour les points immobiles
            self.x += random.gauss(0, brownian_sigma)
            self.y += random.gauss(0, brownian_sigma)
            # Toroidal wrap pour garder les points à l'écran
            if width > 0:
                self.x = self.x % width
            if height > 0:
                self.y = self.y % height
            return True
        self.x += self.vx
        self.y += self.vy
        margin = 50
        if -margin <= self.x <= width + margin and -margin <= self.y <= height + margin:
            return True
        # Respawn dans le cercle, mais la vitesse reste radiale depuis le centre (comme s'il partait du centre)
        self.x, self.y = random_point_in_circle(center_x, center_y, spawn_radius)
        self.angle = math.atan2(self.y - center_y, self.x - center_x)
        self.vx = self.speed * math.cos(self.angle)
        self.vy = self.speed * math.sin(self.angle)
        return True

    def draw(self, surface: "pygame.Surface", color: tuple, size: int) -> None:
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), size)


def create_dots(
    width: int,
    height: int,
    dot_number: int,
    dot_coherence: float,
    dot_speed: float,
    spawn_radius: float,
) -> list[Dot]:
    """Crée dot_number points déjà déployés sur toute la surface.
    Seule la proportion dot_coherence (0–1) est en mouvement (vitesse radiale centre → bords).
    Respawn des mobiles dans le cercle de rayon spawn_radius.
    """
    cx = width / 2
    cy = height / 2
    n_moving = max(0, min(dot_number, int(round(dot_number * dot_coherence))))
    dots = []

    # Tous les points : répartition uniforme sur tout l'écran dès la frame 0
    for i in range(dot_number):
        x = random.uniform(0, width)
        y = random.uniform(0, height)
        moving = i < n_moving
        # Vitesse radiale depuis le centre (comme s'ils partaient du centre)
        angle = math.atan2(y - cy, x - cx) if moving else 0.0
        dots.append(Dot(x, y, moving=moving, angle=angle, speed=dot_speed))

    random.shuffle(dots)
    return dots


def parse_single_config(config: dict) -> dict:
    """Extrait et normalise les paramètres d'une config pour l'affichage."""
    return {
        "dot_size": int(config.get("dot_size", 4)),
        "dot_speed": float(config.get("dot_speed", 2.0)),
        "dot_color": parse_color(config.get("dot_color", [255, 255, 255])),
        "dot_number": int(config.get("dot_number", 200)),
        "dot_coherence": max(0.0, min(1.0, float(config.get("dot_coherence", 0.8)))),
        "spawn_radius": max(1.0, float(config.get("spawn_radius", 80))),
        "brownian_sigma": max(0.0, float(config.get("brownian_sigma", 1.2))),
    }


def run_optical_flow(config_path: str = "config.json") -> None:
    """Lance la fenêtre. Si config contient 'configs', lance la session (touches B/M)."""
    config = load_config(config_path)
    if "configs" in config and config["configs"]:
        run_session(config_path)
        return
    # Ancien format: un seul objet de config
    pygame.init()
    info = pygame.display.Info()
    width, height = info.current_w // 2, info.current_h // 2
    pygame.display.set_mode((width, height), pygame.RESIZABLE)
    params = parse_single_config(config)
    _run_loop(
        width=width,
        height=height,
        params=params,
        config=None,
        key_noise=None,
        key_motion=None,
        results=None,
        output_file=None,
    )
    pygame.quit()


def _run_loop(
    width: int,
    height: int,
    params: dict,
    config: dict | None,
    key_noise: str | None,
    key_motion: str | None,
    results: list | None,
    output_file: str | None,
) -> tuple[bool, int, int]:
    """Boucle d'affichage pour une config. Retourne (running, width, height)."""
    screen = pygame.display.get_surface()
    dot_size = params["dot_size"]
    dot_color = params["dot_color"]
    dot_number = params["dot_number"]
    dot_coherence = params["dot_coherence"]
    dot_speed = params["dot_speed"]
    spawn_radius = params["spawn_radius"]
    brownian_sigma = params["brownian_sigma"]
    dots = create_dots(width, height, dot_number, dot_coherence, dot_speed, spawn_radius)
    config_start_time = pygame.time.get_ticks()
    bg_color = (20, 20, 25)
    running = True
    clock = pygame.time.Clock()
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False, width, height
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False, width, height
                if key_noise and event.unicode.lower() == key_noise and results is not None and config is not None:
                    response_time_ms = pygame.time.get_ticks() - config_start_time
                    results.append({
                        "config": config,
                        "response": "noise",
                        "response_time_ms": response_time_ms,
                    })
                    return True, width, height  # passer à la config suivante
                if key_motion and event.unicode.lower() == key_motion and results is not None and config is not None:
                    response_time_ms = pygame.time.get_ticks() - config_start_time
                    results.append({
                        "config": config,
                        "response": "motion",
                        "response_time_ms": response_time_ms,
                    })
                    return True, width, height
            if event.type == pygame.VIDEORESIZE:
                width, height = event.w, event.h
                screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                dots = create_dots(width, height, dot_number, dot_coherence, dot_speed, spawn_radius)

        screen.fill(bg_color)
        cx, cy = width / 2, height / 2
        for dot in dots:
            dot.update(width, height, cx, cy, spawn_radius, brownian_sigma)
            dot.draw(screen, dot_color, dot_size)
        pygame.display.flip()
        clock.tick(60)
    return False, width, height


def run_session(config_path: str = "config.json") -> None:
    """Joue la liste de configs dans un ordre aléatoire. Touche B = bruit, M = mouvement.
    Enregistre les réponses dans le fichier JSON de sortie. Transition immédiate à la config suivante.
    """
    configs, key_noise, key_motion, output_file, loop = load_config_list(config_path)
    configs = list(configs) * loop  # répéter la liste "loop" fois
    random.shuffle(configs)

    pygame.init()
    info = pygame.display.Info()
    width = info.current_w // 2
    height = info.current_h // 2
    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    pygame.display.set_caption("Flux optique — B=bruit, M=mouvement, Échap=quitter")

    results: list[dict] = []
    index = 0
    running = True

    while running and index < len(configs):
        config = configs[index]
        params = parse_single_config(config)
        running, width, height = _run_loop(
            width=width,
            height=height,
            params=params,
            config=config,
            key_noise=key_noise,
            key_motion=key_motion,
            results=results,
            output_file=output_file,
        )
        if running:
            index += 1

    # Écrire le fichier de sortie
    out_path = Path(config_path).parent / output_file
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"trials": results}, f, indent=2, ensure_ascii=False)
    print(f"Réponses enregistrées dans {out_path} ({len(results)} essai(s)).")
    pygame.quit()


def main() -> None:
    """Point d'entrée CLI (uv run optical-flow [config.json])."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config.json"
    run_optical_flow(config_path)


if __name__ == "__main__":
    main()
