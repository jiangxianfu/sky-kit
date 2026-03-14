"""Tests for baby_robot.memory module."""

import os
import json
import pytest
import time

from baby_robot.memory import Memory


@pytest.fixture
def brain_file(tmp_path):
    return str(tmp_path / "brain.json")


class TestMemoryInit:
    def test_creates_brain_file_on_first_use(self, brain_file):
        _ = Memory(brain_file)
        assert os.path.exists(brain_file)

    def test_default_level_is_one(self, brain_file):
        m = Memory(brain_file)
        assert m.level == 1

    def test_default_interaction_count_is_zero(self, brain_file):
        m = Memory(brain_file)
        assert m.interaction_count == 0

    def test_birth_time_set(self, brain_file):
        before = time.time()
        m = Memory(brain_file)
        after = time.time()
        assert before <= m._data["birth_time"] <= after

    def test_load_existing_brain(self, brain_file):
        m1 = Memory(brain_file)
        m1.record_interaction()
        m1.record_interaction()

        m2 = Memory(brain_file)
        assert m2.interaction_count == 2


class TestMemoryInteractions:
    def test_record_interaction_increments(self, brain_file):
        m = Memory(brain_file)
        m.record_interaction()
        assert m.interaction_count == 1
        m.record_interaction()
        assert m.interaction_count == 2

    def test_growth_points_accumulate(self, brain_file):
        m = Memory(brain_file)
        m.add_growth_points(3)
        assert m.growth_points == 3
        m.add_growth_points(2)
        assert m.growth_points == 5

    def test_level_up_at_threshold(self, brain_file):
        m = Memory(brain_file)
        # Level 2 requires 5 points
        levelled = m.add_growth_points(5)
        assert levelled is True
        assert m.level == 2

    def test_no_level_up_below_threshold(self, brain_file):
        m = Memory(brain_file)
        levelled = m.add_growth_points(4)
        assert levelled is False
        assert m.level == 1

    def test_level_does_not_exceed_10(self, brain_file):
        m = Memory(brain_file)
        m.add_growth_points(10000)
        assert m.level == 10

    def test_next_level_points_needed(self, brain_file):
        m = Memory(brain_file)
        # Fresh start: need 5 points to reach level 2
        assert m.next_level_points_needed() == 5
        m.add_growth_points(3)
        assert m.next_level_points_needed() == 2

    def test_next_level_points_needed_at_max(self, brain_file):
        m = Memory(brain_file)
        m.add_growth_points(10000)
        assert m.next_level_points_needed() == 0


class TestMemoryLearning:
    def test_learn_and_retrieve_response(self, brain_file):
        m = Memory(brain_file)
        m.learn_response("月亮", "月亮真美啊")
        assert "月亮" in m.learned_responses
        assert m.learned_responses["月亮"] == "月亮真美啊"

    def test_learn_normalises_phrase_to_lowercase(self, brain_file):
        m = Memory(brain_file)
        m.learn_response("Hello", "Hi there!")
        assert "hello" in m.learned_responses

    def test_topic_tracking(self, brain_file):
        m = Memory(brain_file)
        m.record_topic("天气")
        assert "天气" in m.topics_discussed

    def test_duplicate_topics_not_added(self, brain_file):
        m = Memory(brain_file)
        m.record_topic("机器人")
        m.record_topic("机器人")
        assert m.topics_discussed.count("机器人") == 1


class TestMemoryPersistence:
    def test_data_persists_to_disk(self, brain_file):
        m1 = Memory(brain_file)
        m1.add_growth_points(5)
        m1.learn_response("test", "reply")

        m2 = Memory(brain_file)
        assert m2.growth_points == 5
        assert "test" in m2.learned_responses

    def test_level_name_changes_with_level(self, brain_file):
        m = Memory(brain_file)
        name_l1 = m.level_name
        m.add_growth_points(5)  # level up to 2
        name_l2 = m.level_name
        assert name_l1 != name_l2
