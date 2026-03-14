#!/usr/bin/env python3
"""
start.py — <<<name>>> AI Robot 统一启动入口

用法:
    python start.py              # 交互式选择启动方式
    python start.py service      # 启动后台服务
    python start.py cli          # 启动 CLI 客户端（连接服务）
    python start.py chat         # 直接本地聊天（无需服务）
    python start.py service --daemon   # 后台守护进程
    python start.py service --stop     # 停止后台服务
    python start.py service --status   # 查看服务状态
"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _banner():
    print("""
╔══════════════════════════════════════════════╗
║       <<<name>>> — AI Robot (sky-kit)        ║
╠══════════════════════════════════════════════╣
║  1. service  后台服务 (API + Web UI)          ║
║  2. cli      命令行客户端 (连接后台服务)        ║
║  3. chat     本地直接聊天 (无需服务)           ║
╚══════════════════════════════════════════════╝
""")


def run_service(extra_args=None):
    """启动后台服务"""
    import service as svc
    args = extra_args or []

    if "--stop" in args:
        svc.cmd_stop()
    elif "--status" in args:
        svc.cmd_status()
    elif "--daemon" in args:
        print("[*] 以守护进程方式启动后台服务 …")
        print(f"[*] 日志文件: {svc.LOG_FILE.absolute()}")
        print("[*] 停止命令: python start.py service --stop")
        svc.cmd_daemon()
    else:
        print("=" * 50)
        print("  <<<name>>> AI Robot 后台服务")
        print(f"  API 文档: http://localhost:{svc.PORT}/docs")
        print(f"  Web  UI : http://localhost:{svc.PORT}/")
        print("  按 Ctrl+C 停止服务")
        print("=" * 50)
        svc.cmd_foreground()


def run_cli(extra_args=None):
    """启动 CLI 客户端"""
    import cli
    if extra_args:
        sys.argv = ["cli.py"] + extra_args
    else:
        sys.argv = ["cli.py"]
    cli.main()


def run_chat():
    """本地直接聊天（原始模式）"""
    from core.bot import Bot
    from core.config import Config

    async def _main():
        config = Config()
        bot = Bot(config)
        await bot.start()

    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        print("\nGoodbye!")
    except Exception as exc:
        print(f"Fatal error: {exc}")
        sys.exit(1)


def interactive_menu():
    """交互式选择菜单"""
    _banner()
    try:
        choice = input("请选择模式 [1/2/3] (默认 1): ").strip() or "1"
    except (KeyboardInterrupt, EOFError):
        print("\n已取消")
        return

    if choice in ("1", "service"):
        run_service()
    elif choice in ("2", "cli"):
        run_cli()
    elif choice in ("3", "chat"):
        run_chat()
    else:
        print(f"未知选项: {choice}")


def main():
    args = sys.argv[1:]

    if not args:
        interactive_menu()
        return

    mode = args[0].lower()
    rest = args[1:]

    if mode in ("service", "svc", "server"):
        run_service(rest)
    elif mode in ("cli", "client"):
        run_cli(rest)
    elif mode in ("chat", "local"):
        run_chat()
    elif mode in ("--help", "-h", "help"):
        print(__doc__)
    else:
        print(f"未知命令: {mode}")
        print("用法: python start.py [service|cli|chat]")
        sys.exit(1)


if __name__ == '__main__':
    main()
