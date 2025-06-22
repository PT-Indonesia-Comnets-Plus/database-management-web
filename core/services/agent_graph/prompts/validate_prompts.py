# -*- coding: utf-8 -*-
# filepath: c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\prompts\validate_prompts.py

"""
Validation script for prompts module.
Run this script to verify all prompts are working correctly.
"""

import sys
import traceback
from typing import Dict, Any


def test_imports():
    """Test if all prompt modules can be imported correctly."""
    try:
        from . import prompt_manager, SystemPrompts, GuidancePrompts, AgentPrompts
        from .prompt_config import TOOL_RELEVANCE_KEYWORDS, AVAILABLE_TOOLS
        print("✅ All imports successful")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        traceback.print_exc()
        return False


def test_prompt_manager():
    """Test PromptManager functionality."""
    try:
        from . import prompt_manager

        # Test system prompts
        system_prompt = prompt_manager.get_main_system_prompt("test query")
        assert isinstance(system_prompt, str) and len(system_prompt) > 0

        final_prompt = prompt_manager.get_final_response_prompt()
        assert isinstance(final_prompt, str) and len(final_prompt) > 0

        # Test error handling
        error_msg = prompt_manager.get_error_response("Test error")
        assert "Test error" in error_msg

        # Test tool relevance
        is_relevant = prompt_manager.is_tool_relevant_to_query(
            "search_internal_documents", "apa itu iconnet")
        assert isinstance(is_relevant, bool)

        # Test context change detection
        context_changed = prompt_manager.detect_context_change(
            "hello", ["complex visualization query"])
        assert isinstance(context_changed, bool)

        print("✅ PromptManager tests passed")
        return True
    except Exception as e:
        print(f"❌ PromptManager tests failed: {e}")
        traceback.print_exc()
        return False


def test_system_prompts():
    """Test SystemPrompts functionality."""
    try:
        from .system_prompts import SystemPrompts

        # Test main system prompt
        main_prompt = SystemPrompts.get_main_system_prompt("test query")
        assert isinstance(main_prompt, str) and "test query" in main_prompt

        # Test final response prompt
        final_prompt = SystemPrompts.get_final_response_prompt()
        assert isinstance(
            final_prompt, str) and "ICONNET Assistant" in final_prompt

        print("✅ SystemPrompts tests passed")
        return True
    except Exception as e:
        print(f"❌ SystemPrompts tests failed: {e}")
        traceback.print_exc()
        return False


def test_guidance_prompts():
    """Test GuidancePrompts functionality."""
    try:
        from .guidance_prompts import GuidancePrompts
        from ..agent_backend import Reflection

        # Create mock reflection
        mock_reflection = Reflection(
            is_sufficient=False,
            critique="Tool was wrong",
            next_action="RETRY",
            suggested_tool="search_internal_documents",
            reasoning="Need internal docs"
        )

        # Test reflection guidance
        guidance = GuidancePrompts.get_reflection_guidance(mock_reflection)
        assert isinstance(
            guidance, str) and "search_internal_documents" in guidance

        # Test tool relevance keywords
        keywords = GuidancePrompts.get_tool_relevance_keywords()
        assert isinstance(
            keywords, dict) and "search_internal_documents" in keywords

        # Test context change keywords
        context_keywords = GuidancePrompts.get_context_change_keywords()
        assert isinstance(context_keywords,
                          dict) and "visualization" in context_keywords

        print("✅ GuidancePrompts tests passed")
        return True
    except Exception as e:
        print(f"❌ GuidancePrompts tests failed: {e}")
        traceback.print_exc()
        return False


def test_agent_prompts():
    """Test AgentPrompts functionality."""
    try:
        from .agent_prompts import AgentPrompts

        # Test error response template
        error_template = AgentPrompts.get_error_response_template()
        assert isinstance(error_template, str) and "{error}" in error_template

        # Test no messages response
        no_msg_response = AgentPrompts.get_no_messages_response()
        assert isinstance(no_msg_response, str)

        # Test context change messages
        context_messages = AgentPrompts.get_context_change_messages()
        assert isinstance(context_messages, dict)

        # Test debug messages
        debug_messages = AgentPrompts.get_debug_messages()
        assert isinstance(debug_messages, dict)

        print("✅ AgentPrompts tests passed")
        return True
    except Exception as e:
        print(f"❌ AgentPrompts tests failed: {e}")
        traceback.print_exc()
        return False


