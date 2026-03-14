# core/skill_manager.py — Dynamic skill loader and executor

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Dict, List


class SkillManager:
    def __init__(
        self, skills_dir: str = 'skills', enabled: List[str] | None = None
    ):
        self.skills_dir = Path(skills_dir)
        self._skills: Dict[str, Any] = {}
        self._load(enabled or [])

    # ── loading ─────────────────────────────────────────────────────────────

    def _load(self, enabled: List[str]):
        # Ensure the skills package is importable for relative imports
        if 'skills' not in sys.modules:
            importlib.import_module('skills')

        from skills.base_skill import BaseSkill

        for name in enabled:
            path = self.skills_dir / f'{name}.py'
            if not path.exists():
                continue
            try:
                module_name = f'skills.{name}'
                spec = importlib.util.spec_from_file_location(module_name, path)
                module = importlib.util.module_from_spec(spec)       # type: ignore[arg-type]
                module.__package__ = 'skills'
                sys.modules[module_name] = module
                spec.loader.exec_module(module)                        # type: ignore[union-attr]
                for attr in dir(module):
                    cls = getattr(module, attr)
                    if (
                        isinstance(cls, type)
                        and issubclass(cls, BaseSkill)
                        and cls is not BaseSkill
                    ):
                        instance = cls()
                        self._skills[instance.name] = instance
                        break
            except Exception as exc:
                print(f'[skill_manager] Failed to load {name!r}: {exc}')

    # ── execution ───────────────────────────────────────────────────────────

    def execute(self, skill_name: str, **kwargs) -> Any:
        if skill_name not in self._skills:
            return f'Skill {skill_name!r} not found.'
        try:
            return self._skills[skill_name].execute(**kwargs)
        except Exception as exc:
            return f'Skill {skill_name!r} error: {exc}'

    # ── info ────────────────────────────────────────────────────────────────

    def list_skills(self) -> List[str]:
        return list(self._skills.keys())

    def get_tool_definitions(self) -> List[Dict]:
        return [s.get_tool_definition() for s in self._skills.values()]
