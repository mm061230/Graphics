from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAYER_CONFIG_PATH = PROJECT_ROOT / "config" / "layers_config.json"


@dataclass(frozen=True)
class LayerStyle:
    name: str
    stroke: str
    width: float
    dash: tuple[float, ...]
    description: str = ""


@dataclass(frozen=True)
class LayerConfig:
    render_order: tuple[str, ...]
    layers: dict[str, LayerStyle]

    def style_for(self, layer_name: str) -> LayerStyle:
        try:
            return self.layers[layer_name]
        except KeyError as exc:
            raise ValueError(f"unknown layer: {layer_name}") from exc


def load_layer_config(path: Path = DEFAULT_LAYER_CONFIG_PATH) -> LayerConfig:
    data = json.loads(path.read_text(encoding="utf-8"))
    render_order = tuple(data["render_order"])
    layers = {
        name: LayerStyle(
            name=name,
            stroke=payload["stroke"],
            width=float(payload["width"]),
            dash=tuple(float(value) for value in payload.get("dash", [])),
            description=payload.get("description", ""),
        )
        for name, payload in data["layers"].items()
    }
    missing_layers = set(render_order) - set(layers)
    if missing_layers:
        raise ValueError(f"render_order references missing layers: {sorted(missing_layers)}")
    return LayerConfig(render_order=render_order, layers=layers)
