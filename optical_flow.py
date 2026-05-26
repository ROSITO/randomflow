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

ALLOWED_EVENTS = (pygame.QUIT, pygame.KEYDOWN, pygame.VIDEORESIZE)


def load_config(config_path: str) -> dict:
    """Charge les paramètres depuis le fichier JSON (objet unique)."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier de config introuvable : {config_path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_config_list(config_path: str) -> tuple[list[dict], str, str, str, int, int]:
    """Charge la liste de configs + options (touches, fichier de sortie, loop, warmup)."""
    data = load_config(config_path)
    configs = data.get("configs", [])
    if not configs:
        raise ValueError("Le fichier doit contenir une liste 'configs' non vide.")
    key_noise = str(data.get("key_noise", "b")).lower()
    key_motion = str(data.get("key_motion", "m")).lower()
    output_file = str(data.get("output_file", "responses.json"))
    loop = max(1, int(data.get("loop", 1)))
    warmup_loops = max(0, int(data.get("warmup_loops", 60)))
    return configs, key_noise, key_motion, output_file, loop, warmup_loops


def parse_color(color) -> tuple:
    """Convertit dot_color (liste ou tuple RGB) en tuple (r, g, b)."""
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        return (int(color[0]), int(color[1]), int(color[2]))
    if isinstance(color, str) and color.startswith("#"):
        color = color.lstrip("#")
        return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))
    return (255, 255, 255)


def configure_event_queue() -> None:
    """Filtre les événements utiles pour éviter certains bugs Pygame/Windows."""
    pygame.event.set_blocked(None)
    pygame.event.set_allowed(ALLOWED_EVENTS)


def get_pygame_events() -> list:
    """Récupère les événements de façon robuste, notamment sous Windows."""
    try:
        return list(pygame.event.get(ALLOWED_EVENTS))
    except (pygame.error, SystemError):
        # Certaines combinaisons Windows/Pygame peuvent lever un SystemError
        # pendant la conversion d'événements inutiles. On vide la file et on
        # continue la frame suivante.
        try:
            pygame.event.clear()
        except pygame.error:
            pass
        return []


def key_matches(event: "pygame.event.Event", key_name: str | None) -> bool:
    """Compare un KEYDOWN Pygame à une touche configurable ('b', 'm', etc.)."""
    if not key_name:
        return False
    try:
        return event.key == pygame.key.key_code(key_name.lower())
    except ValueError:
        return getattr(event, "unicode", "").lower() == key_name.lower()


def random_point_in_circle(cx: float, cy: float, radius: float) -> tuple[float, float]:
    """Point aléatoire dans le disque, avec distance uniforme dans le rayon.

    On évite le tirage uniforme en surface (sqrt(random)) car il concentre
    visuellement les points dans l'anneau externe, comme s'ils apparaissaient
    sur le périmètre du spawn_radius.
    """
    angle = random.uniform(0, 2 * math.pi)
    r = random.uniform(0, radius)
    return (cx + r * math.cos(angle), cy + r * math.sin(angle))


def max_radial_distance(cx: float, cy: float, width: int, height: int) -> float:
    """Distance max du centre au bord de l'écran (approximation radiale symétrique)."""
    return min(cx, width - cx, cy, height - cy)


def random_point_on_screen_edge(width: int, height: int) -> tuple[float, float]:
    """Point aléatoire sur le périmètre de l'écran."""
    side = random.randint(0, 3)
    if side == 0:
        return random.uniform(0, width), 0.0
    if side == 1:
        return random.uniform(0, width), float(height)
    if side == 2:
        return 0.0, random.uniform(0, height)
    return float(width), random.uniform(0, height)


