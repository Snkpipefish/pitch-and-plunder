"""ModernGL post-processing pipeline (v2.7+, `high`-preset).

Tar 640x360 pygame-rendret bilde og kjører det gjennom 2-3 fragment-shader-
passes (bloom + color grading + valgfri CRT) før det vises på skjermen.

Designprinsipper:

- **Aldri krasj på init-feil.** Hvis GL-kontekst ikke kan opprettes (manglende
  driver, fjernskjerm uten GL, manglende libGL-symlink), faller vi tilbake til
  ren pygame-rendering. Brukeren ser et logg-varsel, ikke en crash.
- **Spill-koden skal ikke vite om pipelinen.** Scenene tegner som før til en
  640x360 surface. Pipelinen plukker opp surfacen og driver visningen.
- **Lazy import.** `moderngl` og `numpy` lastes først når `high`-preset er
  valgt, slik at `low`-preset kjører helt uten dem.
"""

from __future__ import annotations

import ctypes
import logging
from typing import Optional

import pygame

log = logging.getLogger("post_fx")


def _patch_moderngl_libgl() -> None:
    """Monkey-patch _moderngl.DefaultLoader til å falle tilbake til libGL.so.1.

    Mint 21.3 / Ubuntu 22.04 leverer `libGL.so.1` men ikke `libGL.so` med
    mindre `libgl1-mesa-dev` er installert. moderngl hardkoder `libGL.so` i
    sin Linux-loader (kjent issue), så vi shim-er ctypes-kallet for kun denne
    spesifikke importen — uten å påvirke globalt ctypes-oppførsel.
    """
    try:
        import _moderngl  # type: ignore[import-not-found]
    except ImportError:
        return

    original_init = _moderngl.DefaultLoader.__init__

    def patched_init(self, *args, **kwargs):
        original_cdll = ctypes.CDLL

        def cdll_with_fallback(name, *a, **kw):
            try:
                return original_cdll(name, *a, **kw)
            except OSError:
                if name == "libGL.so":
                    return original_cdll("libGL.so.1", *a, **kw)
                raise

        ctypes.CDLL = cdll_with_fallback  # type: ignore[assignment]
        try:
            return original_init(self, *args, **kwargs)
        finally:
            ctypes.CDLL = original_cdll  # type: ignore[assignment]

    _moderngl.DefaultLoader.__init__ = patched_init


# --- Shaders --------------------------------------------------------------

# Vertex shader: ren passthrough for fullskjerm-quad (NDC).
_VERTEX_SHADER = """
#version 330 core
in vec2 in_pos;
in vec2 in_uv;
out vec2 v_uv;
void main() {
    v_uv = in_uv;
    gl_Position = vec4(in_pos, 0.0, 1.0);
}
"""

# Brightpass: ekstrahér piksler over luminans-terskel for bloom.
_FRAG_BRIGHTPASS = """
#version 330 core
in vec2 v_uv;
out vec4 frag;
uniform sampler2D u_src;
uniform float u_threshold;
void main() {
    vec3 col = texture(u_src, v_uv).rgb;
    float lum = dot(col, vec3(0.299, 0.587, 0.114));
    float k = max(0.0, lum - u_threshold) / max(1e-4, 1.0 - u_threshold);
    frag = vec4(col * k, 1.0);
}
"""

# Separabel 9-tap blur. To passes (horisontal + vertikal) for bloom-halo.
_FRAG_BLUR = """
#version 330 core
in vec2 v_uv;
out vec4 frag;
uniform sampler2D u_src;
uniform vec2 u_dir;          // (1/w, 0) horisontal, (0, 1/h) vertikal
uniform float u_radius;      // antall texeler å gå ut til hver side

void main() {
    vec3 acc = vec3(0.0);
    float total = 0.0;
    // 9-tap: -4..+4
    for (int i = -4; i <= 4; ++i) {
        float w = exp(-float(i*i) / (2.0 * 4.0));
        vec2 off = u_dir * float(i) * u_radius;
        acc += texture(u_src, v_uv + off).rgb * w;
        total += w;
    }
    frag = vec4(acc / total, 1.0);
}
"""

