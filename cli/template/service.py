#!/usr/bin/env python3
"""
service.py — <<<name>>> AI Robot 后台服务
用法:
    python service.py            # 前台运行（可 Ctrl+C 停止）
    python service.py --daemon   # 后台守护进程运行
    python service.py --stop     # 停止后台守护进程
    python service.py --status   # 查看运行状态
"""

import asyncio
import json
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent))

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("[!] 缺少依赖，正在安装 fastapi & uvicorn …")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]"])
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel
    import uvicorn

from core.bot import Bot
from core.config import Config

HOST = "0.0.0.0"
PORT = 8765
PID_FILE = Path(".service.pid")
LOG_FILE = Path(".service.log")

app = FastAPI(
    title="<<<name>>> AI Robot API",
    description="AI Robot 后台服务 API",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_web_dir = Path("web")
if _web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_web_dir)), name="static")

_bot: Optional[Bot] = None
_bot_ready = False
_start_time = datetime.now()


async def get_bot() -> Bot:
    global _bot, _bot_ready
    if _bot is None:
        config = Config()
        _bot = Bot(config)
        await _bot._ensure_soul()
        _bot._load_system_prompt()
        _bot_ready = True
    return _bot


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    timestamp: str

class StatusResponse(BaseModel):
    status: str
    bot_name: str
    uptime_seconds: float
    message_count: int
    skills: List[str]
    model: str


_sessions: Dict[str, Dict] = {}

def _get_or_create_session(session_id: Optional[str]) -> tuple[str, Dict]:
    if session_id and session_id in _sessions:
        return session_id, _sessions[session_id]
    sid = session_id or datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    _sessions[sid] = {
        "messages": [],
        "created_at": datetime.now().isoformat(),
        "last_active": datetime.now().isoformat(),
    }
    return sid, _sessions[sid]


@app.get("/", response_class=HTMLResponse)
async def root():
    web_index = Path("web/index.html")
    if web_index.exists():
        return web_index.read_text(encoding="utf-8")
    return HTMLResponse(
        "<h1><<<name>>> AI Robot Service</h1>"
        "<p>API: <a href='/docs'>/docs</a></p>"
        "<p>Chat: POST /api/chat</p>"
    )


@app.get("/api/status", response_model=StatusResponse)
async def status():
    bot = await get_bot()
    uptime = (datetime.now() - _start_time).total_seconds()
    total_messages = sum(len(s["messages"]) for s in _sessions.values())
    return StatusResponse(
        status="running",
        bot_name=bot.name,
        uptime_seconds=uptime,
        message_count=total_messages,
        skills=bot.skills.list_skills(),
        model=f"{bot.config.model_provider}/{bot.config.model_name}",
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    bot = await get_bot()
    sid, session = _get_or_create_session(req.session_id)
    bot.messages = session["messages"]
    await bot._agentic_turn_api(req.message)
    session["messages"] = bot.messages
    session["last_active"] = datetime.now().isoformat()
    reply = ""
    for msg in reversed(bot.messages):
        if msg.get("role") == "assistant" and msg.get("content"):
            reply = msg["content"]
            break
    return ChatResponse(
        reply=reply,
        session_id=sid,
        timestamp=datetime.now().isoformat(),
    )


@app.get("/api/chat/stream")
async def chat_stream(message: str, session_id: Optional[str] = None, request: Request = None):
    bot = await get_bot()
    sid, session = _get_or_create_session(session_id)
    bot.messages = session["messages"]

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for chunk in bot._agentic_turn_stream(message):
                data = json.dumps({"type": "chunk", "content": chunk, "session_id": sid}, ensure_ascii=False)
                yield f"data: {data}\n\n"
            session["messages"] = bot.messages
            session["last_active"] = datetime.now().isoformat()
            done_data = json.dumps({"type": "done", "session_id": sid}, ensure_ascii=False)
            yield f"data: {done_data}\n\n"
        except Exception as e:
            err_data = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
            yield f"data: {err_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/sessions")
async def list_sessions():
    return {
        sid: {
            "created_at": s["created_at"],
            "last_active": s["last_active"],
            "message_count": len(s["messages"]),
        }
        for sid, s in _sessions.items()
    }


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    if session_id in _sessions:
        del _sessions[session_id]
        return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Session not found")


@app.get("/api/memory")
async def get_memory():
    bot = await get_bot()
    return {"summary": bot.memory.get_summary()}


@app.get("/api/skills")
async def get_skills():
    bot = await get_bot()
    return {"skills": bot.skills.list_skills()}


@app.on_event("startup")
async def startup_event():
    await get_bot()
    print(f"[✓] <<<name>>> AI Robot 后台服务已启动")
    print(f"[✓] API: http://localhost:{PORT}/docs")
    print(f"[✓] Web UI: http://localhost:{PORT}/")


def _write_pid():
    PID_FILE.write_text(str(os.getpid()))

def _read_pid() -> Optional[int]:
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except ValueError:
            pass
    return None

def _is_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def cmd_status():
    pid = _read_pid()
    if pid and _is_running(pid):
        print(f"[✓] 服务正在运行 (PID: {pid})")
        print(f"    API: http://localhost:{PORT}/docs")
        print(f"    Web: http://localhost:{PORT}/")
    else:
        print("[✗] 服务未运行")
        if PID_FILE.exists():
            PID_FILE.unlink()

def cmd_stop():
    pid = _read_pid()
    if pid and _is_running(pid):
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        if _is_running(pid):
            os.kill(pid, signal.SIGKILL)
        if PID_FILE.exists():
            PID_FILE.unlink()
        print(f"[✓] 服务已停止 (PID: {pid})")
    else:
        print("[✗] 服务未运行")
        if PID_FILE.exists():
            PID_FILE.unlink()

def cmd_daemon():
    if sys.platform == "win32":
        print("[!] Windows 不支持守护进程，请使用前台模式或 Windows 服务")
        print("    直接运行: python service.py")
        sys.exit(1)

    pid = _read_pid()
    if pid and _is_running(pid):
        print(f"[!] 服务已在运行 (PID: {pid})")
        sys.exit(1)

    try:
        if os.fork() > 0:
            sys.exit(0)
    except AttributeError:
        print("[!] 此平台不支持 fork，使用前台模式")
        cmd_foreground()
        return

    os.setsid()
    try:
        if os.fork() > 0:
            sys.exit(0)
    except AttributeError:
        pass

    with open(LOG_FILE, "a") as log:
        os.dup2(log.fileno(), sys.stdout.fileno())
        os.dup2(log.fileno(), sys.stderr.fileno())

    _write_pid()
    cmd_foreground()

def cmd_foreground():
    _write_pid()

    def _cleanup(sig, frame):
        if PID_FILE.exists():
            PID_FILE.unlink()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _cleanup)
    signal.signal(signal.SIGINT, _cleanup)

    uvicorn.run(app, host=HOST, port=PORT, log_level="info", access_log=False)


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--stop" in args:
        cmd_stop()
    elif "--status" in args:
        cmd_status()
    elif "--daemon" in args:
        print("[*] 以守护进程方式启动后台服务 …")
        print(f"[*] 日志: {LOG_FILE.absolute()}")
        print("[*] 停止: python service.py --stop")
        cmd_daemon()
    else:
        print("=" * 50)
        print("  <<<name>>> AI Robot 后台服务")
        print(f"  API 文档: http://localhost:{PORT}/docs")
        print(f"  Web  UI : http://localhost:{PORT}/")
        print("  按 Ctrl+C 停止服务")
        print("=" * 50)
        cmd_foreground()
