from typing import List, Dict, Any, Tuple


class ToolNormalizer:
    """
    Utility to normalize tool definitions between different LLM provider formats.
    Ensures that a single suite-native tool definition can be used across 
    OpenAI, Gemini, and Claude seamlessly.
    """

    @staticmethod
    def to_openai(shim_tools: List[Tuple[str, Any, str]]) -> List[Dict[str, Any]]:
        """Converts suite tools to OpenAI function format."""
        openai_tools = []
        for name, _, desc in shim_tools:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": desc,
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": [],
                        },
                    },
                }
            )
        return openai_tools

    @staticmethod
    def to_gemini(shim_tools: List[Tuple[str, Any, str]]) -> List[Dict[str, Any]]:
        """Converts suite tools to Google Gemini function_declarations format."""
        declarations = []
        for name, _, desc in shim_tools:
            declarations.append(
                {
                    "name": name,
                    "description": desc,
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {},
                        "required": [],
                    },
                }
            )
        # Gemini expects a list of tool objects, each containing function_declarations
        return [{"function_declarations": declarations}]

    @staticmethod
    def to_claude(shim_tools: List[Tuple[str, Any, str]]) -> List[Dict[str, Any]]:
        """Converts suite tools to Anthropic Claude tool format."""
        claude_tools = []
        for name, _, desc in shim_tools:
            claude_tools.append(
                {
                    "name": name,
                    "description": desc,
                    "input_schema": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                }
            )
        return claude_tools
