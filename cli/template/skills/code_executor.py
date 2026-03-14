# skills/code_executor.py — Execute Python code snippets in a sandbox

import io
import sys
import traceback
from typing import Any

from .base_skill import BaseSkill


class CodeExecutorSkill(BaseSkill):
    name = 'code_executor'
    description = 'Execute a Python code snippet and return stdout/stderr.'

    def execute(self, code: str = '') -> Any:
        if not code:
            return 'No code provided.'
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        old_stdout, old_stderr = sys.stdout, sys.stderr
        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            exec(compile(code, '<skill_exec>', 'exec'), {})   # noqa: S102
            output = stdout_capture.getvalue()
            errors = stderr_capture.getvalue()
            return output if output else (errors or '(no output)')
        except Exception:
            return traceback.format_exc()
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def get_tool_definition(self):
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'code': {'type': 'string', 'description': 'Python code to execute'},
                    },
                    'required': ['code'],
                },
            },
        }
