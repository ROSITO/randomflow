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
from datetime import datetime
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

def load_config_list(config_path: str) -> tuple[list[dict], str, str, str, int, int, dict, int]:
    """Charge la liste de configs + options de session."""
    data = load_config(config_path)
    configs = data.get("configs", [])
    if not configs:
        raise ValueError("Le fichier doit contenir une liste 'configs' non vide.")
    key_backward = str(data.get("key_backward", "down")).lower()
    key_forward = str(data.get("key_forward", "up")).lower()
    output_file = str(data.get("output_file", "responses.json"))
    loop = max(1, int(data.get("loop", 1)))
    warmup_loops = max(0, int(data.get("warmup_loops", 60)))
    fixation_min_ms = max(0, int(data.get("fixation_min_ms", 500)))
    fixation_timeout_ms = max(fixation_min_ms, int(data.get("fixation_timeout_ms", 5000)))
    fixation = {
        "min_ms": fixation_min_ms,
        "timeout_ms": fixation_timeout_ms,
        "size": max(1, int(data.get("fixation_size", 5))),
        "color": parse_color(data.get("fixation_color", [255, 255, 255])),
    }
    block_repeats = max(1, int(data.get("block_repeats", 1)))
    fullscreen = bool(data.get("fullscreen", True))
    return configs, key_backward, key_forward, output_file, loop, warmup_loops, fixation, block_repeats, fullscreen

def create_display(fullscreen: bool = True) -> tuple:
    """Crée la fenêtre et retourne (surface, largeur, hauteur) en pixels utilisables."""
    pygame.init()
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        info = pygame.display.Info()
        screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.RESIZABLE)
    width, height = screen.get_size()
    return screen, width, height

def set_display_size(width: int, height: int, fullscreen: bool) -> tuple:
    """Redimensionne la fenêtre et retourne la taille réelle de la surface."""
    if fullscreen:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    else:
        screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    configure_event_queue()
    return screen, *screen.get_size()

def timestamped_output_path(config_path: str, output_file: str) -> Path:
    """Construit un chemin horodaté pour éviter d'écraser les réponses précédentes."""
    base_path = Path(config_path).parent / output_file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    suffix = base_path.suffix or ".json"
    return base_path.with_name(f"{base_path.stem}_{timestamp}{suffix}")

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
        try:
            pygame.event.clear()
        except pygame.error:
            pass
        return []

def key_matches(event: "pygame.event.Event", key_name: str | None) -> bool:
    """Compare un KEYDOWN Pygame à une touche configurable ('up', 'down', etc.)."""
    if not key_name:
        return False
    try:
        # Gestion des touches fléchées
        if key_name == "up":
            return event.key == pygame.K_UP
        elif key_name == "down":
            return event.key == pygame.K_DOWN
        return event.key == pygame.key.key_code(key_name.lower())
    except ValueError:
        return getattr(event, "unicode", "").lower() == key_name.lower()

def random_point_in_circle(cx: float, cy: float, radius: float) -> tuple[float, float]:
    """Point aléatoire dans le disque, avec distance uniforme dans le rayon."""
    angle = random.uniform(0, 2 * math.pi)
    r = random.uniform(0, radius)
    return (cx + r * math.cos(angle), cy + r * math.sin(angle))

def max_radial_distance(cx: float, cy: float, width: int, height: int) -> float:
    """Distance max du centre au bord de l'écran (approximation radiale symétrique)."""
    return min(cx, width - cx, cy, height - cy)

