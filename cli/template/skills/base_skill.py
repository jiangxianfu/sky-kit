# skills/base_skill.py — Base class every skill must inherit from

from typing import Any, Dict


class BaseSkill:
    name: str = 'base'
    description: str = 'Base skill — override this'

    def execute(self, **kwargs) -> Any:
        raise NotImplementedError

    def get_tool_definition(self) -> Dict:
        '''Return an OpenAI-compatible function-tool definition.'''
        return {
            'type': 'function',
            'function': {
                'name': self.name,
                'description': self.description,
                'parameters': {
                    'type': 'object',
                    'properties': {},
                    'required': [],
                },
            },
        }
