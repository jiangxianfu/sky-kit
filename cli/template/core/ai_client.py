# core/ai_client.py — Unified AI provider client
# Supports: OpenAI, Anthropic Claude, GitHub Copilot (GitHub Models)

from typing import Dict, List

from rich.console import Console

console = Console()


class AIClient:
    def __init__(
        self,
        provider: str,
        model: str,
        api_key: str,
        base_url: str = '',
    ):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self._openai_client = None
        self._anthropic_client = None
        self._init_client()

    # ── initialisation ──────────────────────────────────────────────────────

    def _init_client(self):
        if self.provider in ('openai', 'github-copilot'):
            try:
                from openai import OpenAI
                kwargs: dict = {'api_key': self.api_key or 'not-set'}
                if self.base_url:
                    kwargs['base_url'] = self.base_url
                self._openai_client = OpenAI(**kwargs)
            except ImportError:
                raise ImportError('OpenAI SDK missing. Run: uv add openai')
        elif self.provider == 'claude':
            if self.base_url:
                # Use OpenAI-compatible client when a custom base_url is set
                # (corporate gateways typically expose an OpenAI-compatible API)
                try:
                    from openai import OpenAI
                    self._openai_client = OpenAI(
                        api_key=self.api_key or 'not-set',
                        base_url=self.base_url,
                    )
                    self.provider = 'openai'  # redirect chat calls to OpenAI path
                except ImportError:
                    raise ImportError('OpenAI SDK missing. Run: uv add openai')
            else:
                try:
                    import anthropic
                    self._anthropic_client = anthropic.Anthropic(
                        api_key=self.api_key or 'not-set'
                    )
                except ImportError:
                    raise ImportError('Anthropic SDK missing. Run: uv add anthropic')
        else:
            raise ValueError(f'Unknown AI provider: {self.provider!r}')

    # ── public interface ────────────────────────────────────────────────────

    def chat(
        self,
        messages: List[Dict],
        system_prompt: str = '',
        stream: bool = True,
    ) -> str:
        if self.provider in ('openai', 'github-copilot'):
            return self._openai_chat(messages, system_prompt, stream)
        return self._claude_chat(messages, system_prompt, stream)

    def chat_with_tools(
        self,
        messages: List[Dict],
        system_prompt: str = '',
        tools: List[Dict] | None = None,
    ) -> tuple:
        """
        Returns (assistant_msg_dict, tool_calls_or_none).
        - tool_calls_or_none is None  → final text reply, display assistant_msg['content']
        - tool_calls_or_none is list  → [{id, name, arguments}], execute and call again
        """
        if self.provider in ('openai', 'github-copilot'):
            return self._openai_chat_with_tools(messages, system_prompt, tools or [])
        # Anthropic native path (no base_url): fall back to plain chat
        text = self._claude_chat(messages, system_prompt, stream=False)
        return {'role': 'assistant', 'content': text}, None

    # ── internal ─────────────────────────────────────────────────────────────

    def _openai_chat_with_tools(
        self, messages: List[Dict], system_prompt: str, tools: List[Dict]
    ) -> tuple:
        import json
        all_msgs: List[Dict] = []
        if system_prompt:
            all_msgs.append({'role': 'system', 'content': system_prompt})
        all_msgs.extend(messages)

        kwargs: dict = {'model': self.model, 'messages': all_msgs}
        if tools:
            kwargs['tools'] = tools
            kwargs['tool_choice'] = 'auto'

        resp = self._openai_client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message

        if msg.tool_calls:
            assistant_msg = {
                'role': 'assistant',
                'content': msg.content or '',
                'tool_calls': [
                    {
                        'id': tc.id,
                        'type': 'function',
                        'function': {'name': tc.function.name, 'arguments': tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            }
            parsed = []
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except Exception:
                    args = {}
                parsed.append({'id': tc.id, 'name': tc.function.name, 'arguments': args})
            return assistant_msg, parsed

        text = msg.content or ''
        return {'role': 'assistant', 'content': text}, None

    def _openai_chat(
        self, messages: List[Dict], system_prompt: str, stream: bool
    ) -> str:
        all_msgs: List[Dict] = []
        if system_prompt:
            all_msgs.append({'role': 'system', 'content': system_prompt})
        all_msgs.extend(messages)

        if stream:
            resp = self._openai_client.chat.completions.create(
                model=self.model, messages=all_msgs, stream=True
            )
            full = ''
            for chunk in resp:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    console.print(delta.content, end='', markup=False)
                    full += delta.content
            console.print()
            return full
        else:
            resp = self._openai_client.chat.completions.create(
                model=self.model, messages=all_msgs
            )
            return resp.choices[0].message.content

    def _claude_chat(
        self, messages: List[Dict], system_prompt: str, stream: bool
    ) -> str:
        kwargs: dict = {
            'model': self.model,
            'max_tokens': 4096,
            'messages': messages,
        }
        if system_prompt:
            kwargs['system'] = system_prompt

        if stream:
            full = ''
            with self._anthropic_client.messages.stream(**kwargs) as s:
                for text in s.text_stream:
                    console.print(text, end='', markup=False)
                    full += text
            console.print()
            return full
        else:
            resp = self._anthropic_client.messages.create(**kwargs)
            return resp.content[0].text
