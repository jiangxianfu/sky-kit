"""
Memory module: handles persistent brain state for the baby robot.

The robot's knowledge is stored in a JSON file so it survives restarts
and accumulates experience over time.
"""

import json
import os
import time
from typing import Any

_DEFAULT_BRAIN: dict[str, Any] = {
    "version": "0.1.0",
    "birth_time": None,          # Unix timestamp of first run
    "interaction_count": 0,      # Total number of messages handled
    "growth_points": 0,          # Points that drive level-up
    "level": 1,                  # Current growth level (baby=1 … genius=10)
    "learned_responses": {},     # user-phrase -> robot response mappings
    "topics_discussed": [],      # history of topic keywords
}

_GROWTH_THRESHOLDS = {
    1: 0,
    2: 5,
    3: 15,
    4: 30,
    5: 60,
    6: 100,
    7: 150,
    8: 220,
    9: 300,
    10: 400,
}

_LEVEL_NAMES = {
    1: "新生婴儿 (Newborn)",
    2: "好奇宝宝 (Curious Baby)",
    3: "学步儿童 (Toddler)",
    4: "小学生 (Child)",
    5: "少年 (Youngster)",
    6: "青少年 (Teenager)",
    7: "青年 (Young Adult)",
    8: "成年人 (Adult)",
    9: "智者 (Wise One)",
    10: "天才 (Genius)",
}


class Memory:
    """Persistent memory (brain) for the baby robot."""

    def __init__(self, brain_path: str) -> None:
        self._path = brain_path
        self._data: dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if os.path.exists(self._path):
            with open(self._path, encoding="utf-8") as f:
                saved = json.load(f)
            # Merge with defaults so new fields are always present
            brain = dict(_DEFAULT_BRAIN)
            brain.update(saved)
            self._data = brain
        else:
            self._data = dict(_DEFAULT_BRAIN)
            self._data["birth_time"] = time.time()
            self._save()

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self._path) or ".", exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # Public accessors
    # ------------------------------------------------------------------

    @property
    def level(self) -> int:
        return int(self._data["level"])

    @property
    def level_name(self) -> str:
        return _LEVEL_NAMES.get(self.level, "未知 (Unknown)")

    @property
    def interaction_count(self) -> int:
        return int(self._data["interaction_count"])

    @property
    def growth_points(self) -> int:
        return int(self._data["growth_points"])

    @property
    def learned_responses(self) -> dict[str, str]:
        return dict(self._data.get("learned_responses", {}))

    @property
    def topics_discussed(self) -> list[str]:
        return list(self._data.get("topics_discussed", []))

    def age_days(self) -> float:
        birth = self._data.get("birth_time") or time.time()
        return (time.time() - birth) / 86400

    # ------------------------------------------------------------------
    # Mutation helpers (each call saves to disk)
    # ------------------------------------------------------------------

    def record_interaction(self) -> None:
        self._data["interaction_count"] = self.interaction_count + 1
        self._save()

    def add_growth_points(self, pts: int) -> bool:
        """Add growth points; return True if the robot levelled-up."""
        self._data["growth_points"] = self.growth_points + pts
        levelled_up = self._try_level_up()
        self._save()
        return levelled_up

    def learn_response(self, phrase: str, response: str) -> None:
        """Store a new learned response."""
        lr = self._data.setdefault("learned_responses", {})
        lr[phrase.lower().strip()] = response
        self._data["learned_responses"] = lr
        self._save()

    def record_topic(self, topic: str) -> None:
        topics = self._data.setdefault("topics_discussed", [])
        if topic not in topics:
            topics.append(topic)
        self._data["topics_discussed"] = topics
        self._save()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _try_level_up(self) -> bool:
        levelled_up = False
        while self.level < 10:
            next_level = self.level + 1
            threshold = _GROWTH_THRESHOLDS.get(next_level, 9999)
            if self.growth_points >= threshold:
                self._data["level"] = next_level
                levelled_up = True
            else:
                break
        return levelled_up

    def next_level_points_needed(self) -> int:
        """Return how many more growth points are needed to reach next level."""
        next_level = self.level + 1
        if next_level > 10:
            return 0
        threshold = _GROWTH_THRESHOLDS.get(next_level, 9999)
        return max(0, threshold - self.growth_points)
