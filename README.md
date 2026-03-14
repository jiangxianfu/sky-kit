# sky-kit

> AI 机器人项目初始化工具 — 基于 Python 构建。

一条命令，创建一个完整的、可交互的 AI 机器人项目。

---

## 本地开发启动

```bash
# 1. 克隆仓库
git clone <本仓库地址>
cd sky-kit

# 2. 安装依赖（uv 会自动创建虚拟环境并安装所有依赖，需要 Python 3.12+）
uv sync

# 3. 运行单元测试（验证环境）
uv run pytest tests/ --cov=cli --cov-report=term-missing

# 4. 使用 CLI 创建第一个机器人项目
uv run sky-kit init sky001
```

---

## 安装（直接使用，无需开发模式）

```bash
git clone <本仓库地址>
cd sky-kit
uv sync
```

安装完成后，可通过 `uv run sky-kit` 使用命令，或激活虚拟环境后直接使用 `sky-kit`：

```bash
# 方式一：通过 uv run 调用（推荐）
uv run sky-kit init sky001

# 方式二：激活虚拟环境后直接调用
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
sky-kit init sky001
```

---

## 快速开始

```bash
# 交互向导模式（推荐）
uv run sky-kit init sky001

# 创建完成后运行机器人
cd sky001
uv sync
uv run python start.py
```

---

## 命令列表

| 命令 | 说明 |
|------|------|
| `sky-kit init [NAME]` | 创建新的机器人项目（交互向导） |
| `sky-kit --version` | 显示版本号 |

### `sky-kit init` 向导步骤

向导只需回答两个问题：

1. **AI 提供商** — 选择 OpenAI / Claude / GitHub Copilot，并输入模型名称与 Base URL
2. **API Key** — 输入对应的 API 密钥

技能、MCP、调度器等功能均以默认配置自动生成，无需手动配置。

---

## 生成的项目结构

```
sky001/
├── start.py              ← 启动入口：python start.py
├── .meta/                ← 灵魂、记忆与身份（隐藏目录）
│   ├── soul.md           ← 机器人身份文件（运行时自动创建并持续进化）
│   └── memory/           ← 对话记忆，按 yyyy-MM-dd/[主题].md 存储
├── .env                  ← API 密钥（已加入 .gitignore）
├── requirements.txt
├── config/
│   └── config.yaml       ← 全部配置项
├── skills/               ← 技能插件目录
│   ├── base_skill.py
│   ├── file_manager.py
│   ├── code_executor.py
│   ├── web_search.py
│   ├── scheduler_skill.py
│   └── self_modifier.py
└── core/                 ← 机器人核心框架（一般无需修改）
    ├── bot.py
    ├── config.py
    ├── ai_client.py
    ├── memory_manager.py
    ├── scheduler.py
    └── skill_manager.py
```

---

## 首次运行

首次执行 `uv run python start.py` 时，如果 `.meta/soul.md` 不存在，机器人会自动询问：

1. **你想叫我什么名字？** — 设置机器人名称
2. **你希望我是一个怎样的伙伴？** — 设置性格与定位
3. **有哪些专注领域？** — 例如：编程、写作、研究

回答将保存到 `.meta/soul.md`，并作为 AI 系统提示词持续使用和进化。

---

## 对话内置命令

在机器人交互界面中可使用以下指令：

| 命令 | 说明 |
|------|------|
| `/memory` | 显示近期记忆摘要 |
| `/skills` | 列出已激活的技能 |
| `/about` | 显示 `.meta/soul.md` 内容 |
| `/search <关键词>` | 搜索历史对话记忆 |
| `/scheduler` | 查看后台定时任务 |
| `/clear` | 清空当前对话 |
| `/save` | 立即保存当前对话到记忆 |
| `/quit` | 退出 |

---

## 支持的 AI 提供商

| 提供商 | SDK | 说明 |
|--------|-----|------|
| **OpenAI** | `openai` | gpt-4o、gpt-4o-mini、o3-mini 等 |
| **Anthropic Claude** | `anthropic` | claude-3-5-sonnet、claude-3-haiku 等 |
| **GitHub Copilot** | `openai` | 使用 GitHub Models API（`https://models.inference.ai.azure.com`），需要 GitHub PAT |

---

## MCP 工具服务器

在 `config/config.yaml` 中启用 MCP，可为机器人接入外部工具：

- **filesystem** — 通过 `@modelcontextprotocol/server-filesystem` 读写本地文件
- **brave-search** — 通过 `@modelcontextprotocol/server-brave-search` 进行网页搜索
- **github** — 通过 `@modelcontextprotocol/server-github` 访问 GitHub API
- **sqlite** — 通过 `@modelcontextprotocol/server-sqlite` 操作本地数据库

需要安装 Node.js（`npx`）并执行 `uv add mcp`。

---

## 自定义

### 修改机器人性格

编辑项目中的 `.meta/soul.md`。机器人也会随着对话自动更新该文件，持续进化。

### 添加自定义技能

在 `skills/` 目录下新建 `my_skill.py`，继承 `BaseSkill`：

```python
from skills.base_skill import BaseSkill

class MySkill(BaseSkill):
    name = 'my_skill'
    description = '这个技能做一些有用的事情。'

    def execute(self, **kwargs):
        return '来自自定义技能的问候！'
```

然后在 `config/config.yaml` 的 `skills.enabled` 中添加 `my_skill`。

### 切换 AI 模型

编辑 `config/config.yaml`：

```yaml
ai:
  provider: claude
  model: claude-3-5-sonnet-20241022
```

---

## 记忆系统

每次对话结束后自动保存至 `.meta/memory/<日期>/<主题>.md`，以 Markdown 格式存储。

使用 `/search <关键词>` 可跨历史会话全文搜索。

---

## 环境要求

- [uv](https://docs.astral.sh/uv/) ≥ 0.4（Python 包管理器，会自动管理 Python 3.12+ 环境）
- `click`、`rich`、`pyyaml`、`python-dotenv`、`schedule`
- `openai`（用于 OpenAI / GitHub Copilot）
- `anthropic`（用于 Claude）
- `mcp`（可选，用于 MCP 工具服务器）
- Node.js / npx（可选，用于 MCP）

---

## 开源协议

MIT
