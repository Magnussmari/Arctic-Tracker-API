#!/usr/bin/env python3
# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-08-14
"""One way to write a figure: every scripted figure is written as an image
(PNG and SVG) as well as interactive HTML, so running the pipeline regenerates
the figures themselves and not only web pages.
"""
from __future__ import annotations

from pathlib import Path

PRODUCTION = Path(__file__).parent.parent / "production"

# 300 dpi at roughly single- and double-column widths. Nature Communications
# wants at least 300 dpi; scale=2 on these pixel dimensions clears it.
SCALE = 2


def save_figure(fig, stem: str, width: int = 1600, height: int = 1200) -> tuple[Path, Path]:
    """Write both artefacts, or raise.

    The HTML is what the platform serves and what makes the data explorable.
    The PNG is what the manuscript needs. Both, every time, from one call, so
    the two cannot drift and so no script can quietly produce only one.
    """
    PRODUCTION.mkdir(exist_ok=True)
    html_file = PRODUCTION / f"{stem}.html"
    png_file = PRODUCTION / f"{stem}.png"

    fig.write_html(str(html_file), include_plotlyjs="cdn", full_html=True)

    try:
        fig.write_image(str(png_file), width=width, height=height, scale=SCALE)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"{stem}: the figure could not be written as an image ({exc}).\n"
            f"This is a failure, not a skip: a script that emits only HTML does "
            f"not regenerate a figure.\n"
            f"The renderer (kaleido) needs a Chrome or Chromium browser; the "
            f"Dockerfile installs one."
        ) from exc

    # An image file that exists but is empty would satisfy every existence check
    # written about this directory.
    if png_file.stat().st_size < 5_000:
        raise RuntimeError(
            f"{stem}: wrote {png_file.stat().st_size} bytes, which is too small "
            f"to be a rendered figure. A renderer that fails to find a browser "
            f"can still write a valid, blank image.")

    # Vector as well as raster: the journal wants vector artwork for line art,
    # and a raster schematic is the first thing
    # a production editor sends back.
    svg_file = PRODUCTION / f"{stem}.svg"
    try:
        fig.write_image(str(svg_file), width=width, height=height)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"{stem}: could not be written as vector ({exc}). Line art must be "
            f"delivered as vector artwork."
        ) from exc
    if svg_file.stat().st_size < 2_000:
        raise RuntimeError(
            f"{stem}: the SVG is {svg_file.stat().st_size} bytes, too small to be "
            f"a rendered figure.")

    print(f"  wrote {html_file.name}, {png_file.name} "
          f"({png_file.stat().st_size // 1024} KB) and {svg_file.name} "
          f"({svg_file.stat().st_size // 1024} KB)")
    return html_file, png_file
