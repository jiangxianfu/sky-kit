"""Unit tests for cli/main.py 鈥?targeting 鈮?0 % coverage."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.main import cli, _wizard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(args, input_text="", catch_exceptions=False):
    """Invoke the CLI with the given args and optional stdin text."""
    runner = CliRunner()
    return runner.invoke(cli, args, input=input_text, catch_exceptions=catch_exceptions)


# ---------------------------------------------------------------------------
# Top-level group
# ---------------------------------------------------------------------------

class TestCliGroup:
    def test_version_flag(self):
        result = run(["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_flag(self):
        result = run(["--help"])
        assert result.exit_code == 0
        assert "sky-kit" in result.output.lower()

    def test_init_in_help(self):
        result = run(["--help"])
        assert "init" in result.output


# ---------------------------------------------------------------------------
# init command 鈥?preset options path (no interactive prompts)
# ---------------------------------------------------------------------------

class TestInitPreset:
    """Tests where --model and --api-key are supplied so wizard prompts
    only ask for model name and optional base URL."""

    def _run_init(self, tmp_path: Path, name: str, extra_input: str = "") -> object:
        with patch("cli.main.Path") as mock_path_cls:
            mock_path_cls.cwd.return_value = tmp_path
            mock_path_cls.return_value = tmp_path / name   # project_path
            # Make project_path.exists() return False so we skip the overwrite dialog
            fake_project = MagicMock(spec=Path)
            fake_project.exists.return_value = False

            def path_side(arg=""):
                if arg == "":
                    return tmp_path
                return fake_project

            mock_path_cls.cwd.return_value = tmp_path

            with patch("cli.main.ProjectGenerator") as MockGen:
                MockGen.return_value.generate = MagicMock()
                runner = CliRunner()
                result = runner.invoke(
                    cli,
                    ["init", name, "--model", "openai", "--api-key", "sk-test"],
                    input=extra_input,   # model name prompt, optional base_url prompt
                    catch_exceptions=False,
                )
                return result, MockGen

    def test_init_completes_successfully(self, tmp_path):
        with patch("cli.main.ProjectGenerator") as MockGen, \
             patch("cli.main.Path") as MockPath:
            fake_proj_path = MagicMock(spec=Path)
            fake_proj_path.exists.return_value = False
            MockPath.cwd.return_value = tmp_path
            MockPath.return_value = fake_proj_path
            MockGen.return_value.generate = MagicMock()

            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["init", "proj", "--model", "openai", "--api-key", "sk-x"],
                # Prompts: model name (default), base_url (default)
                input="\n\n",
                catch_exceptions=False,
            )
            assert result.exit_code == 0

    def test_init_calls_generator_generate(self, tmp_path):
        with patch("cli.main.ProjectGenerator") as MockGen, \
             patch("cli.main.Path") as MockPath:
            fake_proj_path = MagicMock(spec=Path)
            fake_proj_path.exists.return_value = False
            MockPath.cwd.return_value = tmp_path
            MockPath.return_value = fake_proj_path
            mock_instance = MagicMock()
            MockGen.return_value = mock_instance

            runner = CliRunner()
            runner.invoke(
                cli,
                ["init", "proj", "--model", "openai", "--api-key", "sk-x"],
                input="\n\n",
                catch_exceptions=False,
            )
            mock_instance.generate.assert_called_once()

    def test_init_existing_dir_abort(self, tmp_path):
        with patch("cli.main.ProjectGenerator") as MockGen, \
             patch("cli.main.Path") as MockPath:
            fake_proj_path = MagicMock(spec=Path)
            fake_proj_path.exists.return_value = True
            MockPath.cwd.return_value = tmp_path
            MockPath.return_value = fake_proj_path

            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["init", "proj", "--model", "openai", "--api-key", "sk-x"],
                # "n" to the "directory already exists, continue?" prompt
                input="n\n",
            )
            MockGen.return_value.generate.assert_not_called()

    def test_init_existing_dir_continue(self, tmp_path):
        with patch("cli.main.ProjectGenerator") as MockGen, \
             patch("cli.main.Path") as MockPath:
            fake_proj_path = MagicMock(spec=Path)
            fake_proj_path.exists.return_value = True
            MockPath.cwd.return_value = tmp_path
            MockPath.return_value = fake_proj_path
            mock_instance = MagicMock()
            MockGen.return_value = mock_instance

            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["init", "proj", "--model", "openai", "--api-key", "sk-x"],
                # "y" = continue, then model name + base_url defaults
                input="y\n\n\n",
                catch_exceptions=False,
            )
            mock_instance.generate.assert_called_once()

    def test_init_output_shows_project_name(self, tmp_path):
        with patch("cli.main.ProjectGenerator") as MockGen, \
             patch("cli.main.Path") as MockPath:
            fake_proj_path = MagicMock(spec=Path)
            fake_proj_path.exists.return_value = False
            MockPath.cwd.return_value = tmp_path
            MockPath.return_value = fake_proj_path
            MockGen.return_value.generate = MagicMock()

            runner = CliRunner()
            result = runner.invoke(
                cli,
                ["init", "awesomebot", "--model", "openai", "--api-key", "sk-x"],
                input="\n\n",
                catch_exceptions=False,
            )
            assert "awesomebot" in result.output

    def test_init_help(self):
        result = run(["init", "--help"])
        assert result.exit_code == 0
        assert "NAME" in result.output or "name" in result.output.lower()


# ---------------------------------------------------------------------------
# _wizard 鈥?unit tests (direct call, no CLI runner needed)
# ---------------------------------------------------------------------------

class TestWizard:
    """Test _wizard() by mocking rich prompts."""

    def _run_wizard(self, name: str, preset_model=None, preset_key=None,
                    prompt_returns=None):
        """
        Call _wizard with mocked Prompt.ask / Confirm.ask.
        prompt_returns: list of return values for each Prompt.ask call (in order).
        """
        prompt_returns = prompt_returns or []
        call_count = [0]

        def fake_prompt_ask(question, **kwargs):
            idx = call_count[0]
            call_count[0] += 1
            if idx < len(prompt_returns):
                return prompt_returns[idx]
            return kwargs.get("default", "")

        with patch("cli.main.Prompt.ask", side_effect=fake_prompt_ask):
            return _wizard(name, preset_model, preset_key)

    def test_preset_openai(self):
        # preset model 鈫?only model_name and base_url prompts
        config = self._run_wizard("bot", preset_model="openai", preset_key="sk-abc",
                                  prompt_returns=["gpt-4o", ""])
        assert config["model_provider"] == "openai"
        assert config["api_key"] == "sk-abc"
        assert config["model_name"] == "gpt-4o"

    def test_preset_claude(self):
        config = self._run_wizard("bot", preset_model="claude", preset_key="sk-ant-x",
                                  prompt_returns=["claude-3-5-haiku-20241022"])
        assert config["model_provider"] == "claude"
        assert config["api_key"] == "sk-ant-x"

    def test_preset_github_copilot(self):
        config = self._run_wizard("bot", preset_model="github-copilot", preset_key="ghp_t",
                                  prompt_returns=["gpt-4o"])
        assert config["model_provider"] == "github-copilot"
        assert config["base_url"] == "https://models.inference.ai.azure.com"

    def test_default_skills_included(self):
        config = self._run_wizard("bot", preset_model="openai", preset_key="k",
                                  prompt_returns=["gpt-4o-mini", ""])
        # Wizard always includes all default skills
        for skill in ["file_manager", "code_executor", "web_search",
                      "scheduler_skill", "self_modifier"]:
            assert skill in config["skills"]

    def test_enable_mcp_default_false(self):
        config = self._run_wizard("bot", preset_model="openai", preset_key="k",
                                  prompt_returns=["gpt-4o-mini", ""])
        assert config["enable_mcp"] is False

    def test_name_stored_in_config(self):
        config = self._run_wizard("mybot", preset_model="openai", preset_key="k",
                                  prompt_returns=["gpt-4o-mini", ""])
        assert config["name"] == "mybot"

    def test_interactive_provider_choice_1(self):
        """Interactive mode: user picks choice '1' (openai)."""
        prompt_vals = ["1", "gpt-4o-mini", "", ""]  # provider choice, model name, base_url, api_key
        with patch("cli.main.Prompt.ask", side_effect=prompt_vals), \
             patch("cli.main.console"):
            config = _wizard("bot", None, None)
        assert config["model_provider"] == "openai"

    def test_interactive_provider_choice_2(self):
        """Interactive mode: user picks choice '2' (claude)."""
        with patch("cli.main.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["2", "claude-3-5-haiku-20241022", "sk-ant"]
            with patch("cli.main.console"):
                config = _wizard("bot", None, None)
        assert config["model_provider"] == "claude"

    def test_interactive_provider_choice_3(self):
        """Interactive mode: user picks choice '3' (github-copilot)."""
        with patch("cli.main.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["3", "gpt-4o", "ghp_tok"]
            with patch("cli.main.console"):
                config = _wizard("bot", None, None)
        assert config["model_provider"] == "github-copilot"
        assert config["base_url"] == "https://models.inference.ai.azure.com"

    def test_openai_custom_base_url(self):
        """openai provider can have a custom base_url."""
        with patch("cli.main.Prompt.ask") as mock_prompt:
            # provider choice already preset, model name, base_url
            mock_prompt.side_effect = ["gpt-4o-mini", "https://my-proxy.example.com"]
            config = _wizard("bot", "openai", "sk-x")
        assert config["base_url"] == "https://my-proxy.example.com"

    def test_no_preset_api_key_asks_prompt(self):
        """When no preset key, should prompt for it (password=True)."""
        asked_kwargs = []

        def record_prompt(question, **kwargs):
            asked_kwargs.append(kwargs)
            return kwargs.get("default", "")

        with patch("cli.main.Prompt.ask", side_effect=record_prompt), \
             patch("cli.main.console"):
            _wizard("bot", "openai", None)

        # The last call should have password=True
        assert any(kw.get("password") for kw in asked_kwargs)