class Dot:
    """Un point : cohérent (centre → bord), brownien, ou inverse (bord → centre)."""

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
        noise_mode: str,
    ) -> bool:
        """Met à jour la position. Retourne True si le point est encore visible."""
        if not self.moving:
            if noise_mode == "reverse":
                self.x += self.vx
                self.y += self.vy
                dx = self.x - center_x
                dy = self.y - center_y
                # Disparition aléatoire dans le disque spawn_radius, puis respawn au bord
                if dx * dx + dy * dy <= spawn_radius * spawn_radius:
                    self.x, self.y = random_point_in_circle(center_x, center_y, spawn_radius)
                    self._respawn_on_edge(width, height, center_x, center_y)
                return True
            # Mouvement brownien (bruit) pour les points non-cohérents
            self.x += random.gauss(0, brownian_sigma)
            self.y += random.gauss(0, brownian_sigma)
            if width > 0:
                self.x = self.x % width
            if height > 0:
                self.y = self.y % height
            return True
        self.x += self.vx
        self.y += self.vy
        # Concentrique : traverse tout l'écran, respawn dans spawn_radius seulement au bord
        margin = 50
        if not (-margin <= self.x <= width + margin and -margin <= self.y <= height + margin):
            self._respawn_coherent(center_x, center_y, spawn_radius)
        return True

    def _respawn_coherent(self, center_x: float, center_y: float, spawn_radius: float) -> None:
        """Respawn cohérent : position aléatoire dans le disque spawn_radius,
        vitesse radiale vers l'extérieur (comme si le point partait du centre).
        """
        self.x, self.y = random_point_in_circle(center_x, center_y, spawn_radius)
        dx = self.x - center_x
        dy = self.y - center_y
        if dx * dx + dy * dy < 1e-6:
            self.angle = random.uniform(0, 2 * math.pi)
        else:
            self.angle = math.atan2(dy, dx)
        self.vx = self.speed * math.cos(self.angle)
        self.vy = self.speed * math.sin(self.angle)

    def _respawn_on_edge(self, width: int, height: int, center_x: float, center_y: float) -> None:
        """Replace le point excentrique sur le bord de l'écran, vitesse vers le centre."""
        self.x, self.y = random_point_on_screen_edge(width, height)
        self.angle = math.atan2(center_y - self.y, center_x - self.x)
        self.vx = self.speed * math.cos(self.angle)
        self.vy = self.speed * math.sin(self.angle)

    def draw(self, surface: "pygame.Surface", color: tuple, size: int) -> None:
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), size)


def create_dots(
    width: int,
    height: int,
    dot_number: int,
    dot_coherence: float,
    dot_speed: float,
    spawn_radius: float,
    noise_mode: str = "brownian",
) -> list[Dot]:
    """Crée dot_number points déjà déployés sur toute la surface.
    - dot_coherence : proportion mobile (centre → bord).
    - noise_mode == "brownian" : non-mobiles ont un mouvement brownien.
    - noise_mode == "reverse"  : non-mobiles vont en ligne droite vers le centre.
    """
    cx = width / 2
    cy = height / 2
    n_moving = max(0, min(dot_number, int(round(dot_number * dot_coherence))))
    dots = []

    for i in range(dot_number):
        x = random.uniform(0, width)
        y = random.uniform(0, height)
        moving = i < n_moving
        if moving:
            angle = math.atan2(y - cy, x - cx)
            dot = Dot(x, y, moving=True, angle=angle, speed=dot_speed)
        elif noise_mode == "reverse":
            ex, ey = random_point_on_screen_edge(width, height)
            angle = math.atan2(cy - ey, cx - ex)
            dot = Dot(ex, ey, moving=False, angle=angle, speed=dot_speed)
            dot.vx = dot_speed * math.cos(angle)
            dot.vy = dot_speed * math.sin(angle)
        else:
            dot = Dot(x, y, moving=False, angle=0.0, speed=dot_speed)
        dots.append(dot)

    random.shuffle(dots)
    return dots


