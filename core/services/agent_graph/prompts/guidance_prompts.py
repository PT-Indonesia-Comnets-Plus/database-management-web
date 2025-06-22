# -*- coding: utf-8 -*-
# filepath: c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\prompts\guidance_prompts.py

"""
Guidance prompts for the agent graph.
Contains prompts used for reflection and retry guidance.
"""

from typing import Optional
from ..agent_backend import Reflection
from .prompt_config import TOOL_RELEVANCE_KEYWORDS, CONTEXT_CHANGE_KEYWORDS


class GuidancePrompts:
    """Centralized guidance prompts for reflection and retry mechanisms."""

    @staticmethod
    def get_reflection_guidance(reflection: Reflection) -> str:
        """
        Generate guidance prompt based on reflection results.

        Args:
            reflection (Reflection): The reflection object containing critique and suggestions.

        Returns:
            str: Formatted guidance prompt.
        """
        return f"""

IMPORTANT GUIDANCE FROM REFLECTION SYSTEM:
- Previous tool was incorrect: {reflection.critique}
- Recommended tool: {reflection.suggested_tool}
- Reasoning: {reflection.reasoning}

Please carefully consider this guidance when selecting the appropriate tool for this question.
Make sure to use the suggested tool if it's relevant to the user's question.
"""

    @staticmethod
    def get_tool_relevance_keywords() -> dict:
        """
        Get tool relevance mapping for determining if reflection guidance is still applicable.

        Returns:
            dict: Mapping of tool names to relevant keywords.
        """
        return TOOL_RELEVANCE_KEYWORDS

    @staticmethod
    def get_context_change_keywords() -> dict:
        """
        Get keywords for detecting context changes in user queries.

        Returns:
            dict: Keywords for different types of queries.
        """
        return CONTEXT_CHANGE_KEYWORDS
