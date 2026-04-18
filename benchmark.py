"""Ytelsesbenchmark for Pitch & Plunder.

Kjører en gitt scene i N sekunder med oppdatering og tegning, og rapporterer:
- FPS: gjennomsnitt / min / 1% lavest (P1)
- Frame time (ms): gjennomsnitt
- Minnebruk (maks RSS via resource.getrusage)
- cProfile topp-20 heteste funksjoner (kumulativ tid)

Brukes etter hver fase og resultatet limes inn i BENCHMARKS.md.
"""

from __future__ import annotations

import argparse
import cProfile
import io
import logging
import pstats
import resource
import sys
import time

import constants
import pygame

from main import PlaceholderScene, _load_font
from scenes.parallax_test import ParallaxTestScene


log = logging.getLogger("benchmark")


def _build_scene(name: str, font: pygame.font.Font):
    """Scene-fabrikk. Utvides etter hvert som flere scener finnes."""
    if name == "placeholder":
        return PlaceholderScene(font)
    if name == "parallax_test":
        return ParallaxTestScene(font)
    raise ValueError(f"Ukjent scene: {name}")


def _run_loop(scene, duration_sec: float, drive_camera: bool = False) -> list[float]:
    """Kjør scene i oppgitt tid. Returnerer liste over frame times i sekunder.

    Hvis `drive_camera=True`: poster syntetiske KEYDOWN/KEYUP-events for
    høyre og venstre pil slik at kameraet beveger seg jevnt gjennom hele
    verden under målingen. Brukes for parallax-test der statisk rendering
    ikke ville dekke scroll-costen.
    """
    render_surface = pygame.Surface(
        (constants.RENDER_WIDTH, constants.RENDER_HEIGHT)
    ).convert()
    clock = pygame.time.Clock()
    frame_times: list[float] = []

    if drive_camera:
        # Simuler "hold D" for høyre-bevegelse fra start
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_d}))
    reverse_at = duration_sec * 0.5
    reversed_yet = False

    start = time.perf_counter()
    while True:
        elapsed = time.perf_counter() - start
        if elapsed >= duration_sec:
            break
        dt = clock.tick(constants.TARGET_FPS) / 1000.0

        if drive_camera and not reversed_yet and elapsed >= reverse_at:
            # Bytt retning halvveis for å dekke begge endene av verden
            pygame.event.post(pygame.event.Event(pygame.KEYUP, {"key": pygame.K_d}))
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, {"key": pygame.K_a}))
            reversed_yet = True

        for event in pygame.event.get():
            if drive_camera:
                scene.handle_event(event)

        frame_start = time.perf_counter()
        scene.update(dt)
        scene.draw(render_surface)
        frame_times.append(time.perf_counter() - frame_start)
    return frame_times


def _summarize(frame_times: list[float]) -> dict[str, float]:
    if not frame_times:
        return {"fps_avg": 0.0, "fps_min": 0.0, "fps_p1": 0.0, "frame_ms_avg": 0.0}
    fps = [1.0 / t if t > 0 else 0.0 for t in frame_times]
    fps_sorted = sorted(fps)
    # 1% lav: gjennomsnitt av de laveste 1% framene
    n_low = max(1, len(fps_sorted) // 100)
    p1 = sum(fps_sorted[:n_low]) / n_low
    return {
        "fps_avg": sum(fps) / len(fps),
        "fps_min": min(fps),
        "fps_p1": p1,
        "frame_ms_avg": (sum(frame_times) / len(frame_times)) * 1000.0,
    }


def _peak_rss_mb() -> float:
    """Maks RSS i MB. På Linux gir ru_maxrss verdi i KB."""
    usage = resource.getrusage(resource.RUSAGE_SELF)
    return usage.ru_maxrss / 1024.0


def benchmark(scene_name: str = "placeholder", duration_sec: float = 10.0) -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    pygame.display.init()
    pygame.font.init()
    pygame.event.set_blocked(constants.BLOCKED_EVENTS)
    # Hidden surface: vi trenger ikke vise vinduet for benchmark
    pygame.display.set_mode(
        (constants.RENDER_WIDTH, constants.RENDER_HEIGHT), pygame.HIDDEN
    )

    font = _load_font(8)
    scene = _build_scene(scene_name, font)
    scene.on_enter()

    drive_camera = scene_name == "parallax_test"
    profiler = cProfile.Profile()
    profiler.enable()
    frame_times = _run_loop(scene, duration_sec, drive_camera=drive_camera)
    profiler.disable()

    stats_buf = io.StringIO()
    stats = pstats.Stats(profiler, stream=stats_buf).sort_stats("cumulative")
    stats.print_stats(20)

    summary = _summarize(frame_times)
    rss_mb = _peak_rss_mb()

    print("=" * 60)
    print(f"Scene: {scene_name}   Duration: {duration_sec:.1f}s   "
          f"Frames: {len(frame_times)}")
    print("-" * 60)
    print(f"FPS avg:   {summary['fps_avg']:8.2f}")
    print(f"FPS min:   {summary['fps_min']:8.2f}")
    print(f"FPS 1%:    {summary['fps_p1']:8.2f}")
    print(f"Frame ms:  {summary['frame_ms_avg']:8.3f}")
    print(f"Peak RSS:  {rss_mb:8.2f} MB")
    print("-" * 60)
    print("cProfile (top 20 cumulative):")
    print(stats_buf.getvalue())
    print("=" * 60)

    pygame.display.quit()
    pygame.font.quit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Pitch & Plunder benchmark")
    parser.add_argument("--scene", default="parallax_test", help="Navn på scenen")
    parser.add_argument("--duration", type=float, default=10.0, help="Sekunder")
    args = parser.parse_args()
    benchmark(args.scene, args.duration)
    return 0


if __name__ == "__main__":
    sys.exit(main())
