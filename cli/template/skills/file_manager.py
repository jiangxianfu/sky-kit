# skills/file_manager.py — Read, write, patch and manage project files
# Merged with self_modifier: supports full file edits and partial patching.

from pathlib import Path
from typing import Any

from .base_skill import BaseSkill

# Paths that must never be modified by the AI (security guard)
_PROTECTED = {'.env', '.venv/', '__pycache__/'}


def _is_protected(path: str) -> bool:
    return any(str(path).startswith(p) for p in _PROTECTED)


class FileManagerSkill(BaseSkill):
    name = 'file_manager'
    description = (
        'Read, write, patch or delete any project file. '
        'Use action=patch to replace specific text inside a file without overwriting it entirely. '
        'Use action=write to overwrite the whole file. '
        'Use action=read to read a file. '
        'Use action=list to list files in a directory.'
    )

    def execute(
        self,
        action: str = 'read',
        path: str = '',
        content: str = '',
        old_text: str = '',
        new_text: str = '',
    ) -> Any:
        if action in ('write', 'patch', 'delete') and _is_protected(path):
            return f'Modification of {path!r} is not permitted.'

        fp = Path(path)

        if action == 'read':
            if not fp.exists():
                return f'File not found: {path}'
            return fp.read_text(encoding='utf-8')

        elif action == 'write':
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding='utf-8')
            return f'Written {len(content)} chars to {path}'

        elif action == 'patch':
            # Partial in-place replacement — find old_text and replace with new_text
            if not fp.exists():
                return f'File not found: {path}'
            if not old_text:
                return 'patch requires old_text to locate the section to replace.'
            original = fp.read_text(encoding='utf-8')
            if old_text not in original:
                return f'old_text not found in {path}. No changes made.'
            updated = original.replace(old_text, new_text, 1)
            fp.write_text(updated, encoding='utf-8')
            return f'Patched {path}: replaced {len(old_text)} chars with {len(new_text)} chars.'

        elif action == 'list':
            base = fp if fp.is_dir() else Path('.')
            files = [
                str(p) for p in base.rglob('*')
                if p.is_file() and not _is_protected(str(p))
            ]
            return files

        elif action == 'delete':
            if fp.exists():
                fp.unlink()
                return f'Deleted {path}'
            return f'File not found: {path}'

        else:
            return f'Unknown action: {action!r}. Use read / write / patch / list / delete.'

    def get_tool_definition(self):
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'action': {
                            'type': 'string',
                            'enum': ['read', 'write', 'patch', 'list', 'delete'],
                            'description': 'read=读文件 write=整体覆盖写入 patch=局部替换 list=列出文件 delete=删除',
                        },
                        'path': {'type': 'string', 'description': 'Relative file path'},
                        'content': {'type': 'string', 'description': 'Full content for write action'},
                        'old_text': {'type': 'string', 'description': 'Exact text to find (patch action)'},
                        'new_text': {'type': 'string', 'description': 'Replacement text (patch action)'},
                    },
                    'required': ['action', 'path'],
                },
            },
        }
