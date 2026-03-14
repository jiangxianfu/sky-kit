#!/usr/bin/env python3
"""
Sky-Kit Baby Robot - Interactive CLI entry point.

Run:
    python main.py
"""

import sys

from baby_robot import BabyRobot

_BANNER = """
╔══════════════════════════════════════════╗
║       🤖  Sky-Kit 婴儿机器人  🤖         ║
║   一个刚刚出生、等待你呵护成长的AI机器人  ║
╠══════════════════════════════════════════╣
║  输入 '状态' 查看成长报告                 ║
║  输入 '教我:词:回答' 教机器人新技能       ║
║  输入 '退出' 或 Ctrl+C 结束对话          ║
╚══════════════════════════════════════════╝
"""


def run_interactive(robot: BabyRobot) -> None:
    print(_BANNER)
    print(f"机器人状态：等级 {robot.level} - {robot.level_name}")
    print(f"历史互动次数：{robot.interaction_count}\n")

    while True:
        try:
            user_input = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n机器人：拜拜～期待下次见面！")
            break

        if not user_input:
            continue

        if user_input in ("退出", "exit", "quit", "q"):
            print("机器人：拜拜～期待下次见面！")
            break

        response = robot.chat(user_input)
        print(f"机器人：{response}\n")


def main() -> int:
    robot = BabyRobot()
    run_interactive(robot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