# Composite + grading + valgfri CRT. Tar src + bloom som inputs.
_FRAG_COMPOSITE = """
#version 330 core
in vec2 v_uv;
out vec4 frag;
uniform sampler2D u_src;
uniform sampler2D u_bloom;
uniform float u_bloom_strength;
uniform float u_warm_cool;       // -1..+1: kald → varm split
uniform vec3  u_warm_tint;
uniform vec3  u_cool_tint;
uniform float u_crt;             // 0 = av, 1 = full scanlines
uniform vec2  u_resolution;      // (480, 270) intern (Fase 2.6)

void main() {
    vec3 base = texture(u_src, v_uv).rgb;
    vec3 bloom = texture(u_bloom, v_uv).rgb;
    vec3 col = base + bloom * u_bloom_strength;

    // Tematisk grading: venstre side varm (taverna), høyre side kald (børshus).
    float side = (v_uv.x - 0.5) * 2.0;        // -1..+1
    float warm_w = clamp(0.5 - 0.5 * side, 0.0, 1.0);
    vec3 tint = mix(u_cool_tint, u_warm_tint, warm_w);
    col = mix(col, col * tint, abs(u_warm_cool));

    // CRT scanlines: subtil dimming på partalls-rader.
    if (u_crt > 0.0) {
        float row = floor(v_uv.y * u_resolution.y);
        float scan = mod(row, 2.0) < 0.5 ? 1.0 : 1.0 - 0.08 * u_crt;
        col *= scan;
    }

    frag = vec4(col, 1.0);
}
"""