def max_corner_distance(cx: float, cy: float, width: int, height: int) -> float:
    """Distance du centre au coin le plus éloigné, pour normaliser l'effet de profondeur."""
    return max(
        math.hypot(cx, cy),
        math.hypot(width - cx, cy),
        math.hypot(cx, height - cy),
        math.hypot(width - cx, height - cy),
    )

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

    __slots__ = ("x", "y", "vx", "vy", "moving", "angle", "speed", "reverse_vanish_radius")

    def __init__(self, x: float, y: float, moving: bool, angle: float, speed: float):
        self.x = x
        self.y = y
        self.moving = moving
        self.angle = angle
        self.speed = speed
        self.reverse_vanish_radius = 0.0
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
        perspective_strength: float,
    ) -> bool:
        """Met à jour la position. Retourne True si le point est encore visible."""
        if not self.moving:
            if noise_mode == "reverse":
                if self.reverse_vanish_radius <= 0 or self.reverse_vanish_radius > spawn_radius:
                    self.reverse_vanish_radius = random.uniform(0, spawn_radius)
                old_dx = self.x - center_x
                old_dy = self.y - center_y
                old_dist_sq = old_dx * old_dx + old_dy * old_dy
                self._set_radial_velocity(
                    center_x, center_y, width, height, perspective_strength, toward_center=True
                )
                self.x += self.vx
                self.y += self.vy
                dx = self.x - center_x
                dy = self.y - center_y
                dist_sq = dx * dx + dy * dy
                vanish_sq = self.reverse_vanish_radius * self.reverse_vanish_radius
                crossed_center = old_dist_sq <= spawn_radius * spawn_radius and dist_sq > old_dist_sq
                if dist_sq <= vanish_sq or crossed_center:
                    self._respawn_on_edge(width, height, center_x, center_y, spawn_radius)
                return True
            self.x += random.gauss(0, brownian_sigma)
            self.y += random.gauss(0, brownian_sigma)
            if width > 0:
                self.x = self.x % width
            if height > 0:
                self.y = self.y % height
            return True
        self._set_radial_velocity(
            center_x, center_y, width, height, perspective_strength, toward_center=False
        )
        self.x += self.vx
        self.y += self.vy
        margin = 50
        if not (-margin <= self.x <= width + margin and -margin <= self.y <= height + margin):
            self._respawn_coherent(center_x, center_y, spawn_radius)
        return True

    def _respawn_coherent(self, center_x: float, center_y: float, spawn_radius: float) -> None:
        """Respawn cohérent : position aléatoire dans le disque spawn_radius."""
        self.x, self.y = random_point_in_circle(center_x, center_y, spawn_radius)
        dx = self.x - center_x
        dy = self.y - center_y
        if dx * dx + dy * dy < 1e-6:
            self.angle = random.uniform(0, 2 * math.pi)
        else:
            self.angle = math.atan2(dy, dx)
        self.vx = self.speed * math.cos(self.angle)
        self.vy = self.speed * math.sin(self.angle)

    def _set_radial_velocity(
        self,
        center_x: float,
        center_y: float,
        width: int,
        height: int,
        perspective_strength: float,
        toward_center: bool,
    ) -> None:
        """Met à jour la vitesse radiale : plus loin du centre = plus rapide."""
        dx = self.x - center_x
        dy = self.y - center_y
        if dx * dx + dy * dy < 1e-6:
            angle = random.uniform(0, 2 * math.pi)
        elif toward_center:
            angle = math.atan2(-dy, -dx)
        else:
            angle = math.atan2(dy, dx)

        max_dist = max(max_corner_distance(center_x, center_y, width, height), 1.0)
        normalized_distance = min(1.0, math.hypot(dx, dy) / max_dist)
        speed_multiplier = 1.0 + perspective_strength * normalized_distance * normalized_distance
        radial_speed = self.speed * speed_multiplier
        self.angle = angle
        self.vx = radial_speed * math.cos(angle)
        self.vy = radial_speed * math.sin(angle)

    def _respawn_on_edge(
        self,
        width: int,
        height: int,
        center_x: float,
        center_y: float,
        spawn_radius: float,
    ) -> None:
        """Replace le point excentrique sur le bord de l'écran, vitesse vers le centre."""
        self.x, self.y = random_point_on_screen_edge(width, height)
        self.angle = math.atan2(center_y - self.y, center_x - self.x)
        self.vx = self.speed * math.cos(self.angle)
        self.vy = self.speed * math.sin(self.angle)
        self.reverse_vanish_radius = random.uniform(0, spawn_radius)

    def draw(
        self,
        surface: "pygame.Surface",
        color: tuple,
        size: int,
        center_x: float,
        center_y: float,
        width: int,
        height: int,
        size_depth_scale: float,
    ) -> None:
        max_dist = max(max_corner_distance(center_x, center_y, width, height), 1.0)
        normalized_distance = min(1.0, math.hypot(self.x - center_x, self.y - center_y) / max_dist)
        draw_size = max(1, int(round(size * (1.0 + size_depth_scale * normalized_distance))))
        pygame.draw.circle(surface, color, (int(self.x), int(self.y)), draw_size)

def create_dots(
    width: int,
    height: int,
    dot_number: int,
    dot_coherence: float,
    dot_speed: float,
    spawn_radius: float,
    noise_mode: str = "brownian",
) -> list[Dot]:
    """Crée dot_number points déjà déployés sur toute la surface."""
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
            dot = Dot(0.0, 0.0, moving=False, angle=0.0, speed=dot_speed)
            dot._respawn_on_edge(width, height, cx, cy, spawn_radius)
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
    perspective_strength: float,
    n_loops: int,
) -> None:
    """Simule n_loops mises à jour sans affichage pour stabiliser la distribution des points."""
    if n_loops <= 0:
        return
    cx, cy = width / 2, height / 2
    for _ in range(n_loops):
        for dot in dots:
            dot.update(
                width, height, cx, cy, spawn_radius, brownian_sigma, noise_mode, perspective_strength
            )
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
        "perspective_strength": max(0.0, float(config.get("perspective_strength", 4.0))),
        "size_depth_scale": max(0.0, float(config.get("size_depth_scale", 1.2))),
        "warmup_loops": max(0, int(config.get("warmup_loops", default_warmup_loops))),
    }

