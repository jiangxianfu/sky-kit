"""Unit tests for cli/generator.py — targeting ≥80 % coverage."""
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from cli.generator import (
    _ALL_SKILLS,
    _TEMPLATE_DIR,
    ProjectGenerator,
    _fill,
    _tpl,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

MINIMAL_CONFIG: dict = {
    "model_provider": "openai",
    "model_name": "gpt-4o-mini",
    "api_key": "sk-test",
    "base_url": "",
    "enable_mcp": False,
    "mcp_servers": {},
    "skills": [],
    "create_soul": False,
    "enable_scheduler": True,
}


def make_gen(tmp_path: Path, name: str = "testbot", extra: dict | None = None) -> ProjectGenerator:
    """Create a ProjectGenerator whose root lives inside tmp_path."""
    cfg = {**MINIMAL_CONFIG, **(extra or {})}
    gen = ProjectGenerator(name, cfg)
    gen.root = tmp_path / name          # redirect away from cwd
    return gen


# ---------------------------------------------------------------------------
# _fill()
# ---------------------------------------------------------------------------

class TestFill:
    def test_single_replacement(self):
        assert _fill("Hello <<<NAME>>>!", NAME="World") == "Hello World!"

    def test_multiple_keys(self):
        result = _fill("<<<A>>> + <<<B>>>", A="1", B="2")
        assert result == "1 + 2"

    def test_no_match_leaves_template_unchanged(self):
        tpl = "no markers here"
        assert _fill(tpl, FOO="bar") == tpl

    def test_multiple_occurrences_replaced(self):
        result = _fill("<<<X>>> <<<X>>>", X="hi")
        assert result == "hi hi"

    def test_empty_template(self):
        assert _fill("", KEY="val") == ""

    def test_value_coerced_to_str(self):
        result = _fill("num=<<<N>>>", N=42)
        assert result == "num=42"


# ---------------------------------------------------------------------------
# _tpl()
# ---------------------------------------------------------------------------

class TestTpl:
    def test_reads_existing_template_start(self):
        content = _tpl("start.py")
        assert len(content) > 0

    def test_reads_existing_template_core(self):
        content = _tpl("core/config.py")
        assert len(content) > 0

    def test_reads_existing_template_skill(self):
        content = _tpl("skills/base_skill.py")
        assert len(content) > 0

    def test_missing_file_raises(self):
        with pytest.raises(FileNotFoundError):
            _tpl("does_not_exist.py")

    def test_returns_correct_path(self):
        """_tpl path is relative to _TEMPLATE_DIR."""
        expected = (_TEMPLATE_DIR / "start.py").read_text(encoding="utf-8")
        assert _tpl("start.py") == expected


# ---------------------------------------------------------------------------
# ProjectGenerator.__init__
# ---------------------------------------------------------------------------

class TestProjectGeneratorInit:
    def test_attributes(self, tmp_path):
        gen = make_gen(tmp_path, "mybot")
        assert gen.name == "mybot"
        assert gen.config == {**MINIMAL_CONFIG}

    def test_root_set_to_redirected_path(self, tmp_path):
        gen = make_gen(tmp_path, "mybot")
        assert gen.root == tmp_path / "mybot"


# ---------------------------------------------------------------------------
# _write  /  _mkdirs
# ---------------------------------------------------------------------------

class TestWriteAndMkdirs:
    def test_write_creates_file(self, tmp_path):
        gen = make_gen(tmp_path)
        gen._mkdirs()
        gen._write("hello.txt", "world")
        assert (gen.root / "hello.txt").read_text() == "world"

    def test_write_creates_nested_dirs(self, tmp_path):
        gen = make_gen(tmp_path)
        gen._write("deep/nested/file.txt", "content")
        assert (gen.root / "deep/nested/file.txt").read_text() == "content"

    def test_mkdirs_creates_standard_directories(self, tmp_path):
        gen = make_gen(tmp_path)
        gen._mkdirs()
        for d in ["config", ".meta/memory", "core", "skills"]:
            assert (gen.root / d).is_dir()

    def test_mkdirs_creates_mcp_dir_when_enabled(self, tmp_path):
        gen = make_gen(tmp_path, extra={"enable_mcp": True})
        gen._mkdirs()
        assert (gen.root / "mcp").is_dir()

    def test_mkdirs_no_mcp_dir_when_disabled(self, tmp_path):
        gen = make_gen(tmp_path)
        gen._mkdirs()
        assert not (gen.root / "mcp").exists()


# ---------------------------------------------------------------------------
# _req_txt
# ---------------------------------------------------------------------------

class TestReqTxt:
    def test_base_packages_present(self, tmp_path):
        gen = make_gen(tmp_path)
        txt = gen._req_txt()
        for pkg in ["openai", "anthropic", "rich", "pyyaml", "python-dotenv", "schedule"]:
            assert pkg in txt

    def test_ends_with_newline(self, tmp_path):
        gen = make_gen(tmp_path)
        assert gen._req_txt().endswith("\n")

    def test_mcp_package_included_when_enabled(self, tmp_path):
        gen = make_gen(tmp_path, extra={"enable_mcp": True})
        assert "mcp>=" in gen._req_txt()

    def test_mcp_package_absent_when_disabled(self, tmp_path):
        gen = make_gen(tmp_path)
        assert "mcp>=" not in gen._req_txt()

    def test_duckduckgo_included_for_web_search(self, tmp_path):
        gen = make_gen(tmp_path, extra={"skills": ["web_search"]})
        assert "duckduckgo-search" in gen._req_txt()

    def test_duckduckgo_absent_without_web_search(self, tmp_path):
        gen = make_gen(tmp_path, extra={"skills": ["file_manager"]})
        assert "duckduckgo-search" not in gen._req_txt()


# ---------------------------------------------------------------------------
# _env_file
# ---------------------------------------------------------------------------

class TestEnvFile:
    def test_openai_key_line(self, tmp_path):
        gen = make_gen(tmp_path, extra={"model_provider": "openai", "api_key": "sk-abc"})
        env = gen._env_file()
        assert "OPENAI_API_KEY=sk-abc" in env

    def test_claude_key_line(self, tmp_path):
        gen = make_gen(tmp_path, extra={"model_provider": "claude", "api_key": "sk-ant-xyz"})
        env = gen._env_file()
        assert "ANTHROPIC_API_KEY=sk-ant-xyz" in env

    def test_github_copilot_key_line(self, tmp_path):
        gen = make_gen(tmp_path, extra={"model_provider": "github-copilot", "api_key": "ghp_tok"})
        env = gen._env_file()
        assert "GITHUB_TOKEN=ghp_tok" in env

    def test_unknown_provider_fallback(self, tmp_path):
        gen = make_gen(tmp_path, extra={"model_provider": "custom", "api_key": "mykey"})
        env = gen._env_file()
        assert "API_KEY=mykey" in env

    def test_contains_project_name(self, tmp_path):
        gen = make_gen(tmp_path, name="myrobot")
        env = gen._env_file()
        assert "myrobot" in env

    def test_ends_with_newline(self, tmp_path):
        gen = make_gen(tmp_path)
        assert gen._env_file().endswith("\n")


# ---------------------------------------------------------------------------
# _config_yaml
# ---------------------------------------------------------------------------

FIXED_DATE = "2026-03-13"


class TestConfigYaml:
    @pytest.fixture(autouse=True)
    def _freeze_date(self):
        fake_dt = MagicMock(wraps=datetime)
        fake_dt.now.return_value = datetime(2026, 3, 13, 12, 0, 0)
        with patch("cli.generator.datetime", fake_dt):
            yield

    def test_contains_provider_and_model(self, tmp_path):
        gen = make_gen(tmp_path, extra={"model_provider": "claude", "model_name": "claude-3-5-sonnet"})
        yaml = gen._config_yaml()
        assert "provider: claude" in yaml
        assert "model: claude-3-5-sonnet" in yaml

    def test_robot_name_is_project_name(self, tmp_path):
        gen = make_gen(tmp_path, name="myrobot")
        assert "name: myrobot" in gen._config_yaml()

    def test_soul_name_overrides_robot_name(self, tmp_path):
        gen = make_gen(tmp_path, name="myrobot",
                       extra={"create_soul": True, "soul_name": "Aria"})
        yaml = gen._config_yaml()
        assert "name: Aria" in yaml

    def test_skills_listed(self, tmp_path):
        gen = make_gen(tmp_path, extra={"skills": ["file_manager", "web_search"]})
        yaml = gen._config_yaml()
        assert "- file_manager" in yaml
        assert "- web_search" in yaml

    def test_no_skills_shows_empty_list(self, tmp_path):
        gen = make_gen(tmp_path, extra={"skills": []})
        yaml = gen._config_yaml()
        assert "  []" in yaml

    def test_mcp_enabled_flag(self, tmp_path):
        gen = make_gen(tmp_path, extra={"enable_mcp": True})
        assert "enabled: true" in gen._config_yaml()

    def test_scheduler_disabled_flag(self, tmp_path):
        gen = make_gen(tmp_path, extra={"enable_scheduler": False})
        assert "enabled: false" in gen._config_yaml()

    def test_contains_date(self, tmp_path):
        gen = make_gen(tmp_path)
        assert FIXED_DATE in gen._config_yaml()

    def test_ends_with_newline(self, tmp_path):
        gen = make_gen(tmp_path)
        assert gen._config_yaml().endswith("\n")


# ---------------------------------------------------------------------------
# _mcp_json
# ---------------------------------------------------------------------------

class TestMcpJson:
    def test_empty_servers(self, tmp_path):
        gen = make_gen(tmp_path)
        data = json.loads(gen._mcp_json())
        assert data == {"mcpServers": {}}

    def test_with_servers(self, tmp_path):
        servers = {"my-server": {"command": "node", "args": ["server.js"]}}
        gen = make_gen(tmp_path, extra={"mcp_servers": servers})
        data = json.loads(gen._mcp_json())
        assert data["mcpServers"] == servers

    def test_valid_json(self, tmp_path):
        gen = make_gen(tmp_path)
        assert isinstance(json.loads(gen._mcp_json()), dict)


# ---------------------------------------------------------------------------
# _soul_md
# ---------------------------------------------------------------------------

class TestSoulMd:
    @pytest.fixture(autouse=True)
    def _freeze_date(self):
        fake_dt = MagicMock(wraps=datetime)
        fake_dt.now.return_value = datetime(2026, 3, 13, 12, 0, 0)
        with patch("cli.generator.datetime", fake_dt):
            yield

    def test_contains_soul_name(self, tmp_path):
        gen = make_gen(tmp_path, extra={"soul_name": "Nova"})
        md = gen._soul_md()
        assert "Nova" in md

    def test_defaults_to_project_name(self, tmp_path):
        gen = make_gen(tmp_path, name="botx")
        md = gen._soul_md()
        assert "botx" in md

    def test_contains_creation_date(self, tmp_path):
        gen = make_gen(tmp_path)
        assert "2026-03-13" in gen._soul_md()

    def test_contains_description(self, tmp_path):
        gen = make_gen(tmp_path, extra={"soul_description": "A wise sage AI"})
        assert "A wise sage AI" in gen._soul_md()

    def test_default_description_present(self, tmp_path):
        gen = make_gen(tmp_path)
        assert "helpful" in gen._soul_md().lower()

    def test_ends_with_newline(self, tmp_path):
        gen = make_gen(tmp_path)
        assert gen._soul_md().endswith("\n")


# ---------------------------------------------------------------------------
# _readme_md
# ---------------------------------------------------------------------------

class TestReadmeMd:
    def test_contains_project_name(self, tmp_path):
        gen = make_gen(tmp_path, name="skybot")
        assert "# skybot" in gen._readme_md()

    def test_soul_name_as_title(self, tmp_path):
        gen = make_gen(tmp_path, name="skybot",
                       extra={"create_soul": True, "soul_name": "Aria"})
        assert "# Aria" in gen._readme_md()

    def test_no_skills_shows_none(self, tmp_path):
        gen = make_gen(tmp_path, extra={"skills": []})
        assert "none" in gen._readme_md()

    def test_skills_listed(self, tmp_path):
        gen = make_gen(tmp_path, extra={"skills": ["web_search", "file_manager"]})
        readme = gen._readme_md()
        assert "web_search" in readme
        assert "file_manager" in readme

    def test_mcp_disabled_shown(self, tmp_path):
        gen = make_gen(tmp_path, extra={"enable_mcp": False})
        assert "disabled" in gen._readme_md()

    def test_mcp_enabled_shown(self, tmp_path):
        gen = make_gen(tmp_path, extra={"enable_mcp": True})
        assert "enabled" in gen._readme_md()

    def test_contains_provider_and_model(self, tmp_path):
        gen = make_gen(tmp_path, extra={"model_provider": "claude", "model_name": "claude-3-5-sonnet"})
        readme = gen._readme_md()
        assert "claude" in readme
        assert "claude-3-5-sonnet" in readme

    def test_ends_with_newline(self, tmp_path):
        gen = make_gen(tmp_path)
        assert gen._readme_md().endswith("\n")


# ---------------------------------------------------------------------------
# _bot_py
# ---------------------------------------------------------------------------

class TestBotPy:
    def test_no_mcp_placeholders_empty(self, tmp_path):
        gen = make_gen(tmp_path, extra={"enable_mcp": False})
        result = gen._bot_py()
        # <<<mcp_import>>> and <<<mcp_init>>> should both be replaced with ""
        assert "<<<mcp_import>>>" not in result
        assert "<<<mcp_init>>>" not in result

    def test_with_mcp_contains_import(self, tmp_path):
        gen = make_gen(tmp_path, extra={"enable_mcp": True})
        result = gen._bot_py()
        assert "MCPClient" in result
        assert "<<<mcp_import>>>" not in result
        assert "<<<mcp_init>>>" not in result

    def test_without_mcp_no_mcp_client_import(self, tmp_path):
        gen = make_gen(tmp_path, extra={"enable_mcp": False})
        # The empty string should be substituted; MCPClient import should not appear
        result = gen._bot_py()
        assert "from .mcp_client import MCPClient" not in result


# ---------------------------------------------------------------------------
# _ALL_SKILLS constant
# ---------------------------------------------------------------------------

class TestAllSkills:
    def test_all_skills_have_template_files(self):
        for skill in _ALL_SKILLS:
            assert (_TEMPLATE_DIR / "skills" / f"{skill}.py").exists(), \
                f"Missing template for skill: {skill}"

    def test_expected_skills_present(self):
        expected = {"file_manager", "code_executor", "web_search", "scheduler_skill", "self_modifier"}
        assert set(_ALL_SKILLS) == expected


# ---------------------------------------------------------------------------
# ProjectGenerator.generate  (integration — uses real template files)
# ---------------------------------------------------------------------------

class TestGenerate:
    def test_generate_minimal_creates_core_files(self, tmp_path):
        gen = make_gen(tmp_path, name="proj", extra={"skills": []})
        gen.generate()

        root = tmp_path / "proj"
        assert (root / "start.py").exists()
        assert (root / ".gitignore").exists()
        assert (root / "core" / "config.py").exists()
        assert (root / "core" / "ai_client.py").exists()
        assert (root / "core" / "memory_manager.py").exists()
        assert (root / "core" / "scheduler.py").exists()
        assert (root / "core" / "skill_manager.py").exists()
        assert (root / "core" / "bot.py").exists()
        assert (root / "skills" / "base_skill.py").exists()
        assert (root / "requirements.txt").exists()
        assert (root / ".env").exists()
        assert (root / "config" / "config.yaml").exists()
        assert (root / "README.md").exists()
        assert (root / ".meta" / "memory" / ".gitkeep").exists()

    def test_generate_with_skills(self, tmp_path):
        gen = make_gen(tmp_path, name="proj",
                       extra={"skills": ["file_manager", "web_search"]})
        gen.generate()
        root = tmp_path / "proj"
        assert (root / "skills" / "file_manager.py").exists()
        assert (root / "skills" / "web_search.py").exists()
        assert not (root / "skills" / "code_executor.py").exists()

    def test_generate_unknown_skill_skipped(self, tmp_path):
        gen = make_gen(tmp_path, name="proj",
                       extra={"skills": ["nonexistent_skill", "file_manager"]})
        gen.generate()
        root = tmp_path / "proj"
        assert not (root / "skills" / "nonexistent_skill.py").exists()
        assert (root / "skills" / "file_manager.py").exists()

    def test_generate_with_mcp(self, tmp_path):
        gen = make_gen(tmp_path, name="proj",
                       extra={"enable_mcp": True, "mcp_servers": {}})
        gen.generate()
        root = tmp_path / "proj"
        assert (root / "core" / "mcp_client.py").exists()
        assert (root / "mcp" / "mcp_servers.json").exists()

    def test_generate_without_mcp_no_mcp_files(self, tmp_path):
        gen = make_gen(tmp_path, name="proj")
        gen.generate()
        root = tmp_path / "proj"
        assert not (root / "core" / "mcp_client.py").exists()
        assert not (root / "mcp").exists()

    def test_generate_with_soul(self, tmp_path):
        gen = make_gen(tmp_path, name="proj",
                       extra={"create_soul": True, "soul_name": "Aria",
                              "soul_description": "A wise AI"})
        gen.generate()
        root = tmp_path / "proj"
        assert (root / ".meta" / "soul.md").exists()
        assert "Aria" in (root / ".meta" / "soul.md").read_text(encoding="utf-8")

    def test_generate_without_soul_no_soul_file(self, tmp_path):
        gen = make_gen(tmp_path, name="proj")
        gen.generate()
        assert not (tmp_path / "proj" / ".meta" / "soul.md").exists()

    def test_generate_all_skills(self, tmp_path):
        gen = make_gen(tmp_path, name="proj", extra={"skills": list(_ALL_SKILLS)})
        gen.generate()
        root = tmp_path / "proj"
        for skill in _ALL_SKILLS:
            assert (root / "skills" / f"{skill}.py").exists()

    def test_start_py_contains_project_name(self, tmp_path):
        gen = make_gen(tmp_path, name="myrobot")
        gen.generate()
        content = (tmp_path / "myrobot" / "start.py").read_text(encoding="utf-8")
        assert "myrobot" in content

    def test_requirements_txt_content(self, tmp_path):
        gen = make_gen(tmp_path, name="proj",
                       extra={"enable_mcp": True, "skills": ["web_search"]})
        gen.generate()
        req = (tmp_path / "proj" / "requirements.txt").read_text()
        assert "openai" in req
        assert "mcp>=" in req
        assert "duckduckgo-search" in req

    def test_env_file_content(self, tmp_path):
        gen = make_gen(tmp_path, name="proj",
                       extra={"model_provider": "openai", "api_key": "sk-xyz"})
        gen.generate()
        env = (tmp_path / "proj" / ".env").read_text()
        assert "OPENAI_API_KEY=sk-xyz" in env

    def test_mcp_json_valid(self, tmp_path):
        servers = {"test": {"command": "python", "args": ["-m", "server"]}}
        gen = make_gen(tmp_path, name="proj",
                       extra={"enable_mcp": True, "mcp_servers": servers})
        gen.generate()
        data = json.loads((tmp_path / "proj" / "mcp" / "mcp_servers.json").read_text())
        assert data["mcpServers"] == servers
