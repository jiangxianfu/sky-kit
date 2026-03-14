#!/usr/bin/env python3
"""
cli.py — <<<name>>> AI Robot 命令行客户端（连接后台服务）
用法:
    python cli.py                         # 连接默认服务 (localhost:8765)
    python cli.py --url http://host:port  # 连接指定服务
    python cli.py --session my-session    # 使用指定会话
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

try:
    import httpx
except ImportError:
    print("[!] 正在安装 httpx …")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

DEFAULT_URL = "http://localhost:8765"


class CLIClient:
    def __init__(self, base_url: str = DEFAULT_URL, session_id: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.session_id = session_id
        self.console = Console() if HAS_RICH else None
        self.bot_name = "AI"

    def _print(self, msg, style=None):
        if self.console:
            self.console.print(msg, style=style)
        else:
            print(msg)

    def _check_service(self) -> bool:
        try:
            with httpx.Client(timeout=3) as client:
                resp = client.get(f"{self.base_url}/api/status")
                if resp.status_code == 200:
                    data = resp.json()
                    self.bot_name = data.get("bot_name", "AI")
                    return True
        except Exception:
            pass
        return False

    def _print_welcome(self, status: dict):
        skills = ", ".join(status.get("skills", [])) or "无"
        model = status.get("model", "未知")
        uptime = status.get("uptime_seconds", 0)
        uptime_str = f"{int(uptime//60)}分{int(uptime%60)}秒" if uptime > 60 else f"{int(uptime)}秒"

        if self.console:
            self.console.print(Panel(
                f"[bold cyan]{self.bot_name}[/bold cyan] 已就绪（后台服务模式）\n"
                f"[dim]服务: {self.base_url}[/dim]\n"
                f"[dim]模型: {model}[/dim]\n"
                f"[dim]技能: {skills}[/dim]\n"
                f"[dim]运行: {uptime_str}[/dim]\n\n"
                "[dim]命令: /quit  /session  /clear  /status  /memory  /help[/dim]",
                title="[bold]<<<name>>> AI Robot (CLI 客户端)[/bold]",
                border_style="bright_blue",
            ))
        else:
            print(f"\n{'='*50}")
            print(f"  {self.bot_name} 已就绪")
            print(f"  服务: {self.base_url}")
            print(f"  模型: {model}")
            print(f"{'='*50}\n")

    async def _stream_chat(self, message: str) -> str:
        full_reply = []
        url = f"{self.base_url}/api/chat/stream"
        params = {"message": message}
        if self.session_id:
            params["session_id"] = self.session_id

        if self.console:
            self.console.print(f"\n[bold cyan]{self.bot_name}[/bold cyan]: ", end="")

        try:
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream("GET", url, params=params) as resp:
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            raw = line[6:]
                            try:
                                data = json.loads(raw)
                                if data["type"] == "chunk":
                                    chunk = data["content"]
                                    full_reply.append(chunk)
                                    if self.console:
                                        self.console.print(chunk, end="", highlight=False)
                                    else:
                                        print(chunk, end="", flush=True)
                                    if not self.session_id:
                                        self.session_id = data.get("session_id")
                                elif data["type"] == "done":
                                    if not self.session_id:
                                        self.session_id = data.get("session_id")
                                elif data["type"] == "error":
                                    self._print(f"\n[red]错误: {data['content']}[/red]")
                            except json.JSONDecodeError:
                                pass
        except httpx.ConnectError:
            self._print("\n[red]✗ 无法连接到后台服务，请确认服务正在运行：[/red]")
            self._print("[yellow]  python service.py[/yellow]")
            return ""
        except Exception as e:
            self._print(f"\n[red]错误: {e}[/red]")
            return ""

        if self.console:
            self.console.print()
        else:
            print()

        return "".join(full_reply)

    async def _handle_command(self, cmd: str) -> bool:
        cmd = cmd.strip().lower()

        if cmd in ("/quit", "/exit", "/bye", "/q"):
            return False

        elif cmd == "/status":
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"{self.base_url}/api/status")
                    data = resp.json()
                    uptime = data.get("uptime_seconds", 0)
                    self._print(f"\n[green]服务状态:[/green]")
                    self._print(f"  机器人: {data.get('bot_name')}")
                    self._print(f"  模型: {data.get('model')}")
                    self._print(f"  消息数: {data.get('message_count')}")
                    self._print(f"  运行时间: {int(uptime)}秒")
            except Exception as e:
                self._print(f"[red]获取状态失败: {e}[/red]")

        elif cmd == "/session":
            self._print(f"[dim]当前会话 ID: {self.session_id or '(新会话)'}[/dim]")

        elif cmd == "/clear":
            if self.session_id:
                try:
                    async with httpx.AsyncClient(timeout=5) as client:
                        await client.delete(f"{self.base_url}/api/sessions/{self.session_id}")
                except Exception:
                    pass
            self.session_id = None
            if self.console:
                self.console.clear()
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"{self.base_url}/api/status")
                    self._print_welcome(resp.json())
            self._print("[green]✓ 会话已清除，开始新对话[/green]")

        elif cmd == "/memory":
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"{self.base_url}/api/memory")
                    data = resp.json()
                    if self.console:
                        self.console.print(Panel(
                            data.get("summary", "无记忆"),
                            title="记忆摘要",
                            border_style="blue"
                        ))
                    else:
                        print(f"\n记忆摘要:\n{data.get('summary', '无记忆')}\n")
            except Exception as e:
                self._print(f"[red]获取记忆失败: {e}[/red]")

        elif cmd == "/help":
            help_text = (
                "[bold]可用命令:[/bold]\n"
                "  /quit    - 退出（不停止后台服务）\n"
                "  /status  - 查看服务状态\n"
                "  /session - 显示当前会话 ID\n"
                "  /clear   - 清除会话，开始新对话\n"
                "  /memory  - 查看记忆摘要\n"
                "  /help    - 显示帮助"
            )
            if self.console:
                self.console.print(Panel(help_text, title="帮助", border_style="green"))
            else:
                print(help_text)
        else:
            self._print(f"[yellow]未知命令: {cmd}，输入 /help 查看帮助[/yellow]")

        return True

    async def run(self):
        if not self._check_service():
            self._print("[red]✗ 无法连接到后台服务！[/red]")
            self._print("[yellow]请先启动服务: python service.py[/yellow]")
            self._print(f"[dim]目标地址: {self.base_url}[/dim]")
            return

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/status")
                self._print_welcome(resp.json())
        except Exception:
            self._print_welcome({})

        while True:
            try:
                if self.console:
                    user_input = Prompt.ask("\n[bold green]You[/bold green]")
                else:
                    user_input = input("\nYou: ").strip()

                if not user_input.strip():
                    continue

                if user_input.startswith("/"):
                    if not await self._handle_command(user_input):
                        break
                    continue

                await self._stream_chat(user_input)

            except KeyboardInterrupt:
                self._print("\n[yellow]提示: 用 /quit 优雅退出（后台服务继续运行）[/yellow]")
            except EOFError:
                break
            except Exception as e:
                self._print(f"\n[red]错误: {e}[/red]")

        self._print("\n[dim]已退出 CLI 客户端（后台服务仍在运行）[/dim]")
        self._print(f"[dim]Web UI: {self.base_url}/[/dim]")


def main():
    args = sys.argv[1:]
    base_url = DEFAULT_URL
    session_id = None

    i = 0
    while i < len(args):
        if args[i] == "--url" and i + 1 < len(args):
            base_url = args[i + 1]
            i += 2
        elif args[i] == "--session" and i + 1 < len(args):
            session_id = args[i + 1]
            i += 2
        else:
            i += 1

    client = CLIClient(base_url=base_url, session_id=session_id)
    asyncio.run(client.run())


if __name__ == "__main__":
    main()
