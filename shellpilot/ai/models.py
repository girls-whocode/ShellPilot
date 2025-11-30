from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import json
import os
import urllib.request


# Base models/ directory under the repo root:
BASE_MODELS_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
    / "models"
)

# Remote manifest of available models.
# Default: your GitHub raw URL, override via env if needed.
DEFAULT_MODELS_MANIFEST_URL = os.getenv(
    "SHELLPILOT_MODELS_URL",
    "https://raw.githubusercontent.com/girls-whocode/ShellPilot/refs/heads/main/models.json",
)


@dataclass
class AIModelSpec:
    id: str
    name: str
    description: str
    subdir: str
    filename: str
    download_url: str
    recommended_ram_gb: int


AI_MODEL_REGISTRY: Dict[str, AIModelSpec] = {}
_MODELS_LOADED = False


def _load_manifest_from_url(url: str) -> List[dict]:
    """Fetch models.json from the given URL and parse JSON."""
    with urllib.request.urlopen(url) as resp:
        data = resp.read()
    return json.loads(data.decode("utf-8"))


def _load_manifest_local_fallback() -> List[dict]:
    """
    Optional local fallback: config/models.local.json.
    Used if remote fetch fails (offline, GitHub down, bad URL, etc.).
    """
    fallback_path = (
        Path(__file__).resolve().parents[2]
        / "config"
        / "models.local.json"
    )
    if fallback_path.is_file():
        return json.loads(fallback_path.read_text(encoding="utf-8"))

    # Last-ditch hardcoded fallback so AI isn't completely dead.
    return [
        {
            "id": "phi-3.5-mini-q4",
            "name": "Phi-3.5-mini (Q4_K_M)",
            "description": "Fast, low-RAM; good default on laptops and small VMs.",
            "subdir": "phi-3.5-mini",
            "filename": "Phi-3.5-mini-instruct-Q4_K_M.gguf",
            "download_url": "https://your-cdn-or-hf/Phi-3.5-mini-instruct-Q4_K_M.gguf",
            "recommended_ram_gb": 8,
        }
    ]


def _ensure_models_loaded() -> None:
    """Populate AI_MODEL_REGISTRY from remote manifest (with fallback)."""
    global AI_MODEL_REGISTRY, _MODELS_LOADED
    if _MODELS_LOADED:
        return

    try:
        specs_raw = _load_manifest_from_url(DEFAULT_MODELS_MANIFEST_URL)
    except Exception:
        # Network / URL failure – fall back to local JSON or minimal default
        specs_raw = _load_manifest_local_fallback()

    registry: Dict[str, AIModelSpec] = {}
    for item in specs_raw:
        spec = AIModelSpec(
            id=item["id"],
            name=item["name"],
            description=item.get("description", ""),
            subdir=item["subdir"],
            filename=item["filename"],
            download_url=item["download_url"],
            recommended_ram_gb=int(item.get("recommended_ram_gb", 8)),
        )
        registry[spec.id] = spec

    AI_MODEL_REGISTRY = registry
    _MODELS_LOADED = True


def get_model_registry() -> Dict[str, AIModelSpec]:
    """Public accessor: lazily load and return the model registry."""
    _ensure_models_loaded()
    return AI_MODEL_REGISTRY


def get_model_path(model_id: str) -> Path:
    """Return the on-disk path where this model's GGUF should live."""
    _ensure_models_loaded()
    spec = AI_MODEL_REGISTRY[model_id]
    return BASE_MODELS_DIR / spec.subdir / spec.filename