def run_optical_flow(config_path: str = "config.json") -> None:
    """Lance la fenêtre. Si config contient 'configs', lance la session (touches fléchées)."""
    config = load_config(config_path)
    if "configs" in config and config["configs"]:
        run_session(config_path)
        return
    fullscreen = bool(config.get("fullscreen", True))
    screen, width, height = create_display(fullscreen=fullscreen)
    configure_event_queue()
    default_warmup = max(0, int(config.get("warmup_loops", 60)))
    params = parse_single_config(config, default_warmup_loops=default_warmup)
    _run_loop(
        width=width,
        height=height,
        params=params,
        config=None,
        key_backward=None,
        key_forward=None,
        results=None,
        output_file=None,
        fullscreen=fullscreen,
    )
    pygame.quit()

def _run_loop(
    width: int,
    height: int,
    params: dict,
    config: dict | None,
    key_backward: str | None,
    key_forward: str | None,
    results: list | None,
    output_file: str | None,
    fullscreen: bool = True,
) -> tuple[bool, int, int]:
    """Boucle d'affichage pour une config. Retourne (running, width, height)."""
    screen = pygame.display.get_surface()
    if screen is not None:
        width, height = screen.get_size()
    dot_size = params["dot_size"]
    dot_color = params["dot_color"]
    dot_number = params["dot_number"]
    dot_coherence = params["dot_coherence"]
    dot_speed = params["dot_speed"]
    spawn_radius = params["spawn_radius"]
    brownian_sigma = params["brownian_sigma"]
    noise_mode = params["noise_mode"]
    perspective_strength = params["perspective_strength"]
    size_depth_scale = params["size_depth_scale"]
    warmup_loops = params["warmup_loops"]
    dots = create_dots(width, height, dot_number, dot_coherence, dot_speed, spawn_radius, noise_mode)
    _warmup_dots(
        dots, width, height, spawn_radius, brownian_sigma, noise_mode, perspective_strength, warmup_loops
    )
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
                if key_matches(event, key_backward) and results is not None and config is not None:
                    response_time_ms = pygame.time.get_ticks() - config_start_time
                    results.append({
                        "config": config,
                        "response": "backward",
                        "response_time_ms": response_time_ms,
                    })
                    return True, width, height
                if key_matches(event, key_forward) and results is not None and config is not None:
                    response_time_ms = pygame.time.get_ticks() - config_start_time
                    results.append({
                        "config": config,
                        "response": "forward",
                        "response_time_ms": response_time_ms,
                    })
                    return True, width, height
            if event.type == pygame.VIDEORESIZE and not fullscreen:
                screen, width, height = set_display_size(event.w, event.h, fullscreen=False)
                dots = create_dots(width, height, dot_number, dot_coherence, dot_speed, spawn_radius, noise_mode)
                _warmup_dots(
                    dots, width, height, spawn_radius, brownian_sigma, noise_mode,
                    perspective_strength, warmup_loops,
                )

        screen.fill(bg_color)
        cx, cy = width / 2, height / 2
        for dot in dots:
            dot.update(width, height, cx, cy, spawn_radius, brownian_sigma, noise_mode, perspective_strength)
            dot.draw(screen, dot_color, dot_size, cx, cy, width, height, size_depth_scale)
        pygame.display.flip()
        clock.tick(60)
    return False, width, height

