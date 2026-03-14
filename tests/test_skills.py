"""Tests for baby_robot.skills module."""

import pytest

from baby_robot.memory import Memory
from baby_robot.skills import Skills


@pytest.fixture
def memory(tmp_path):
    return Memory(str(tmp_path / "brain.json"))


@pytest.fixture
def skills(memory):
    return Skills(memory)


class TestSkillsGreeting:
    def test_hello_response(self, skills):
        response, pts = skills.respond("你好")
        assert response
        assert pts >= 1

    def test_bye_response(self, skills):
        response, pts = skills.respond("再见")
        assert response
        assert pts >= 1

    def test_help_response(self, skills):
        response, pts = skills.respond("你能做什么")
        assert "教我" in response

    def test_status_response(self, skills):
        response, pts = skills.respond("状态")
        assert "等级" in response
        assert pts >= 1


class TestSkillsTeach:
    def test_teach_valid_command(self, skills, memory):
        response, pts = skills.respond("教我:月亮:月亮真美啊")
        assert "月亮" in response
        assert pts == 5
        assert "月亮" in memory.learned_responses

    def test_teach_invalid_format(self, skills):
        response, pts = skills.respond("教我:月亮")
        assert "格式" in response
        assert pts == 0

    def test_teach_empty_phrase(self, skills):
        response, pts = skills.respond("教我::回答")
        assert pts == 0

    def test_learned_response_used(self, skills, memory):
        memory.learn_response("彩虹", "彩虹好漂亮！")
        response, pts = skills.respond("彩虹是什么")
        assert "彩虹好漂亮" in response
        assert pts == 3


class TestSkillsMath:
    def test_math_requires_level_6(self, skills, memory):
        # At level 1, math skill should not fire
        response, _ = skills.respond("3+4")
        assert "计算结果" not in response

    def test_math_at_level_6(self, skills, memory):
        memory.add_growth_points(10000)  # max level
        response, pts = skills.respond("3+4")
        assert "计算结果" in response
        assert "7" in response

    def test_math_subtraction(self, skills, memory):
        memory.add_growth_points(10000)
        response, _ = skills.respond("10-3")
        assert "7" in response

    def test_math_division_by_zero(self, skills, memory):
        memory.add_growth_points(10000)
        response, _ = skills.respond("5/0")
        assert "除数不能为零" in response


class TestSkillsStory:
    def test_story_requires_level_5(self, skills, memory):
        response, _ = skills.respond("讲个故事")
        assert "故事" not in response or "等级" in response or "成长" in response

    def test_story_at_level_5(self, skills, memory):
        # Give enough points to reach level 5 (60 points)
        memory.add_growth_points(60)
        response, pts = skills.respond("讲个故事")
        assert "故事" in response or "机器人" in response
        assert pts >= 2


class TestSkillsFallback:
    def test_unknown_input_returns_string(self, skills):
        response, pts = skills.respond("xyzabcdef12345")
        assert isinstance(response, str)
        assert len(response) > 0
        assert pts >= 1
