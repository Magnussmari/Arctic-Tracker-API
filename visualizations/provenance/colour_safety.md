# Colour-vision safety audit — manuscript figures (2026-07-22)

Audited against deuteranopia/protanopia/tritanopia simulation heuristics.

| Fig | Palette | CVD verdict |
|---|---|---|
| 1 | IUCN standard (CR `#D81E05` → LC `#60C659`) + appendix bar labels printed on marks (`textposition='auto'`) + hover text | **Pass** — the red→green ramp is the IUCN convention and is never the sole channel: values are printed on bars and statuses named in hover/legend. |
| 2 | Panel A: IUCN status ramp (CR `#D81E05` → LC `#60C659`) with values printed on bars + species named on axis; Panels B/C: single-hue bars + printed values | **Pass** — Panel A uses the IUCN convention but never as sole channel (values printed, species axis-labeled, status in hover); B/C luminance-only. |
| 3 | `#2E5266` blue-grey sequential, table panel with explicit numbers | **Pass** — single hue; the table carries all values textually. |
| 4 | IUCN standard ramp + per-point hover with status name | **Pass** — line/point positions encode status ordinally; colour redundant. |
| 5 | IUCN ramp heatmap with colorbar tick labels (LC…RE) + per-cell hover | **Pass** — ordered categories with labeled colorbar; cells hover-named. |
| 7 | Status/appendix categorical colors + species names on axes and values printed | **Pass** — categories are axis-labeled; colour redundant. |
| 8 | Same construction as 7 | **Pass**. |

Rule applied: no figure may encode information in hue alone — every colour
channel is backed by position, text label, or explicit legend naming. The
IUCN red→green ramp is retained deliberately (domain convention) with
redundant encoding, not removed.
