# -*- coding: utf-8 -*-
# filepath: c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\prompts\prompt_manager.py

"""
Prompt Manager for centralized prompt management.
Provides a single interface for accessing all prompts with configuration options.
"""

import re
from typing import Optional, Dict, Any
from .system_prompts import SystemPrompts
from .guidance_prompts import GuidancePrompts
from .agent_prompts import AgentPrompts
from ..agent_backend import Reflection

# Import debug logger untuk integration
try:
    from ..debug_logger import debug_logger
    LOGGER_AVAILABLE = True
except ImportError:
    LOGGER_AVAILABLE = False


class PromptManager:
    """
    Centralized prompt manager for the agent graph.
    Provides a single interface for all prompt operations.
    """

    def __init__(self):
        """Initialize the prompt manager."""
        self.system_prompts = SystemPrompts()
        self.guidance_prompts = GuidancePrompts()
        self.agent_prompts = AgentPrompts()

    # System Prompts
    def get_main_system_prompt(self, current_query: str = "") -> str:
        """Get the main system prompt with current query context."""
        if LOGGER_AVAILABLE:
            debug_logger.log_step(
                node_name="prompt_manager",
                step_type="PROMPT_GENERATION",
                description="Generating main system prompt",
                data={"query_length": len(
                    current_query), "has_query": bool(current_query)}
            )
        return self.system_prompts.get_main_system_prompt(current_query)

    def get_final_response_prompt(self) -> str:
        """Get the final response generation prompt."""
        return self.system_prompts.get_final_response_prompt()

    # Guidance Prompts
    def get_reflection_guidance(self, reflection: Reflection) -> str:
        """Get reflection guidance prompt."""
        return self.guidance_prompts.get_reflection_guidance(reflection)

    def get_tool_relevance_keywords(self) -> Dict[str, list]:
        """Get tool relevance keyword mapping."""
        return self.guidance_prompts.get_tool_relevance_keywords()

    def get_context_change_keywords(self) -> Dict[str, list]:
        """Get context change detection keywords."""
        return self.guidance_prompts.get_context_change_keywords()

    # Agent Prompts
    def get_error_response(self, error: str) -> str:
        """Get formatted error response message."""
        template = self.agent_prompts.get_error_response_template()
        return template.format(error=error)

    def get_no_messages_response(self) -> str:
        """Get no messages available response."""
        return self.agent_prompts.get_no_messages_response()

    def get_context_change_message(self, change_type: str, **kwargs) -> str:
        """Get context change message by type."""
        messages = self.agent_prompts.get_context_change_messages()
        template = messages.get(change_type, "Context changed")
        return template.format(**kwargs)

    def get_debug_message(self, message_type: str, **kwargs) -> str:
        """Get debug message by type."""
        messages = self.agent_prompts.get_debug_messages()
        template = messages.get(message_type, "Debug message")
        return template.format(**kwargs)

    # Utility Methods
    def is_tool_relevant_to_query(self, tool_name: str, query: str) -> bool:
        """
        Check if a tool is relevant to the current query based on keywords.

        Args:
            tool_name (str): Name of the tool to check.
            query (str): Current user query.            
        Returns:
            bool: True if tool is relevant to the query.
        """
        tool_keywords = self.get_tool_relevance_keywords()
        query_lower = query.lower()

        # SPECIAL HANDLING for query_asset_database with FAT ID queries
        if tool_name == 'query_asset_database':
            # Check for FAT ID patterns
            fat_id_pattern = r'\b[A-Z]{3,4}\d{3,4}\b'
            has_fat_id = bool(re.search(fat_id_pattern, query.upper()))

            # Check for location keywords
            location_keywords = ['dimana', 'letak', 'lokasi',
                                 'posisi', 'alamat', 'berada', 'terletak']
            has_location_keyword = any(
                kw in query_lower for kw in location_keywords)

            # Check for FAT-related keywords
            fat_keywords = ['fat', 'fat id', 'fatid', 'fdt', 'olt']
            has_fat_keyword = any(kw in query_lower for kw in fat_keywords)
            # If query contains FAT ID or related terms, it's ALWAYS relevant
            if has_fat_id or (has_fat_keyword and has_location_keyword):
                print(f"🎯 FAT ID query detected -> using query_asset_database")

                if LOGGER_AVAILABLE:
                    debug_logger.log_step(
                        node_name="prompt_manager",
                        step_type="TOOL_RELEVANCE_CHECK",
                        description=f"FORCED RELEVANCE for {tool_name} (FAT ID query)",
                        data={
                            "tool_name": tool_name,
                            "query": query[:100],
                            "is_relevant": True,
                            "reason": "FAT ID special handling"
                        }
                    )

                return True

        # Standard keyword-based relevance check
        if tool_name in tool_keywords:
            relevant_keywords = tool_keywords[tool_name]
            matched_keywords = [
                kw for kw in relevant_keywords if kw in query_lower]
            is_relevant = len(matched_keywords) > 0
            # Log tool relevance check
            if LOGGER_AVAILABLE:
                debug_logger.log_step(
                    node_name="prompt_manager",
                    step_type="TOOL_RELEVANCE_CHECK",
                    description=f"Checking relevance of {tool_name} for query",
                    data={"tool_name": tool_name,
                          "query": query[:100],
                          "is_relevant": is_relevant,
                          "matched_keywords": matched_keywords
                          }
                )
            return is_relevant
        else:
            return False

    def detect_context_change(self, current_query: str, previous_hints: list) -> bool:
        """
        Detect if the context has changed significantly between queries.
        Enhanced to handle follow-up location queries properly.

        Args:
            current_query (str): Current user query.
            previous_hints (list): Previous context hints from reflection.

        Returns:
            bool: True if context has changed significantly.
        """
        if not previous_hints:
            return False

        query_lower = current_query.lower()
        context_keywords = self.get_context_change_keywords()
        # Import thresholds from config
        from .prompt_config import CONTEXT_CHANGE_CONFIG

        simple_threshold = CONTEXT_CHANGE_CONFIG['simple_query_word_threshold']
        complex_threshold = CONTEXT_CHANGE_CONFIG['complex_hint_word_threshold']

        # SPECIAL CHECK: Disable context change for FAT ID queries AND location follow-ups
        fat_id_pattern = CONTEXT_CHANGE_CONFIG.get(
            'fat_id_pattern', r'\b[A-Z]{3,4}\d{3,4}\b')
        disable_fat_id = CONTEXT_CHANGE_CONFIG.get(
            'disable_context_change_for_fat_id', True)

        # Check if current query contains FAT ID
        has_fat_id = bool(re.search(fat_id_pattern, current_query.upper()))
        fat_keywords = ['fat', 'fat id', 'fatid', 'fdt', 'olt']
        has_fat_keyword = any(kw in query_lower for kw in fat_keywords)

        # Check for location-related follow-up queries
        location_followup_keywords = [
            'dimana', 'di mana', 'letak', 'lokasi', 'alamat', 'berada', 'terletak',
            'kota', 'kecamatan', 'kelurahan', 'provinsi', 'daerah', 'wilayah',
            'keluruhannya', 'kotanya', 'kecamatannya', 'tempatnya'
        ]
        has_location_followup = any(
            kw in query_lower for kw in location_followup_keywords)

        # Check if previous hints mention FAT ID or asset data
        previous_text = ' '.join(str(hint) for hint in previous_hints).lower()
        previous_mentions_fat = (
            bool(re.search(fat_id_pattern, previous_text.upper())) or
            any(kw in previous_text for kw in fat_keywords) or
            'asset' in previous_text or 'database' in previous_text
        )

        if disable_fat_id:
            # Disable context change for:
            # 1. Direct FAT ID queries
            # 2. Location follow-ups when previous context involved FAT/assets
            if has_fat_id or has_fat_keyword or (has_location_followup and previous_mentions_fat):
                if LOGGER_AVAILABLE:
                    debug_logger.log_step(
                        node_name="prompt_manager",
                        step_type="CONTEXT_CHANGE_DETECTION",
                        description="Context change DISABLED for FAT ID/location follow-up query",
                        data={
                            "query": current_query,
                            "reason": "FAT ID/location follow-up detected",
                            "has_fat_id": has_fat_id,
                            "has_fat_keyword": has_fat_keyword,
                            "has_location_followup": has_location_followup,
                            "previous_mentions_fat": previous_mentions_fat
                        }
                    )
                return False  # Never trigger context change for FAT ID/location queries

        # Check for visualization context change
        viz_keywords = context_keywords.get('visualization', [])
        has_viz_keyword = any(
            keyword in query_lower for keyword in viz_keywords)

        if has_viz_keyword:
            if LOGGER_AVAILABLE:
                debug_logger.log_step(
                    node_name="prompt_manager",
                    step_type="CONTEXT_CHANGE_DETECTION",
                    description="Visualization context change detected",
                    data={"query": current_query, "viz_keywords_found": True}
                )
            return True

        # Simple query check
        query_word_count = len(current_query.split())
        if query_word_count <= simple_threshold:
            hints_text = ' '.join(str(hint) for hint in previous_hints)
            hints_word_count = len(hints_text.split())

            if hints_word_count > complex_threshold:
                if LOGGER_AVAILABLE:
                    debug_logger.log_step(
                        node_name="prompt_manager",
                        step_type="CONTEXT_CHANGE_DETECTION",
                        description="Context change detected (simple query vs complex hints)",
                        data={
                            "query_words": query_word_count,
                            "hints_words": hints_word_count,
                            "simple_threshold": simple_threshold,
                            "complex_threshold": complex_threshold
                        }
                    )
                return True

        return False


# Create global instance for backward compatibility
prompt_manager = PromptManager()
