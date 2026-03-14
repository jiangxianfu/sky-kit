#!/usr/bin/env python3
"""sky-kit CLI - Bootstrap a zero-to-one AI robot with a single command."""

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from .generator import ProjectGenerator

console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="sky-kit")
def cli():
    """sky-kit — Bootstrap a zero-to-one AI robot.

    \b
    Quick start:
        sky-kit init sky001
        cd sky001
        uv sync
        python start.py
    """
    pass


@cli.command()
@click.argument("name", required=False)
@click.option("--model", "-m",
              type=click.Choice(["openai", "claude", "github-copilot"]),
              help="AI model provider")
@click.option("--api-key", "-k", "api_key", help="API key for the AI provider")
def init(name, model, api_key):
    """Bootstrap a new AI Robot project.

    \b
    Examples:
        sky-kit init
        sky-kit init sky001
        sky-kit init sky001 --model openai --api-key sk-...
    """
    console.print(Panel.fit(
        "[bold cyan]sky-kit[/bold cyan]  —  Bootstrap your AI Robot\n"
        "[dim]Answer two questions, then run: python start.py[/dim]",
        border_style="cyan",
    ))

    # ── project name ────────────────────────────────────────────────────────
    if not name:
        name = Prompt.ask("[green]Robot project name[/green]", default="my-robot")
    name = name.strip().replace(" ", "-")

    project_path = Path.cwd() / name
    if project_path.exists():
        if not Confirm.ask(
            f"[yellow]Directory '{name}' already exists. Continue?[/yellow]"
        ):
            sys.exit(0)

    config = _wizard(name, model, api_key)

    with console.status(f"[bold green]Creating '{name}'…"):
        ProjectGenerator(name, config).generate()

    console.print(f"\n[bold green]✓ '{name}' is ready![/bold green]\n")
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  [cyan]cd {name}[/cyan]")
    console.print(f"  [cyan]uv sync[/cyan]")
    console.print(f"  [cyan]python start.py[/cyan]")
    console.print()
    console.print("[dim]Your robot will introduce itself on first run. 🤖[/dim]")


def _wizard(name: str, preset_model, preset_api_key) -> dict:
    """Two-question wizard: AI model + API key. Everything else is self-configured."""
    config: dict = {
        "name": name,
        # Filled in below
        "model_provider": "",
        "model_name": "",
        "api_key": "",
        "base_url": "",
        # Defaults — the robot evolves these itself
        "enable_mcp": False,
        "mcp_servers": {},
        "enable_skills": True,
        "skills": ["file_manager", "code_executor", "web_search"],
        "create_soul": False,
    }

    # ── Question 1: AI provider ───────────────────────────────────────────────
    console.print()
    if preset_model:
        config["model_provider"] = preset_model
    else:
        t = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 2))
        t.add_column("#", style="cyan", width=3)
        t.add_column("Provider", style="green", width=20)
        t.add_column("Example models")
        t.add_row("1", "OpenAI", "gpt-4o, gpt-4o-mini, o3-mini")
        t.add_row("2", "Claude (Anthropic)", "claude-3-5-sonnet, claude-3-haiku")
        t.add_row("3", "GitHub Copilot", "gpt-4o, o1-mini  (GitHub Models API)")
        console.print(t)
        choice = Prompt.ask(
            "[green]Choose AI provider[/green]",
            choices=["1", "2", "3"],
            default="1",
        )
        config["model_provider"] = {"1": "openai", "2": "claude", "3": "github-copilot"}[choice]

    model_defaults = {
        "openai": "gpt-4o-mini",
        "claude": "claude-3-5-haiku-20241022",
        "github-copilot": "gpt-4o",
    }
    config["model_name"] = Prompt.ask(
        "[green]Model name[/green]",
        default=model_defaults[config["model_provider"]],
    )

    if config["model_provider"] == "github-copilot":
        config["base_url"] = "https://models.inference.ai.azure.com"
    elif config["model_provider"] == "openai":
        config["base_url"] = Prompt.ask(
            "[green]Custom API base URL (leave blank for default)[/green]",
            default="",
        )

    # ── Question 2: API key ───────────────────────────────────────────────────
    if preset_api_key:
        config["api_key"] = preset_api_key
    else:
        key_prompts = {
            "openai": "OpenAI API key  (sk-…)",
            "claude": "Anthropic API key  (sk-ant-…)",
            "github-copilot": "GitHub Personal Access Token",
        }
        config["api_key"] = Prompt.ask(
            f"[green]{key_prompts[config['model_provider']]}[/green]",
            password=True,
            default="",
        )

    return config


if __name__ == "__main__":
    cli()