class PostFXPipeline:
    """ModernGL post-FX-pipeline. Eier GL-kontekst, FBO-er, programmer og quad.

    Bruks:
        pipeline = PostFXPipeline.try_create(window_size=(1280, 720))
        if pipeline is None:
            # Fall tilbake til ren pygame
            ...
        else:
            # Hver frame:
            scene.draw(render_surface)         # 640x360 pygame-surface
            pipeline.present(render_surface)   # rendrer + swap_buffers

    `try_create` fanger alle init-feil og returnerer None hvis GL ikke er
    tilgjengelig — kalleren faller tilbake til pygame.SCALED.
    """

    def __init__(self, ctx, programs: dict, fbos: dict, quad, window_size: tuple) -> None:
        self.ctx = ctx
        self.programs = programs
        self.fbos = fbos
        self.quad = quad
        self.window_size = window_size
        # Justérbare parametre — settes som uniforms hver frame.
        # Re-tunet 2026-04-30 for 480×270 / 24×40-sprites (Fase 2.6 sub-
        # steg 10): chunkier piksler trenger mindre blur-radius ellers blir
        # bildet søkkvått; lavere strength bevarer pixel-skarphet.
        self.bloom_threshold = 0.50
        self.bloom_radius = 1.8
        self.bloom_strength = 0.85
        self.warm_cool = 0.55
        self.warm_tint = (1.18, 1.02, 0.86)
        self.cool_tint = (0.88, 0.96, 1.16)
        self.crt = 0.0  # 0..1; 0 = av (pixel art ser allerede skarp ut uten)

    @classmethod
    def try_create(cls, window_size: tuple, render_size: tuple = (480, 270)) -> Optional["PostFXPipeline"]:
        """Forsøk å lage GL-kontekst og kompilere shaders. Returnerer None
        ved enhver feil — kalleren skal da bruke pygame.SCALED-fallback.

        Forutsetter at pygame.display er init og at vinduet ble laget med
        `pygame.OPENGL | pygame.DOUBLEBUF`. Lager IKKE vinduet selv, fordi
        SCALED-flagget og OPENGL-flagget er gjensidig utelukkende — flagg-
        valget hører hjemme i main.py basert på preset.
        """
        try:
            _patch_moderngl_libgl()
            import moderngl  # type: ignore[import-not-found]
            import numpy as np  # type: ignore[import-not-found]
        except ImportError as exc:
            log.warning("PostFX init: avhengighet mangler (%s) — fallback til pygame", exc)
            return None

        try:
            ctx = moderngl.create_context()
        except Exception as exc:  # bredt: GL-init kan feile på mange måter
            log.warning("PostFX init: kunne ikke opprette GL-kontekst (%s)", exc)
            return None

        try:
            log.info(
                "PostFX GL: vendor=%s renderer=%s glsl=%s",
                ctx.info.get("GL_VENDOR"),
                ctx.info.get("GL_RENDERER"),
                ctx.info.get("GL_SHADING_LANGUAGE_VERSION"),
            )

            # Programmer
            prog_brightpass = ctx.program(
                vertex_shader=_VERTEX_SHADER, fragment_shader=_FRAG_BRIGHTPASS
            )
            prog_blur = ctx.program(
                vertex_shader=_VERTEX_SHADER, fragment_shader=_FRAG_BLUR
            )
            prog_composite = ctx.program(
                vertex_shader=_VERTEX_SHADER, fragment_shader=_FRAG_COMPOSITE
            )

            # Fullskjerm-quad: to triangler i NDC + UV.
            quad_data = np.array([
                # x,    y,    u, v
                -1.0, -1.0, 0.0, 1.0,
                 1.0, -1.0, 1.0, 1.0,
                -1.0,  1.0, 0.0, 0.0,
                 1.0,  1.0, 1.0, 0.0,
            ], dtype="f4")
            vbo = ctx.buffer(quad_data.tobytes())
            quads = {}
            for name, prog in [
                ("brightpass", prog_brightpass),
                ("blur", prog_blur),
                ("composite", prog_composite),
            ]:
                quads[name] = ctx.vertex_array(
                    prog,
                    [(vbo, "2f 2f", "in_pos", "in_uv")],
                )

            # Source-tekstur (640x360, RGBA fra pygame).
            tex_src = ctx.texture(render_size, 4)
            tex_src.filter = (moderngl.NEAREST, moderngl.NEAREST)

            # Bloom-FBO-er på halv oppløsning for hastighet.
            half_w, half_h = render_size[0] // 2, render_size[1] // 2
            tex_bright = ctx.texture((half_w, half_h), 4)
            tex_bright.filter = (moderngl.LINEAR, moderngl.LINEAR)
            fbo_bright = ctx.framebuffer(color_attachments=[tex_bright])

            tex_blur_h = ctx.texture((half_w, half_h), 4)
            tex_blur_h.filter = (moderngl.LINEAR, moderngl.LINEAR)
            fbo_blur_h = ctx.framebuffer(color_attachments=[tex_blur_h])

            tex_blur_v = ctx.texture((half_w, half_h), 4)
            tex_blur_v.filter = (moderngl.LINEAR, moderngl.LINEAR)
            fbo_blur_v = ctx.framebuffer(color_attachments=[tex_blur_v])

            programs = {
                "brightpass": prog_brightpass,
                "blur": prog_blur,
                "composite": prog_composite,
            }
            fbos = {
                "tex_src": tex_src,
                "tex_bright": tex_bright,
                "fbo_bright": fbo_bright,
                "tex_blur_h": tex_blur_h,
                "fbo_blur_h": fbo_blur_h,
                "tex_blur_v": tex_blur_v,
                "fbo_blur_v": fbo_blur_v,
                "render_size": render_size,
                "half_size": (half_w, half_h),
            }

            return cls(ctx, programs, fbos, quads, window_size)

        except Exception as exc:
            log.warning("PostFX init: shader/buffer-oppsett feilet (%s)", exc)
            return None

    def resize(self, window_size: tuple) -> None:
        """Kalles ved fullscreen-toggle eller window-resize."""
        self.window_size = window_size

    def present(self, render_surface: pygame.Surface, flip: bool = True) -> None:
        """Last 640x360 surfacen til GL-tekstur og kjør pipelinen + swap.

        Pipeline:
          1. Last `render_surface` → tex_src
          2. brightpass(tex_src) → fbo_bright
          3. blur horisontalt(fbo_bright) → fbo_blur_h
          4. blur vertikalt(fbo_blur_h) → fbo_blur_v
          5. composite(tex_src, fbo_blur_v) → screen
          6. pygame.display.flip()
        """
        import moderngl  # allerede importert i try_create
        ctx = self.ctx
        prog_b = self.programs["brightpass"]
        prog_blur = self.programs["blur"]
        prog_c = self.programs["composite"]

        tex_src = self.fbos["tex_src"]
        tex_bright = self.fbos["tex_bright"]
        fbo_bright = self.fbos["fbo_bright"]
        tex_blur_h = self.fbos["tex_blur_h"]
        fbo_blur_h = self.fbos["fbo_blur_h"]
        tex_blur_v = self.fbos["tex_blur_v"]
        fbo_blur_v = self.fbos["fbo_blur_v"]
        render_w, render_h = self.fbos["render_size"]
        half_w, half_h = self.fbos["half_size"]

        # 1. Surface → tekstur. pygame-CE har get_view; vi bruker en
        #    bytes-konvertering for portabilitet på tvers av pixel-formater.
        # Surface er 8-bit per kanal; konverter til 32-bit RGBA hvis ikke.
        if render_surface.get_bitsize() != 32:
            render_surface = render_surface.convert(32)
        # tobytes("RGBA") gir piksler i top-down-rekkefølge.
        # Vi har satt UV slik at v=0 er topp (se quad_data: y=+1 → v=0).
        tex_src.write(pygame.image.tobytes(render_surface, "RGBA"))

        # 2. brightpass
        fbo_bright.use()
        ctx.viewport = (0, 0, half_w, half_h)
        tex_src.use(location=0)
        prog_b["u_src"].value = 0
        prog_b["u_threshold"].value = self.bloom_threshold
        self.quad["brightpass"].render(mode=moderngl.TRIANGLE_STRIP)

        # 3. blur horisontal
        fbo_blur_h.use()
        ctx.viewport = (0, 0, half_w, half_h)
        tex_bright.use(location=0)
        prog_blur["u_src"].value = 0
        prog_blur["u_dir"].value = (1.0 / half_w, 0.0)
        prog_blur["u_radius"].value = self.bloom_radius
        self.quad["blur"].render(mode=moderngl.TRIANGLE_STRIP)

        # 4. blur vertikal
        fbo_blur_v.use()
        ctx.viewport = (0, 0, half_w, half_h)
        tex_blur_h.use(location=0)
        prog_blur["u_src"].value = 0
        prog_blur["u_dir"].value = (0.0, 1.0 / half_h)
        prog_blur["u_radius"].value = self.bloom_radius
        self.quad["blur"].render(mode=moderngl.TRIANGLE_STRIP)

        # 5. composite til skjerm
        ctx.screen.use()
        ctx.viewport = (0, 0, self.window_size[0], self.window_size[1])
        tex_src.use(location=0)
        tex_blur_v.use(location=1)
        prog_c["u_src"].value = 0
        prog_c["u_bloom"].value = 1
        prog_c["u_bloom_strength"].value = self.bloom_strength
        prog_c["u_warm_cool"].value = self.warm_cool
        prog_c["u_warm_tint"].value = self.warm_tint
        prog_c["u_cool_tint"].value = self.cool_tint
        prog_c["u_crt"].value = self.crt
        prog_c["u_resolution"].value = (float(render_w), float(render_h))
        self.quad["composite"].render(mode=moderngl.TRIANGLE_STRIP)

        if flip:
            pygame.display.flip()

    def release(self) -> None:
        """Frigi GL-ressurser. Kalles ved exit eller preset-bytte."""
        for k in ("fbo_bright", "fbo_blur_h", "fbo_blur_v",
                  "tex_src", "tex_bright", "tex_blur_h", "tex_blur_v"):
            obj = self.fbos.get(k)
            if obj is not None:
                try:
                    obj.release()
                except Exception:
                    pass
        for prog in self.programs.values():
            try:
                prog.release()
            except Exception:
                pass
        try:
            self.ctx.release()
        except Exception:
            pass
