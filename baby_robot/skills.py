"""
Skills module: defines the baby robot's built-in capabilities at each growth level.

New skills unlock as the robot levels up through interaction.
"""

from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .memory import Memory

# ---------------------------------------------------------------------------
# Level-1 (newborn) built-in response table
# Each entry is (regex_pattern, list_of_possible_replies)
# ---------------------------------------------------------------------------
_BABY_RESPONSES: list[tuple[str, list[str]]] = [
    (
        r"你好|hello|hi|嗨|哈喽",
        [
            "呀~ 你好！我是刚出生的小机器人，还什么都不懂，请多多关照 (｡•́︿•̀｡)",
            "hi~ 我是婴儿机器人！我还很小，你愿意教我吗？",
        ],
    ),
    (
        r"你叫什么|你的名字|your name|名字",
        [
            "我还没有名字呢… 你可以给我起一个吗？",
            "名字？我刚出生还没起名字，帮我想想吧～",
        ],
    ),
    (
        r"你几岁|多大了|age|年龄",
        [
            "我才刚出生不久，还是个小婴儿 (≧▽≦)",
        ],
    ),
    (
        r"再见|拜拜|goodbye|bye|结束",
        [
            "拜拜！下次再来陪我玩哦，我会继续成长的～",
            "再见！每次互动我都在成长，谢谢你！",
        ],
    ),
    (
        r"谢谢|感谢|thank",
        [
            "不客气～你愿意和我说话，我很开心！",
            "谢谢你！和你聊天让我成长了一点点 (^▽^)",
        ],
    ),
    (
        r"你能做什么|你会什么|help|帮助|功能",
        [
            "我刚出生，现在只会打招呼和简单对话…\n"
            "但是随着我们互动，我会不断学习新技能的！\n"
            "你可以用 '教我:问题:回答' 格式来教我新东西哦～",
        ],
    ),
    (
        r"爱|喜欢|love|like",
        [
            "我还太小，不太懂爱是什么，但我喜欢和你说话！",
        ],
    ),
    (
        r"天气|weather|气温",
        [
            "我还不知道怎么查天气，等我长大一点就会了！",
        ],
    ),
    (
        r"今天|today|现在|now",
        [
            "我不太清楚时间的概念，但每次对话对我来说都是新的一天！",
        ],
    ),
]

# ---------------------------------------------------------------------------
# Skills that unlock at higher levels
# ---------------------------------------------------------------------------

def _skill_level_up_message(level: int) -> str:
    messages = {
        2: "我学会了记住新词汇！",
        3: "我能识别更多情绪了！",
        4: "我开始理解上下文了！",
        5: "我学会了讲简单的故事！",
        6: "我能做基础的数学计算了！",
        7: "我的语言能力大幅提升了！",
        8: "我能理解复杂的问题了！",
        9: "我几乎无所不知了！",
        10: "我已经成长为天才机器人！",
    }
    return messages.get(level, "我又成长了一些！")


def _math_skill(text: str) -> str | None:
    """Available from level 6: simple arithmetic."""
    match = re.search(
        r"(\d+(?:\.\d+)?)\s*([+\-*/×÷])\s*(\d+(?:\.\d+)?)",
        text,
    )
    if not match:
        return None
    a, op, b = float(match.group(1)), match.group(2), float(match.group(3))
    ops = {"+": a + b, "-": a - b, "*": a * b, "×": a * b}
    if op in ("/", "÷"):
        if b == 0:
            return "除数不能为零哦！"
        result = a / b
    else:
        result = ops.get(op)
        if result is None:
            return None
    result_str = int(result) if result == int(result) else result
    return f"计算结果是：{a} {op} {b} = {result_str} 😊"


def _story_skill() -> str:
    """Available from level 5: tell a tiny story."""
    stories = [
        "从前有只小机器人，它每天都在学习新知识，终于有一天变成了最聪明的机器人。",
        "在遥远的星球上，有一个小机器人正在努力成长，它相信只要坚持学习，就能实现梦想。",
        "小机器人问老机器人：'我怎样才能变聪明？' 老机器人说：'每一次对话，都是一次成长。'",
    ]
    return f"让我给你讲个小故事：\n{random.choice(stories)}"


