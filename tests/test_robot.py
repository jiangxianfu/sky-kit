"""Integration tests for BabyRobot."""

import pytest

from baby_robot import BabyRobot


@pytest.fixture
def robot(tmp_path):
    return BabyRobot(brain_path=str(tmp_path / "brain.json"))


class TestBabyRobotBasics:
    def test_chat_returns_string(self, robot):
        assert isinstance(robot.chat("你好"), str)

    def test_empty_input(self, robot):
        response = robot.chat("")
        assert "等待" in response or response  # still returns something

    def test_whitespace_input(self, robot):
        response = robot.chat("   ")
        assert isinstance(response, str)

    def test_interaction_count_increments(self, robot):
        assert robot.interaction_count == 0
        robot.chat("你好")
        assert robot.interaction_count == 1
        robot.chat("再见")
        assert robot.interaction_count == 2

    def test_growth_points_accumulate(self, robot):
        robot.chat("你好")
        assert robot.growth_points > 0

    def test_initial_level_is_1(self, robot):
        assert robot.level == 1

    def test_level_name_is_string(self, robot):
        assert isinstance(robot.level_name, str)
        assert len(robot.level_name) > 0

    def test_status_contains_level(self, robot):
        status = robot.status()
        assert "等级" in status


class TestBabyRobotLearning:
    def test_teach_command_stores_knowledge(self, robot):
        robot.chat("教我:星星:星星闪闪亮")
        response = robot.chat("星星是什么")
        assert "星星闪闪亮" in response

    def test_multiple_teach_commands(self, robot):
        robot.chat("教我:太阳:太阳很温暖")
        robot.chat("教我:月亮:月亮好圆啊")
        assert "太阳很温暖" in robot.chat("太阳")
        assert "月亮好圆啊" in robot.chat("月亮")


class TestBabyRobotGrowth:
    def test_robot_levels_up(self, tmp_path):
        """Verify the robot levels up after enough interactions."""
        robot = BabyRobot(brain_path=str(tmp_path / "brain.json"))
        # Teaching gives 5 points each; level 2 requires 5 points
        robot.chat("教我:a:b")
        assert robot.level >= 2

    def test_level_up_message_in_response(self, tmp_path):
        robot = BabyRobot(brain_path=str(tmp_path / "brain.json"))
        # First teach command earns 5 points → triggers level-up message
        response = robot.chat("教我:a:b")
        assert "升级" in response or "等级" in response or "🎉" in response

    def test_persistence_across_instances(self, tmp_path):
        path = str(tmp_path / "brain.json")
        r1 = BabyRobot(brain_path=path)
        r1.chat("你好")
        count1 = r1.interaction_count

        r2 = BabyRobot(brain_path=path)
        assert r2.interaction_count == count1
