# core/memory_manager.py — Persistent conversation memory
# Storage layout: .meta/memory/yyyy-MM-dd/[topic].md

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class MemoryManager:
    def __init__(self, memory_dir: str = '.meta/memory'):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    # ── internal ────────────────────────────────────────────────────────────

    def _today_dir(self) -> Path:
        d = self.memory_dir / datetime.now().strftime('%Y-%m-%d')
        d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def _safe_name(s: str) -> str:
        return ''.join(c if c.isalnum() or c in '-_' else '_' for c in s)[:40]

    # ── save ────────────────────────────────────────────────────────────────

    def save_conversation(
        self,
        messages: List[Dict],
        session_id: Optional[str] = None,
        topic: str = 'chat',
    ) -> Path:
        '''Persist a conversation as a dated markdown file.'''
        if not session_id:
            session_id = datetime.now().strftime('%H%M%S')
        filename = f'{self._safe_name(topic)}_{session_id}.md'
        filepath = self._today_dir() / filename
        lines = [
            f'# {topic}',
            '',
            f'**Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  ',
            f'**Messages**: {len(messages)}',
            '',
            '---',
            '',
        ]
        for msg in messages:
            role = msg.get('role', 'unknown').capitalize()
            content = msg.get('content', '').strip()
            lines += [f'**{role}**', '', content, '', '---', '']
        filepath.write_text(chr(10).join(lines), encoding='utf-8')
        return filepath

    def save_note(self, note: str, topic: str = 'note') -> Path:
        '''Save a free-form note as a dated markdown file.'''
        ts = datetime.now().strftime('%H%M%S')
        filename = f'{self._safe_name(topic)}_{ts}.md'
        filepath = self._today_dir() / filename
        lines = [
            f'# {topic}',
            '',
            f'**Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            '',
            note,
            '',
        ]
        filepath.write_text(chr(10).join(lines), encoding='utf-8')
        return filepath

    # ── load ────────────────────────────────────────────────────────────────

    def load_recent_files(self, n: int = 5) -> List[Path]:
        '''Return n most recently modified .md files.'''
        all_md = sorted(
            self.memory_dir.rglob('*.md'),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return all_md[:n]

    def load_recent_sessions(self, n: int = 5) -> List[Dict]:
        '''Return brief metadata dicts for the n most recent memory files.'''
        return [
            {
                'file': str(fp),
                'date': fp.parent.name,
                'topic': fp.stem.rsplit('_', 1)[0],
                'preview': fp.read_text(encoding='utf-8')[:300],
            }
            for fp in self.load_recent_files(n)
        ]

    def search_memories(self, keyword: str) -> List[Dict]:
        '''Full-text search across all stored markdown files.'''
        results: List[Dict] = []
        kw = keyword.lower()
        for fp in self.memory_dir.rglob('*.md'):
            try:
                content = fp.read_text(encoding='utf-8')
                if kw in content.lower():
                    match_line = next(
                        (ln.strip() for ln in content.splitlines() if kw in ln.lower()),
                        '',
                    )
                    results.append({
                        'file': str(fp),
                        'date': fp.parent.name,
                        'topic': fp.stem.rsplit('_', 1)[0],
                        'match': match_line,
                    })
            except Exception:
                continue
        return results

    # ── summary ─────────────────────────────────────────────────────────────

    def get_summary(self) -> str:
        if not self.memory_dir.exists():
            return 'No memories yet.'
        by_date: Dict[str, int] = {}
        for fp in self.memory_dir.rglob('*.md'):
            date = fp.parent.name
            by_date[date] = by_date.get(date, 0) + 1
        if not by_date:
            return 'No memories yet.'
        lines = [f'Memory: {sum(by_date.values())} file(s) across {len(by_date)} day(s)']
        for date in sorted(by_date.keys(), reverse=True)[:5]:
            lines.append(f'  {date}: {by_date[date]} file(s)')
        return chr(10).join(lines)