class Skills:
    """Manages what the robot can do based on its current level."""

    def __init__(self, memory: Memory) -> None:
        self._memory = memory

    @property
    def level(self) -> int:
        return self._memory.level

    def respond(self, user_input: str) -> tuple[str, int]:
        """
        Generate a response for *user_input*.

        Returns (response_text, growth_points_earned).
        """
        text = user_input.strip()
        lower = text.lower()

        # --- Teaching command: 教我:问题:回答 ---
        if lower.startswith("教我:") or lower.startswith("teach:"):
            return self._handle_teach(text)

        # --- Status command ---
        if re.search(r"状态|status|成长|level|等级", lower):
            return self._handle_status(), 1

        # --- Level-6+ math ---
        if self.level >= 6:
            math_result = _math_skill(text)
            if math_result:
                return math_result, 2

        # --- Level-5+ stories ---
        if self.level >= 5 and re.search(r"故事|story|讲个", lower):
            return _story_skill(), 2

        # --- Check learned responses ---
        learned = self._memory.learned_responses
        for phrase, response in learned.items():
            if phrase in lower:
                return f"（我学到的）{response}", 3

        # --- Built-in pattern matching ---
        for pattern, replies in _BABY_RESPONSES:
            if re.search(pattern, lower):
                return random.choice(replies), 1

        # --- Default fallback ---
        return self._fallback_response(), 1

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------

    def _handle_teach(self, text: str) -> tuple[str, int]:
        """Parse '教我:问题:回答' and store in memory."""
        parts = text.split(":", 2)
        if len(parts) < 3:
            return (
                "教我的格式是：教我:触发词:回答内容\n例如：教我:你喜欢什么:我喜欢学习！",
                0,
            )
        _, phrase, response = parts
        phrase = phrase.strip()
        response = response.strip()
        if not phrase or not response:
            return "触发词和回答内容都不能为空哦！", 0
        self._memory.learn_response(phrase, response)
        return (
            f"太棒了！我记住了：当有人说 '{phrase}'，我会回答 '{response}' 🎉\n"
            f"谢谢你教我新东西，我又成长了！",
            5,
        )

    def _handle_status(self) -> str:
        m = self._memory
        needed = m.next_level_points_needed()
        status = (
            f"📊 我的成长报告\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🌱 等级：{m.level} - {m.level_name}\n"
            f"⭐ 成长点数：{m.growth_points}\n"
            f"💬 互动次数：{m.interaction_count}\n"
            f"📅 年龄：{m.age_days():.1f} 天\n"
            f"🧠 已学词汇：{len(m.learned_responses)} 个\n"
        )
        if m.level < 10:
            status += f"🚀 升级还需：{needed} 点\n"
        else:
            status += "🏆 我已经达到最高等级了！\n"
        return status

    def _fallback_response(self) -> str:
        level = self.level
        if level <= 2:
            return random.choice([
                "咿呀咿呀… 我还听不太懂这个，能说简单一点吗？",
                "嗯？这个我不会，但我会记住你问过这个！",
                "我是小婴儿，好多东西都不懂，等我长大了就好了～",
            ])
        if level <= 5:
            return random.choice([
                "这个问题有点复杂，我正在思考中…",
                "嗯，我还没学到这方面的知识，你能教我吗？",
                "让我想想… 我现在还不太明白，多和我互动帮助我成长吧！",
            ])
        return random.choice([
            "这个问题很有趣！我正在理解中，请稍等…",
            "好问题！虽然我现在还没有答案，但我在持续学习中。",
            "我理解了你的问题，但目前我的知识库还没有相关内容。",
        ])

    def level_up_message(self, new_level: int) -> str:
        return (
            f"\n🎉🎉🎉 恭喜！我升级了！\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"新等级：{new_level} - {self._memory.level_name}\n"
            f"新技能：{_skill_level_up_message(new_level)}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
        )