def _warmup_dots(
    dots: list[Dot],
    width: int,
    height: int,
    spawn_radius: float,
    brownian_sigma: float,
    noise_mode: str,
    n_loops: int,
) -> None:
    """Simule n_loops mises à jour sans affichage pour stabiliser la distribution des points."""
    if n_loops <= 0:
        return
    cx, cy = width / 2, height / 2
    for _ in range(n_loops):
        for dot in dots:
            dot.update(width, height, cx, cy, spawn_radius, brownian_sigma, noise_mode)
        try:
            pygame.event.pump()
        except pygame.error:
            return


def parse_single_config(config: dict, default_warmup_loops: int = 60) -> dict:
    """Extrait et normalise les paramètres d'une config pour l'affichage."""
    noise_mode = str(config.get("noise_mode", "brownian")).lower()
    if noise_mode not in ("brownian", "reverse"):
        noise_mode = "brownian"
    return {
        "dot_size": int(config.get("dot_size", 4)),
        "dot_speed": float(config.get("dot_speed", 2.0)),
        "dot_color": parse_color(config.get("dot_color", [255, 255, 255])),
        "dot_number": int(config.get("dot_number", 200)),
        "dot_coherence": max(0.0, min(1.0, float(config.get("dot_coherence", 0.8)))),
        "spawn_radius": max(1.0, float(config.get("spawn_radius", 80))),
        "brownian_sigma": max(0.0, float(config.get("brownian_sigma", 1.2))),
        "noise_mode": noise_mode,
        "warmup_loops": max(0, int(config.get("warmup_loops", default_warmup_loops))),
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
    configure_event_queue()
    default_warmup = max(0, int(config.get("warmup_loops", 60)))
    params = parse_single_config(config, default_warmup_loops=default_warmup)
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
    noise_mode = params["noise_mode"]
    warmup_loops = params["warmup_loops"]
    dots = create_dots(width, height, dot_number, dot_coherence, dot_speed, spawn_radius, noise_mode)
    _warmup_dots(dots, width, height, spawn_radius, brownian_sigma, noise_mode, warmup_loops)
    config_start_time = pygame.time.get_ticks()
    bg_color = (20, 20, 25)
    running = True
    clock = pygame.time.Clock()
    while running:
        for event in get_pygame_events():
            if event.type == pygame.QUIT:
                return False, width, height
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False, width, height
                if key_matches(event, key_noise) and results is not None and config is not None:
                    response_time_ms = pygame.time.get_ticks() - config_start_time
                    results.append({
                        "config": config,
                        "response": "noise",
                        "response_time_ms": response_time_ms,
                    })
                    return True, width, height  # passer à la config suivante
                if key_matches(event, key_motion) and results is not None and config is not None:
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
                configure_event_queue()
                dots = create_dots(width, height, dot_number, dot_coherence, dot_speed, spawn_radius, noise_mode)
                _warmup_dots(dots, width, height, spawn_radius, brownian_sigma, noise_mode, warmup_loops)

        screen.fill(bg_color)
        cx, cy = width / 2, height / 2
        for dot in dots:
            dot.update(width, height, cx, cy, spawn_radius, brownian_sigma, noise_mode)
            dot.draw(screen, dot_color, dot_size)
        pygame.display.flip()
        clock.tick(60)
    return False, width, height


def run_session(config_path: str = "config.json") -> None:
    """Joue la liste de configs dans un ordre aléatoire. Touche B = bruit, M = mouvement.
    Enregistre les réponses dans le fichier JSON de sortie. Transition immédiate à la config suivante.
    """
    configs, key_noise, key_motion, output_file, loop, default_warmup = load_config_list(config_path)
    configs = list(configs) * loop  # répéter la liste "loop" fois
    random.shuffle(configs)

    pygame.init()
    info = pygame.display.Info()
    width = info.current_w // 2
    height = info.current_h // 2
    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    configure_event_queue()
    pygame.display.set_caption("Flux optique — B=bruit, M=mouvement, Échap=quitter")

    results: list[dict] = []
    index = 0
    running = True

    while running and index < len(configs):
        config = configs[index]
        params = parse_single_config(config, default_warmup_loops=default_warmup)
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
