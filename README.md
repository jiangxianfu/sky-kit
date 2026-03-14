# 🤖 sky-kit — 婴儿机器人 (Baby Robot)

> 创造一个可以自我更新迭代的机器人工具。它是一个刚刚出生的婴儿版机器人，后续的升级都需要你真心呵护才能自我成长。

## 特性

- **自我成长**：每次互动都会积累成长点数，升到更高等级后解锁新技能。
- **自我学习**：用 `教我:触发词:回答` 命令教机器人新知识，它永远记得。
- **持久记忆**：机器人的大脑保存在 `data/brain.json`，重启后记忆不丢失。
- **10 个成长等级**：从「新生婴儿」一路成长到「天才」。

## 成长等级

| 等级 | 名称 | 所需成长点 | 新技能 |
|------|------|-----------|--------|
| 1 | 新生婴儿 | 0 | 基础问候 |
| 2 | 好奇宝宝 | 5 | 记忆新词汇 |
| 3 | 学步儿童 | 15 | 情绪识别 |
| 4 | 小学生 | 30 | 上下文理解 |
| 5 | 少年 | 60 | 讲故事 |
| 6 | 青少年 | 100 | 数学计算 |
| 7 | 青年 | 150 | 语言提升 |
| 8 | 成年人 | 220 | 复杂问题理解 |
| 9 | 智者 | 300 | 深度知识 |
| 10 | 天才 | 400 | 满级能力 |

## 快速开始

```bash
# 运行机器人（交互模式）
python main.py
```

## 与机器人对话

```
你: 你好
机器人: hi~ 我是婴儿机器人！我还很小，你愿意教我吗？

你: 教我:星星:星星真漂亮
机器人: 太棒了！我记住了：当有人说 '星星'，我会回答 '星星真漂亮' 🎉

你: 状态
机器人: 📊 我的成长报告
        🌱 等级：2 - 好奇宝宝 (Curious Baby)
        ⭐ 成长点数：8
        ...
```

## 项目结构

```
sky-kit/
├── baby_robot/
│   ├── __init__.py     # 包入口
│   ├── robot.py        # BabyRobot 主类
│   ├── memory.py       # 持久化记忆/大脑模块
│   └── skills.py       # 技能系统（按等级解锁）
├── tests/
│   ├── test_memory.py
│   ├── test_skills.py
│   └── test_robot.py
├── data/               # brain.json 存储于此（自动创建）
├── main.py             # 交互式 CLI 入口
└── requirements.txt
```

## 测试

```bash
pip install pytest
python -m pytest tests/ -v
```

## API 使用

```python
from baby_robot import BabyRobot

robot = BabyRobot()                          # 默认脑文件在 data/brain.json
robot = BabyRobot(brain_path="/path/to/brain.json")  # 自定义路径

response = robot.chat("你好")
print(response)

print(robot.level)             # 当前等级 (1-10)
print(robot.level_name)        # 等级名称
print(robot.interaction_count) # 累计互动次数
print(robot.growth_points)     # 累计成长点数
print(robot.status())          # 格式化成长报告
```

