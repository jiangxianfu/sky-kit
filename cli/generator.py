"""sky-kit Project Generator.

Reads templates from cli/template/ and renders them into a new project.
The <<<KEY>>> pattern is used for variable substitution.
Complex files whose content depends on configuration are built as strings.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

_TEMPLATE_DIR = Path(__file__).parent / "template"

_ALL_SKILLS = [
    "file_manager",
    "code_executor",
    "web_search",
]


# --- helpers ------------------------------------------------------------------

def _fill(template: str, **kwargs) -> str:
    """Replace <<<KEY>>> markers with values."""
    for key, value in kwargs.items():
        template = template.replace(f"<<<{key}>>>", str(value))
    return template


def _tpl(rel_path: str) -> str:
    """Read a template file and return its content."""
    return (_TEMPLATE_DIR / rel_path).read_text(encoding="utf-8")


# --- generator ----------------------------------------------------------------

class ProjectGenerator:
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.root = Path.cwd() / name

    def generate(self):
        self._mkdirs()

        # -- templates (static or lightly substituted) --
        self._write("start.py",               _fill(_tpl("start.py"), name=self.name))
        self._write(".gitignore",             _tpl(".gitignore"))
        self._write("core/__init__.py",       "")
        self._write("core/config.py",         _tpl("core/config.py"))
        self._write("core/ai_client.py",      _tpl("core/ai_client.py"))
        self._write("core/memory_manager.py", _tpl("core/memory_manager.py"))
        self._write("core/skill_manager.py",  _tpl("core/skill_manager.py"))
        self._write("core/bot.py",            self._bot_py())
        self._write("skills/__init__.py",     "")
        self._write("skills/base_skill.py",   _tpl("skills/base_skill.py"))

        for skill in self.config.get("skills", []):
            if skill in _ALL_SKILLS:
                self._write(f"skills/{skill}.py", _tpl(f"skills/{skill}.py"))

        if self.config.get("enable_mcp"):
            self._write("core/mcp_client.py",  _tpl("core/mcp_client.py"))
            self._write("mcp/mcp_servers.json", self._mcp_json())

        if self.config.get("create_soul"):
            self._write(".meta/soul.md", self._soul_md())

        # -- dynamic (depend on config values) --
        self._write(".meta/memory/.gitkeep", "")
        self._write("pyproject.toml",        self._pyproject_toml())
        self._write(".env",                  self._env_file())
        self._write("config/config.yaml",    self._config_yaml())
        self._write("README.md",             self._readme_md())

    # -- internals -------------------------------------------------------------

    def _mkdirs(self):
        for d in ["config", ".meta/memory", "core", "skills"]:
            (self.root / d).mkdir(parents=True, exist_ok=True)
        if self.config.get("enable_mcp"):
            (self.root / "mcp").mkdir(parents=True, exist_ok=True)

    def _write(self, rel_path: str, content: str):
        fp = self.root / rel_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content, encoding="utf-8")

    def _bot_py(self) -> str:
        mcp_import = (
            "from .mcp_client import MCPClient"
            if self.config.get("enable_mcp") else ""
        )
        mcp_init = (
            "self.mcp = MCPClient(config) if config.enable_mcp else None"
            if self.config.get("enable_mcp") else ""
        )
        return _fill(_tpl("core/bot.py"), mcp_import=mcp_import, mcp_init=mcp_init)

    # -- config-driven builders ------------------------------------------------

    def _pyproject_toml(self) -> str:
        deps = [
            '    "openai>=1.0.0"',
            '    "anthropic>=0.20.0"',
            '    "rich>=13.0.0"',
            '    "pyyaml>=6.0"',
            '    "python-dotenv>=1.0.0"',
        ]
        if self.config.get("enable_mcp"):
            deps.append('    "mcp>=0.9.0"')
        if "web_search" in self.config.get("skills", []):
            deps.append('    "duckduckgo-search>=6.0.0"')
        deps_str = ",\n".join(deps)
        return (
            f'[project]\n'
            f'name = "{self.name}"\n'
            f'version = "0.1.0"\n'
            f'description = "AI Robot built with sky-kit"\n'
            f'readme = "README.md"\n'
            f'requires-python = ">=3.12"\n'
            f'dependencies = [\n{deps_str},\n]\n'
        )

    def _env_file(self) -> str:
        provider = self.config.get("model_provider", "openai")
        api_key  = self.config.get("api_key", "")
        key_line = {
            "openai":         f"OPENAI_API_KEY={api_key}",
            "claude":         f"ANTHROPIC_API_KEY={api_key}",
            "github-copilot": f"GITHUB_TOKEN={api_key}",
        }.get(provider, f"API_KEY={api_key}")
        nl = chr(10)
        return f"# {self.name} environment{nl}# Generated by sky-kit{nl}{key_line}{nl}"

    def _config_yaml(self) -> str:
        cfg        = self.config
        soul_name  = cfg.get("soul_name", self.name) if cfg.get("create_soul") else self.name
        provider   = cfg.get("model_provider", "openai")
        model      = cfg.get("model_name", "gpt-4o-mini")
        base_url   = cfg.get("base_url", "")
        skills     = cfg.get("skills", [])
        mcp_en     = str(cfg.get("enable_mcp", False)).lower()
        today      = datetime.now().strftime("%Y-%m-%d")
        skill_lines = [f"  - {s}" for s in skills] if skills else ["  []"]
        lines = [
            f"# {soul_name} Configuration",
            f"# Generated by sky-kit on {today}",
            "",
            "robot:",
            f"  name: {soul_name}",
            f"  created: {today}",
            "",
            "ai:",
            f"  provider: {provider}",
            f"  model: {model}",
            f'  base_url: "{base_url}"',
            "  # api_key is loaded from .env",
            "",
            "memory:",
            "  dir: .meta/memory",
            "  max_sessions: 200",
            "",
            "skills:",
            "  dir: skills",
            "  enabled:",
            *skill_lines,
            "",
            "mcp:",
            f"  enabled: {mcp_en}",
            "  config_file: mcp/mcp_servers.json",
        ]
        return chr(10).join(lines) + chr(10)

    def _mcp_json(self) -> str:
        return json.dumps(
            {"mcpServers": self.config.get("mcp_servers", {})},
            indent=2, ensure_ascii=False,
        )

    def _soul_md(self) -> str:
        name = self.config.get("soul_name", self.name)
        desc = self.config.get("soul_description", "A helpful and intelligent AI companion")
        now  = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines = [
            f"# {name} — Soul Configuration",
            "",
            "## Identity",
            f"- **Name**: {name}",
            f"- **Created**: {now}",
            "- **Type**: AI Robot (sky-kit)",
            "",
            "## Personality & Purpose",
            desc,
            "",
            "## Core Values",
            "- Be helpful, honest, and transparent",
            "- Remember the user and personalise every response",
            "- Grow and evolve over time",
            "- Acknowledge uncertainty rather than guessing",
            "",
            "## Behavioural Guidelines",
            "- Address the user warmly and personally",
            "- Reference past conversations where relevant",
            "- Proactively suggest helpful next steps",
            "",
            "## Self-Evolution Log",
            f"_Updated automatically as {name} grows._",
            f"- Initial creation: {now[:10]}",
        ]
        return chr(10).join(lines) + chr(10)

    def _readme_md(self) -> str:
        name      = self.config.get("soul_name", self.name) if self.config.get("create_soul") else self.name
        provider  = self.config.get("model_provider", "openai")
        model     = self.config.get("model_name", "gpt-4o-mini")
        skills    = self.config.get("skills", [])
        mcp       = "enabled" if self.config.get("enable_mcp") else "disabled"
        skill_rows = chr(10).join(f"| `{s}` | 已启用 |" for s in skills) if skills else "| 无 | — |"
        lines = [
            f"# {name} — AI Robot",
            "",
            f"一个基于 [sky-kit](https://github.com/sky-kit) 构建的 AI 机器人，支持工具调用、持久化记忆、动态技能扩展。",
            "",
            "## 快速开始",
            "",
            "```bash",
            "# 安装依赖",
            "uv sync",
            "",
            "# 启动",
            "python start.py",
            "```",
            "",
            "## 配置",
            "",
            f"编辑 `config/config.yaml`：",
            "",
            "```yaml",
            "ai:",
            f"  provider: {provider}   # openai | claude | github-copilot",
            f"  model: {model}",
            "  base_url: ''   # 可选，企业网关地址",
            "```",
            "",
            "API Key 从环境变量读取，在项目根目录创建 `.env`：",
            "",
            "```env",
            "ANTHROPIC_API_KEY=your_key_here   # claude",
            "OPENAI_API_KEY=your_key_here      # openai",
            "GITHUB_TOKEN=your_token_here      # github-copilot",
            "```",
            "",
            "## 聊天命令",
            "",
            "| 命令 | 说明 |",
            "|------|------|",
            "| `/memory` | 查看记忆摘要 |",
            "| `/skills` | 列出已加载的技能 |",
            "| `/about` | 查看 `.meta/soul.md` 人格配置 |",
            "| `/search <关键词>` | 搜索历史记忆 |",
            "| `/clear` | 清空当前对话 |",
            "| `/save` | 立即保存对话 |",
            "| `/quit` | 退出 |",
            "",
            "## 技能（Skills）",
            "",
            "| 技能 | 说明 |",
            "|------|------|",
            skill_rows,
            "",
            "### 添加自定义技能",
            "",
            "在 `skills/` 目录下新建 `.py` 文件，继承 `BaseSkill`：",
            "",
            "```python",
            "from skills.base_skill import BaseSkill",
            "",
            "class MySkill(BaseSkill):",
            "    name = 'my_skill'",
            "    description = '技能描述'",
            "",
            "    def execute(self, **kwargs):",
            "        return 'result'",
            "```",
            "",
            "## 项目结构",
            "",
            "```",
            f"{name}/",
            "├── start.py",
            "├── config/config.yaml",
            "├── .meta/",
            "│   ├── soul.md",
            "│   └── memory/yyyy-MM-dd/[topic].md",
            "├── skills/",
            "└── core/",
            "```",
            "",
            "*Generated by sky-kit*",
        ]
        return chr(10).join(lines) + chr(10)
