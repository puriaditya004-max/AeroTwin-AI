from __future__ import annotations

from pathlib import Path
from typing import Any

from app.settings import Settings, load_yaml
from simulation.engine_model import EngineModel


class ScenarioCatalog:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._definitions: dict[str, dict[str, Any]] = {}
        self.reload()

    def reload(self) -> None:
        self._definitions = {}
        for name, relative in self.settings.scenarios.items():
            path = Path(relative)
            if not path.is_absolute():
                path = self.settings.configDir / path
            definition = load_yaml(path)
            definition["id"] = definition.get("id", name)
            if definition["id"] != name:
                raise ValueError(f"Scenario file id {definition['id']!r} does not match catalog key {name!r}")
            self._definitions[name] = definition

    def names(self) -> list[str]:
        return sorted(self._definitions)

    def get(self, name: str) -> dict[str, Any]:
        if name not in self._definitions:
            known = ", ".join(self.names()) or "(none)"
            raise KeyError(f"Unknown scenario {name!r}. Available: {known}")
        return self._definitions[name]

    def model(self, name: str) -> EngineModel:
        return EngineModel(
            self.get(name),
            producer_version=self.settings.service.producerVersion,
            schema_version=self.settings.service.schemaVersion,
            replay_epoch=self.settings.publish.replayEpoch,
        )
