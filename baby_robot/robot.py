"""
BabyRobot: the main robot class that ties memory and skills together.
"""

from __future__ import annotations

import os
import re

from .memory import Memory
from .skills import Skills

_DEFAULT_BRAIN_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "brain.json"
)


class BabyRobot:
    """
    A self-growing baby AI robot.

    The robot starts at level 1 with minimal capabilities. Every interaction
    earns growth points. Accumulating enough points causes the robot to
    level up, unlocking new skills.

    Usage
    -----
    >>> robot = BabyRobot()
    >>> print(robot.chat("你好"))
    >>> print(robot.chat("教我:月亮:月亮真美啊"))
    >>> print(robot.chat("状态"))
    """

    def __init__(self, brain_path: str | None = None) -> None:
        path = brain_path or os.environ.get("ROBOT_BRAIN_PATH") or _DEFAULT_BRAIN_PATH
        self._memory = Memory(os.path.normpath(path))
        self._skills = Skills(self._memory)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chat(self, user_input: str) -> str:
        """Process *user_input* and return the robot's response."""
        if not user_input or not user_input.strip():
            return "（小机器人歪着头，等待你说话）"

        # Extract keywords for topic tracking
        self._track_topics(user_input)

        # Generate response
        response, points = self._skills.respond(user_input)

        # Record interaction and growth
        self._memory.record_interaction()
        levelled_up = self._memory.add_growth_points(points)

        # Append level-up notice if applicable
        if levelled_up:
            response += self._skills.level_up_message(self._memory.level)

        return response

    @property
    def level(self) -> int:
        """Current growth level (1-10)."""
        return self._memory.level

    @property
    def level_name(self) -> str:
        """Human-readable name for current level."""
        return self._memory.level_name

    @property
    def interaction_count(self) -> int:
        """Total number of interactions so far."""
        return self._memory.interaction_count

    @property
    def growth_points(self) -> int:
        """Total accumulated growth points."""
        return self._memory.growth_points

    def status(self) -> str:
        """Return a formatted status / growth report."""
        return self._skills._handle_status()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _track_topics(self, text: str) -> None:
        # Very simple keyword extraction: words longer than 1 char
        words = re.findall(r"[\w\u4e00-\u9fff]{2,}", text)
        for word in words[:5]:  # limit to first 5 to avoid noise
            self._memory.record_topic(word)
