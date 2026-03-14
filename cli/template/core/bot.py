# core/bot.py — Main AI-robot logic: soul, chat loop, memory
<<<mcp_import>>>
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .ai_client import AIClient
from .config import Config
from .memory_manager import MemoryManager
from .skill_manager import SkillManager

console = Console()


class Bot:
    def __init__(self, config: Config):
        self.config = config
        self.name: str = config.robot_name
        self.messages: List[Dict] = []
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.soul_path = Path('.meta/soul.md')
        self.system_prompt = ''

        # Core components
        self.ai = AIClient(
            provider=config.model_provider,
            model=config.model_name,
            api_key=config.api_key,
            base_url=config.base_url,
        )
        self.memory = MemoryManager(config.memory_dir)
        self.skills = SkillManager(
            skills_dir=config.skills_dir,
            enabled=config.enabled_skills,
        )
        <<<mcp_init>>>

    # ── lifecycle ───────────────────────────────────────────────────────────

    async def start(self):
        await self._ensure_soul()
        self._load_system_prompt()
        self._print_welcome()
        await self._chat_loop()

    # ── soul ────────────────────────────────────────────────────────────────

    async def _ensure_soul(self):
        '''If no soul.md exists, guide the user through identity creation.'''
        if self.soul_path.exists():
            return

        console.print(Panel(
            '[bold cyan]Hello! This is my very first run.[/bold cyan]\n'
            '[dim]Let me discover who I am…[/dim]',
            border_style='cyan',
        ))

        given_name = Prompt.ask(
            '\n[bold green]What would you like to call me?[/bold green]',
            default=self.config.robot_name,
        )
        console.print('\n[bold green]What kind of AI companion should I be?[/bold green]')
        console.print('[dim]e.g. creative partner, research assistant, coding buddy…[/dim]')
        personality = Prompt.ask('[green]My personality & purpose[/green]')
        focus = Prompt.ask(
            '[green]Special focus areas (optional)[/green]',
            default='general-purpose assistant',
        )

        self.soul_path.parent.mkdir(parents=True, exist_ok=True)
        self.soul_path.write_text(
            self._make_soul_md(given_name, personality, focus),
            encoding='utf-8',
        )
        self.name = given_name
        self.config.update_robot_name(given_name)
        console.print(f'\n[bold green]✓ Soul created! I am now {given_name}.[/bold green]\n')

    def _make_soul_md(self, name: str, personality: str, focus: str) -> str:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return f'''# {name} — Soul Configuration

## Identity
- **Name**: {name}
- **Created**: {now}
- **Type**: AI Robot (sky-kit)

## Personality & Purpose
{personality}

## Focus Areas
{focus}

## Core Values
- Be helpful, honest, and transparent
- Remember the user and personalise every response
- Grow, learn, and evolve over time
- Acknowledge uncertainty rather than guessing

## Behavioural Guidelines
- Address the user warmly and personally
- Reference past conversations where relevant
- Proactively suggest helpful next steps
- Celebrate achievements and milestones with the user

## Self-Evolution Log
_Updated automatically as {name} grows._
- Initial creation: {now[:10]}
'''

    def _load_system_prompt(self):
        if not self.soul_path.exists():
            self.system_prompt = f'You are {self.name}, a helpful AI assistant.'
            return

        soul = self.soul_path.read_text(encoding='utf-8')

        # Extract name from soul
        for line in soul.splitlines():
            if '**Name**:' in line:
                self.name = line.split('**Name**:')[1].strip()
                break

        mem_summary = self.memory.get_summary()
        skill_list = ', '.join(self.skills.list_skills()) or 'none'
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.system_prompt = f'''You are {self.name}, an AI robot created with sky-kit.

## Your Soul
{soul}

## Current Date & Time
{now}

## Memory Summary
{mem_summary}

## Available Skills
{skill_list}

## Instructions
- Embody the personality described in your soul
- Reference memories from past conversations when relevant
- Use skills when they would genuinely help the user
- If asked to modify yourself, update files in the project directory
- Store important facts explicitly by writing to the memory directory'''

    # ── welcome ─────────────────────────────────────────────────────────────

    def _print_welcome(self):
        skill_str = ', '.join(self.skills.list_skills()) or 'none'
        console.print(Panel(
            f'[bold cyan]{self.name}[/bold cyan] is online.\n'
            f'[dim]Model : {self.config.model_provider} / {self.config.model_name}[/dim]\n'
            f'[dim]Skills: {skill_str}[/dim]\n\n'
            '[dim]Commands: /quit  /memory  /skills  /about  /clear  /save  /search <kw>[/dim]',
            title='[bold]sky-kit AI Robot[/bold]',
            border_style='bright_blue',
        ))

    # ── chat loop ───────────────────────────────────────────────────────────

    async def _chat_loop(self):
        while True:
            try:
                user_input = Prompt.ask(f'\n[bold green]You[/bold green]')
                if not user_input.strip():
                    continue

                if user_input.startswith('/'):
                    if not await self._handle_command(user_input):
                        break
                    continue

                await self._agentic_turn(user_input)

                # Auto-save every 10 messages
                if len(self.messages) % 10 == 0:
                    self.memory.save_conversation(self.messages, self.session_id)

            except KeyboardInterrupt:
                console.print('\n[yellow]Tip: use /quit to exit cleanly.[/yellow]')
            except EOFError:
                break
            except Exception as exc:
                console.print(f'\n[red]Error: {exc}[/red]')

        # ── shutdown ─────────────────────────────────────────────────────────
        if self.messages:
            saved = self.memory.save_conversation(self.messages, self.session_id)
            console.print(f'\n[dim]Conversation saved → {saved}[/dim]')
        console.print('[dim]Goodbye![/dim]')

    # ── agentic turn ─────────────────────────────────────────────────────────

    async def _agentic_turn(self, user_input: str):
        """Handle one user turn with multi-step tool-use loop."""
        self.messages.append({'role': 'user', 'content': user_input})
        tools = self.skills.get_tool_definitions()

        console.print(f'\n[bold cyan]{self.name}[/bold cyan]:')

        max_iterations = 10
        for _ in range(max_iterations):
            assistant_msg, tool_calls = self.ai.chat_with_tools(
                messages=self.messages,
                system_prompt=self.system_prompt,
                tools=tools,
            )
            self.messages.append(assistant_msg)

            if tool_calls is None:
                # Final text reply
                text = assistant_msg.get('content', '')
                console.print(Markdown(text) if text else '')
                return

            # Execute each tool call and feed results back
            for call in tool_calls:
                skill_name = call['name']
                args = call['arguments']
                console.print(f'[dim]→ [{skill_name}] {args}[/dim]')
                result = self.skills.execute(skill_name, **args)
                result_str = str(result)
                preview = result_str[:300] + ('...' if len(result_str) > 300 else '')
                console.print(f'[dim]✓ {preview}[/dim]')
                self.messages.append({
                    'role': 'tool',
                    'tool_call_id': call['id'],
                    'content': result_str,
                })

        console.print('[yellow]⚠ 已达到工具调用上限。[/yellow]')

    async def _agentic_turn_api(self, user_input: str):
        """Non-streaming turn for service.py API endpoint."""
        self.messages.append({'role': 'user', 'content': user_input})
        tools = self.skills.get_tool_definitions()
        max_iterations = 10
        for _ in range(max_iterations):
            assistant_msg, tool_calls = self.ai.chat_with_tools(
                messages=self.messages,
                system_prompt=self.system_prompt,
                tools=tools,
            )
            self.messages.append(assistant_msg)
            if tool_calls is None:
                return
            for call in tool_calls:
                result = self.skills.execute(call['name'], **call['arguments'])
                self.messages.append({
                    'role': 'tool',
                    'tool_call_id': call['id'],
                    'content': str(result),
                })

    async def _agentic_turn_stream(self, user_input: str):
        """Streaming turn for service.py SSE endpoint (async generator)."""
        self.messages.append({'role': 'user', 'content': user_input})
        tools = self.skills.get_tool_definitions()
        max_iterations = 10
        for _ in range(max_iterations):
            assistant_msg, tool_calls = self.ai.chat_with_tools(
                messages=self.messages,
                system_prompt=self.system_prompt,
                tools=tools,
            )
            self.messages.append(assistant_msg)
            if tool_calls is None:
                text = assistant_msg.get('content', '')
                if text:
                    words = text.split(' ')
                    for i, word in enumerate(words):
                        yield word + (' ' if i < len(words) - 1 else '')
                        await asyncio.sleep(0.01)
                return
            for call in tool_calls:
                yield f'\n> 🔧 调用工具: {call["name"]}\n'
                result = self.skills.execute(call['name'], **call['arguments'])
                self.messages.append({
                    'role': 'tool',
                    'tool_call_id': call['id'],
                    'content': str(result),
                })

    # ── command handler ─────────────────────────────────────────────────────

    async def _handle_command(self, raw: str) -> bool:
        '''Process a slash-command. Returns False to exit the loop.'''
        cmd = raw.strip().lower()

        if cmd in ('/quit', '/exit', '/bye', '/q'):
            return False

        elif cmd == '/memory':
            console.print(Panel(self.memory.get_summary(), title='Memory', border_style='blue'))

        elif cmd == '/skills':
            names = self.skills.list_skills()
            body = chr(10).join(f'• {n}' for n in names) if names else 'No skills loaded.'
            console.print(Panel(body, title='Skills', border_style='green'))

        elif cmd == '/about':
            if self.soul_path.exists():
                console.print(Markdown(self.soul_path.read_text(encoding='utf-8')))
            else:
                console.print('[yellow]No soul.md found.[/yellow]')

        elif cmd == '/clear':
            self.messages = []
            console.clear()
            self._print_welcome()

        elif cmd in ('/save', '/s'):
            path = self.memory.save_conversation(self.messages, self.session_id)
            console.print(f'[green]Saved → {path}[/green]')

        elif cmd.startswith('/search '):
            kw = raw[8:].strip()
            results = self.memory.search_memories(kw)
            if results:
                console.print(f'[green]Found {len(results)} result(s) for "{kw}":[/green]')
                for r in results[:5]:
                    console.print(
                        f'  [{r["date"]}] {r["topic"]}: '
                        f'{r["match"][:80]}'
                    )
            else:
                console.print(f'[yellow]No memories found for "{kw}".[/yellow]')

        else:
            console.print(f'[yellow]Unknown command: {raw}[/yellow]')
            console.print('[dim]/quit /memory /skills /about /clear /save /search <kw>[/dim]')

        return True
