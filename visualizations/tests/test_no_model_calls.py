# @orchestrator: Magnús Smárason | smarason.is  @created: 2026-07-30
"""
Assert that no generative-model SDK or API client appears in figure pipeline code.

This is the mechanical check that figure_provenance.json's
ai_involvement.verified_by field points at. A figure may claim
ai_involvement.level == "none" only while this test passes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "visualizations" / "provenance" / "figure_provenance.json"

MODEL_PATTERN = re.compile(
    r"gemini|openai|anthropic|scite|claude|gpt-|llm|generativeai|transformers|langchain",
    re.IGNORECASE,
)

# Hosts that would indicate a model API call if requested.
MODEL_HOST_PATTERN = re.compile(
    r"api\.openai\.com|generativelanguage\.googleapis|api\.anthropic\.com|"
    r"api\.scite\.ai|openai\.azure\.com",
    re.IGNORECASE,
)


def _looks_like_path(value: object) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    # Annotations like "in-script aggregate query" are not paths.
    if " " in value and not value.startswith(("visualizations/", "data/", "ingest/")):
        return False
    return "/" in value or value.endswith(".py")


def _paths_from_figure(fig: dict) -> list[Path]:
    paths: list[Path] = []
    for key in ("script", "generator"):
        val = fig.get(key)
        if _looks_like_path(val):
            paths.append(ROOT / str(val).split()[0])
    for step in fig.get("processing_steps") or []:
        art = step.get("artifact")
        if _looks_like_path(art) and str(art).endswith(".py"):
            paths.append(ROOT / str(art).split()[0])
    # Deduplicate while preserving order.
    seen: set[Path] = set()
    out: list[Path] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST.is_file(), f"missing manifest: {MANIFEST}"
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data.get("schema_version") == "figure-provenance/v2"
    return data


def test_no_model_sdk_in_named_pipeline_files(manifest: dict) -> None:
    figures = manifest.get("figures") or {}
    scanned: list[Path] = []
    for fig_id, fig in figures.items():
        for path in _paths_from_figure(fig):
            assert path.is_file(), f"{fig_id}: missing pipeline file {path}"
            text = path.read_text(encoding="utf-8", errors="replace")
            match = MODEL_PATTERN.search(text)
            assert match is None, (
                f"{fig_id}: model reference {match.group(0)!r} in {path.relative_to(ROOT)}"
            )
            host = MODEL_HOST_PATTERN.search(text)
            assert host is None, (
                f"{fig_id}: model-host reference {host.group(0)!r} in {path.relative_to(ROOT)}"
            )
            scanned.append(path)

    # The pipeline is twelve files; fail loud if we somehow scanned none.
    assert len(scanned) >= 7, f"expected to scan pipeline scripts, got {len(scanned)}"


def test_ai_involvement_none_points_at_this_test(manifest: dict) -> None:
    for fig_id, fig in (manifest.get("figures") or {}).items():
        ai = fig.get("ai_involvement") or {}
        if ai.get("level") == "none":
            assert "test_no_model_calls" in (ai.get("verified_by") or ""), fig_id
