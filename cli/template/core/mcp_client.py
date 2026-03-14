# core/mcp_client.py — MCP (Model Context Protocol) client wrapper

import json
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional


class MCPClient:
    '''
    Thin wrapper around MCP server processes.
    Reads server definitions from mcp/mcp_servers.json and can spawn
    servers on demand; tool invocation is handled via the mcp SDK.
    '''

    def __init__(self, config):
        self.config = config
        self._servers: Dict[str, dict] = {}
        self._load_server_config()

    def _load_server_config(self):
        cfg_path = Path(self.config.mcp_config_file)
        if cfg_path.exists():
            with open(cfg_path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
            self._servers = data.get('mcpServers', {})

    def list_servers(self) -> List[str]:
        return list(self._servers.keys())

    def call_tool(
        self, server_name: str, tool_name: str, arguments: Optional[Dict] = None
    ) -> Any:
        '''
        Invoke a tool on a given MCP server.
        Requires `mcp` Python SDK: pip install mcp
        '''
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            import asyncio

            server_cfg = self._servers.get(server_name)
            if not server_cfg:
                return f'MCP server {server_name!r} not configured.'

            params = StdioServerParameters(
                command=server_cfg['command'],
                args=server_cfg.get('args', []),
                env=server_cfg.get('env'),
            )

            async def _invoke():
                async with stdio_client(params) as (read, write):
                    async with ClientSession(read, write) as session:
                        await session.initialize()
                        result = await session.call_tool(
                            tool_name, arguments=arguments or {}
                        )
                        return result

            return asyncio.run(_invoke())
        except ImportError:
            return 'MCP SDK not installed. Run: pip install mcp'
        except Exception as exc:
            return f'MCP error: {exc}'
