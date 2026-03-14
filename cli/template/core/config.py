# core/config.py — Configuration loader
# Reads config/config.yaml and .env

import os
from pathlib import Path
from typing import List

import yaml
from dotenv import load_dotenv


class Config:
    def __init__(
        self,
        config_file: str = 'config/config.yaml',
        env_file: str = '.env',
    ):
        load_dotenv(env_file)
        self._data: dict = {}
        self._load(config_file)

    def _load(self, config_file: str):
        path = Path(config_file)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as fh:
                self._data = yaml.safe_load(fh) or {}

    @property
    def robot_name(self) -> str:
        return self._data.get('robot', {}).get('name', 'Sky')

    @property
    def model_provider(self) -> str:
        return self._data.get('ai', {}).get('provider', 'openai')

    @property
    def model_name(self) -> str:
        return self._data.get('ai', {}).get('model', 'gpt-4o-mini')

    @property
    def api_key(self) -> str:
        env_map = {
            'openai': 'OPENAI_API_KEY',
            'claude': 'ANTHROPIC_API_KEY',
            'github-copilot': 'GITHUB_TOKEN',
        }
        env_key = env_map.get(self.model_provider, 'API_KEY')
        return os.getenv(env_key) or self._data.get('ai', {}).get('api_key', '')

    @property
    def base_url(self) -> str:
        return self._data.get('ai', {}).get('base_url', '')

    @property
    def memory_dir(self) -> str:
        return self._data.get('memory', {}).get('dir', '.meta/memory')

    @property
    def skills_dir(self) -> str:
        return self._data.get('skills', {}).get('dir', 'skills')

    @property
    def enabled_skills(self) -> List[str]:
        return self._data.get('skills', {}).get('enabled', [])

    @property
    def enable_scheduler(self) -> bool:
        return self._data.get('scheduler', {}).get('enabled', True)

    @property
    def enable_mcp(self) -> bool:
        return self._data.get('mcp', {}).get('enabled', False)

    @property
    def mcp_config_file(self) -> str:
        return self._data.get('mcp', {}).get('config_file', 'mcp/mcp_servers.json')

    def update_robot_name(self, name: str):
        '''Persist an updated robot name to config.yaml.'''
        if 'robot' not in self._data:
            self._data['robot'] = {}
        self._data['robot']['name'] = name
        config_path = Path('config/config.yaml')
        if config_path.exists():
            with open(config_path, 'w', encoding='utf-8') as fh:
                yaml.dump(self._data, fh, allow_unicode=True, default_flow_style=False)
