# skills/web_search.py — Web search (configure your preferred backend)

from typing import Any

from .base_skill import BaseSkill


class WebSearchSkill(BaseSkill):
    name = 'web_search'
    description = 'Search the web for information.'

    def execute(self, query: str = '') -> Any:
        if not query:
            return 'No query provided.'
        # ── Option A: DuckDuckGo (no key needed, install duckduckgo-search) ──
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
            if not results:
                return 'No results found.'
            lines = []
            for r in results:
                lines.append(f'- {r["title"]}')
                lines.append(f'  {r["href"]}')
                lines.append(f'  {r["body"][:120]}')
            return chr(10).join(lines)
        except ImportError:
            pass
        # ── Option B: stub ────────────────────────────────────────────────────
        return (
            f'Web search for "{query}" — install duckduckgo-search '
            'or integrate your preferred search API here.'
        )

    def get_tool_definition(self):
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'query': {'type': 'string', 'description': 'Search query'},
                    },
                    'required': ['query'],
                },
            },
        }