def test_prompt_config():
    """Test prompt configuration."""
    try:
        from .prompt_config import (
            TOOL_RELEVANCE_KEYWORDS,
            CONTEXT_CHANGE_KEYWORDS,
            AVAILABLE_TOOLS,
            TOOL_PRIORITY_HIERARCHY,
            COMPANY_QUERY_RULES
        )

        # Test tool relevance keywords
        assert isinstance(TOOL_RELEVANCE_KEYWORDS, dict)
        assert "search_internal_documents" in TOOL_RELEVANCE_KEYWORDS

        # Test context change keywords
        assert isinstance(CONTEXT_CHANGE_KEYWORDS, dict)
        assert "visualization" in CONTEXT_CHANGE_KEYWORDS

        # Test available tools
        assert isinstance(AVAILABLE_TOOLS, list)
        assert len(AVAILABLE_TOOLS) > 0

        # Test priority hierarchy
        assert isinstance(TOOL_PRIORITY_HIERARCHY, dict)
        assert "PRIMARY" in TOOL_PRIORITY_HIERARCHY

        # Test company rules
        assert isinstance(COMPANY_QUERY_RULES, list)
        assert len(COMPANY_QUERY_RULES) > 0

        print("✅ PromptConfig tests passed")
        return True
    except Exception as e:
        print(f"❌ PromptConfig tests failed: {e}")
        traceback.print_exc()
        return False


def run_integration_tests():
    """Run integration tests to verify the whole system works together."""
    try:
        from . import prompt_manager

        # Test query processing workflow
        test_queries = [
            "apa itu iconnet",
            "berapa jumlah pelanggan jakarta",
            "buatkan grafik data pelanggan",
            "cari informasi terbaru tentang AI"
        ]

        for query in test_queries:
            # Get system prompt
            system_prompt = prompt_manager.get_main_system_prompt(query)
            assert isinstance(system_prompt, str) and len(system_prompt) > 100

            # Check tool relevance for each query
            tools_to_check = ["search_internal_documents",
                              "query_asset_database", "create_visualization"]
            for tool in tools_to_check:
                relevance = prompt_manager.is_tool_relevant_to_query(
                    tool, query)
                assert isinstance(relevance, bool)

        # Test context change scenarios
        context_scenarios = [
            ("hello", ["create complex visualization with multiple charts"]),
            ("grafik", ["simple data query"]),
            ("apa itu iconnet", ["show me bar chart of customer data"])
        ]

        for current_query, previous_hints in context_scenarios:
            context_changed = prompt_manager.detect_context_change(
                current_query, previous_hints)
            assert isinstance(context_changed, bool)

        print("✅ Integration tests passed")
        return True
    except Exception as e:
        print(f"❌ Integration tests failed: {e}")
        traceback.print_exc()
        return False


def validate_prompts() -> Dict[str, bool]:
    """
    Run all validation tests for the prompts module.

    Returns:
        Dict[str, bool]: Test results for each component.
    """
    print("🚀 Starting prompts validation...")
    print("=" * 50)

    test_results = {
        "imports": test_imports(),
        "prompt_manager": test_prompt_manager(),
        "system_prompts": test_system_prompts(),
        "guidance_prompts": test_guidance_prompts(),
        "agent_prompts": test_agent_prompts(),
        "prompt_config": test_prompt_config(),
        "integration": run_integration_tests()
    }

    print("=" * 50)
    print("📊 Validation Results:")

    all_passed = True
    for test_name, result in test_results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if not result:
            all_passed = False

    print("=" * 50)
    if all_passed:
        print("🎉 All tests passed! Prompts module is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")

    return test_results


if __name__ == "__main__":
    results = validate_prompts()

    # Exit with error code if any tests failed
    if not all(results.values()):
        sys.exit(1)
    else:
        sys.exit(0)