def _run_fixation_screen(
    width: int,
    height: int,
    fixation_min_ms: int,
    fixation_timeout_ms: int | None,
    fixation_size: int,
    fixation_color: tuple,
    fullscreen: bool = True,
) -> tuple[bool, int, int, int]:
    """Affiche un point de fixation entre deux stimuli."""
    screen = pygame.display.get_surface()
    if screen is not None:
        width, height = screen.get_size()
    clock = pygame.time.Clock()
    start_time = pygame.time.get_ticks()

    while True:
        elapsed_ms = pygame.time.get_ticks() - start_time
        if fixation_timeout_ms is not None and elapsed_ms >= fixation_timeout_ms:
            return True, width, height, elapsed_ms

        for event in get_pygame_events():
            if event.type == pygame.QUIT:
                return False, width, height, elapsed_ms
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False, width, height, elapsed_ms
                if event.key == pygame.K_SPACE and elapsed_ms >= fixation_min_ms:
                    return True, width, height, elapsed_ms
            if event.type == pygame.VIDEORESIZE and not fullscreen:
                screen, width, height = set_display_size(event.w, event.h, fullscreen=False)

        screen.fill((0, 0, 0))
        pygame.draw.circle(screen, fixation_color, (width // 2, height // 2), fixation_size)
        pygame.display.flip()
        clock.tick(60)

def _run_instruction_screen(
    width: int,
    height: int,
    instruction_text: str,
    bg_color: tuple = (0, 0, 0),
    text_color: tuple = (255, 255, 255),
    font_size: int = 24,
    fullscreen: bool = True,
) -> tuple[bool, int, int]:
    """Affiche un écran avec des instructions."""
    screen = pygame.display.get_surface()
    if screen is not None:
        width, height = screen.get_size()
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, font_size)
    lines = instruction_text.split('\n')

    running = True
    while running:
        for event in get_pygame_events():
            if event.type == pygame.QUIT:
                return False, width, height
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False, width, height
                if event.key == pygame.K_SPACE:
                    return True, width, height
            if event.type == pygame.VIDEORESIZE and not fullscreen:
                screen, width, height = set_display_size(event.w, event.h, fullscreen=False)

        screen.fill(bg_color)
        y_offset = height // 2 - (len(lines) * font_size) // 2
        for line in lines:
            text_surface = font.render(line, True, text_color)
            text_rect = text_surface.get_rect(center=(width // 2, y_offset))
            screen.blit(text_surface, text_rect)
            y_offset += font_size + 10

        pygame.draw.circle(screen, text_color, (width // 2, height // 2), 5)  # Point de fixation
        pygame.display.flip()
        clock.tick(60)

    return True, width, height

def run_session(config_path: str = "config.json") -> None:
    """Joue la liste de configs dans un ordre aléatoire."""
    configs, key_backward, key_forward, output_file, loop, default_warmup, fixation, block_repeats, fullscreen = load_config_list(config_path)
    configs = list(configs) * loop

    screen, width, height = create_display(fullscreen=fullscreen)
    configure_event_queue()
    pygame.display.set_caption("Flux optique — Flèche bas=arrière, Flèche haut=avant, Échap=quitter")

    results: list[dict] = []
    running = True

    # Écran d'instructions initial
    instruction_text = (
        "Fixer au centre.\n"
        "Entre deux essais, vous pouvez passer à la suite en appuyant sur la barre d'espace.\n"
        "Répondez dans quelle est la direction du mouvement de soi perçue (pas le mouvement des points)\n"
        "en appuyant sur la flèche HAUT pour l'avant, la flèche BAS pour l'arrière."
    )
    running, width, height = _run_instruction_screen(
        width=width,
        height=height,
        instruction_text=instruction_text,
        bg_color=(0, 0, 0),
        text_color=(255, 255, 255),
        font_size=24,
        fullscreen=fullscreen,
    )

    # Répéter le bloc entier "block_repeats" fois
    for block in range(block_repeats):
        if not running:
            break

        # Mélanger les configs pour chaque bloc
        random.shuffle(configs)
        index = 0

        # Fixation initiale pour chaque bloc (sauf le premier, déjà géré après l'écran d'instructions)
        if block > 0:
            running, width, height, _ = _run_fixation_screen(
                width=width,
                height=height,
                fixation_min_ms=0,
                fixation_timeout_ms=None,
                fixation_size=fixation["size"],
                fixation_color=fixation["color"],
                fullscreen=fullscreen,
            )

        # Exécuter toutes les configurations du bloc
        while running and index < len(configs):
            config = configs[index]
            params = parse_single_config(config, default_warmup_loops=default_warmup)
            running, width, height = _run_loop(
                width=width,
                height=height,
                params=params,
                config=config,
                key_backward=key_backward,
                key_forward=key_forward,
                results=results,
                output_file=output_file,
                fullscreen=fullscreen,
            )
            if running:
                index += 1
                if index < len(configs):
                    running, width, height, fixation_duration_ms = _run_fixation_screen(
                        width=width,
                        height=height,
                        fixation_min_ms=fixation["min_ms"],
                        fixation_timeout_ms=fixation["timeout_ms"],
                        fixation_size=fixation["size"],
                        fixation_color=fixation["color"],
                        fullscreen=fullscreen,
                    )
                    if results:
                        results[-1]["fixation_after_ms"] = fixation_duration_ms

        # Écran de pause à la fin du bloc
        if running and block < block_repeats - 1:
            pause_text = "Ceci est une pause, prenez un KitKat.\nPassez à la suite en appuyant sur espace."
            running, width, height = _run_instruction_screen(
                width=width,
                height=height,
                instruction_text=pause_text,
                bg_color=(0, 0, 0),
                text_color=(255, 255, 255),
                font_size=24,
                fullscreen=fullscreen,
            )

    # Écrire le fichier de sortie
    out_path = timestamped_output_path(config_path, output_file)
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