# -*- coding: utf-8 -*-
# filepath: c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\debug_logger.py

import json
import time
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
import streamlit as st


logger = logging.getLogger('ICONNET_AGENT')


@dataclass
class AgentStep:
    """Represents a single step in agent execution"""
    step_id: str
    timestamp: str
    node_name: str
    step_type: str  # 'NODE_ENTRY', 'TOOL_CALL', 'LLM_CALL', 'REFLECTION', 'DECISION', 'ERROR'
    description: str
    data: Dict[str, Any]
    execution_time_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None


@dataclass
class AgentSession:
    """Represents an agent session with multiple steps"""
    session_id: str
    user_query: str
    username: str
    start_time: str
    steps: List[AgentStep]
    total_execution_time_ms: Optional[float] = None
    final_result: Optional[str] = None
    success: bool = True


class AgentDebugLogger:
    """Comprehensive debug logger for agent graph execution"""

    def __init__(self):
        self.current_session: Optional[AgentSession] = None
        self.step_counter = 0
        self.session_start_time = None

    def start_session(self, user_query: str, username: str = "Unknown") -> str:
        """Start a new agent session"""
        session_id = f"session_{int(time.time())}_{hash(user_query) % 10000}"
        self.session_start_time = time.time()

        self.current_session = AgentSession(
            session_id=session_id,
            user_query=user_query,
            username=username,
            start_time=datetime.now().isoformat(),
            steps=[]
        )

        self.step_counter = 0

        logger.info(f"🚀 NEW AGENT SESSION STARTED")
        logger.info(f"   Session ID: {session_id}")
        logger.info(f"   User: {username}")
        logger.info(f"   Query: {user_query}")
        logger.info(f"   Time: {self.current_session.start_time}")
        # Store in Streamlit session state for UI display
        if 'agent_debug_sessions' not in st.session_state:
            st.session_state.agent_debug_sessions = []

        return session_id

    def log_step(self,
                 node_name: str,
                 step_type: str,
                 description: str,
                 data: Dict[str, Any] = None,
                 success: bool = True,
                 error_message: str = None,
                 execution_time_ms: float = None) -> str:
        """Log a single step in agent execution"""

        if not self.current_session:
            logger.warning("⚠️ Attempted to log step without active session")
            # Create a minimal temporary session to avoid breaking the flow
            logger.info("🔧 Creating temporary session for orphaned log step")
            self.start_session(
                user_query="[Orphaned Step]",
                username="System"
            )

        self.step_counter += 1
        step_id = f"step_{self.step_counter:03d}"

        step = AgentStep(
            step_id=step_id,
            timestamp=datetime.now().isoformat(),
            node_name=node_name,
            step_type=step_type,
            description=description,
            data=data or {},
            execution_time_ms=execution_time_ms,
            success=success,
            error_message=error_message
        )

        self.current_session.steps.append(step)

        # Log to console with structured format
        status_icon = "✅" if success else "❌"
        time_info = f" ({execution_time_ms:.2f}ms)" if execution_time_ms else ""

        logger.info(f"{status_icon} [{step_id}] {node_name} | {step_type}")
        logger.info(f"   📝 {description}{time_info}")

        if data:
            # Log important data fields
            if 'tool_name' in data:
                logger.info(f"   🔧 Tool: {data['tool_name']}")
            if 'query' in data:
                logger.info(f"   🔍 Query: {data['query'][:100]}...")
            if 'result_summary' in data:
                logger.info(f"   📊 Result: {data['result_summary'][:100]}...")
            if 'reflection_action' in data:
                logger.info(f"   🤔 Reflection: {data['reflection_action']}")

        if error_message:
            logger.error(f"   💥 Error: {error_message}")

        return step_id

    def log_node_entry(self, node_name: str, input_data: Dict[str, Any] = None):
        """Log entry into a graph node"""
        return self.log_step(
            node_name=node_name,
            step_type="NODE_ENTRY",
            description=f"Entering {node_name} node",
            data={
                "input_data": self._sanitize_data(input_data),
                "node_type": "graph_node"
            }
        )

    def log_tool_call(self, tool_name: str, tool_args: Dict[str, Any], execution_time_ms: float = None):
        """Log a tool call"""
        return self.log_step(
            node_name="tools",
            step_type="TOOL_CALL",
            description=f"Executing tool: {tool_name}",
            data={
                "tool_name": tool_name,
                "tool_args": self._sanitize_data(tool_args),
                "execution_type": "tool_execution"
            },
            execution_time_ms=execution_time_ms
        )

    def log_tool_result(self, tool_name: str, result: Any, success: bool = True, error_message: str = None):
        """Log tool execution result"""
        result_summary = self._create_result_summary(result, tool_name)

        return self.log_step(
            node_name="tools",
            step_type="TOOL_RESULT",
            description=f"Tool {tool_name} {'completed' if success else 'failed'}",
            data={
                "tool_name": tool_name,
                "result_summary": result_summary,
                "result_type": type(result).__name__,
                "success": success
            },
            success=success,
            error_message=error_message
        )

    def log_llm_call(self, prompt_type: str, messages_count: int, execution_time_ms: float = None):
        """Log LLM invocation"""
        return self.log_step(
            node_name="chatbot",
            step_type="LLM_CALL",
            description=f"LLM call for {prompt_type}",
            data={
                "prompt_type": prompt_type,
                "messages_count": messages_count,
                "llm_type": "GoogleGenerativeAI"
            },
            execution_time_ms=execution_time_ms
        )

    def log_reflection(self, reflection_result: Any, suggested_tool: str = None):
        """Log reflection analysis"""
        return self.log_step(
            node_name="reflection_node",
            step_type="REFLECTION",
            description="Agent reflection analysis",
            data={
                "is_sufficient": getattr(reflection_result, 'is_sufficient', None),
                "next_action": getattr(reflection_result, 'next_action', None),
                "suggested_tool": suggested_tool,
                "critique": getattr(reflection_result, 'critique', '')[:200],
                "reflection_action": getattr(reflection_result, 'next_action', 'UNKNOWN')
            }
        )

    def log_decision(self, decision_point: str, decision: str, reasoning: str = ""):
        """Log routing and decision points"""
        return self.log_step(
            node_name="router",
            step_type="DECISION",
            description=f"Decision at {decision_point}: {decision}",
            data={
                "decision_point": decision_point,
                "decision": decision,
                "reasoning": reasoning
            }
        )

    def log_error(self, node_name: str, error: Exception, context: Dict[str, Any] = None):
        """Log errors with context"""
        return self.log_step(
            node_name=node_name,
            step_type="ERROR",
            description=f"Error in {node_name}: {str(error)}",
            data={
                "error_type": type(error).__name__,
                "error_details": str(error),
                "context": self._sanitize_data(context)
            },
            success=False,
            error_message=str(error)
        )

    def end_session(self, final_result: str = None, success: bool = True):
        """End the current session and calculate metrics"""
        if not self.current_session:
            logger.warning(
                "⚠️ Attempted to end session without active session")
            return

        if self.session_start_time:
            total_time = (time.time() - self.session_start_time) * 1000
            self.current_session.total_execution_time_ms = total_time

        self.current_session.final_result = final_result
        self.current_session.success = success

        # Log session summary
        logger.info(f"🏁 AGENT SESSION COMPLETED")
        logger.info(f"   Session ID: {self.current_session.session_id}")
        logger.info(f"   Success: {'✅' if success else '❌'}")
        logger.info(f"   Total Steps: {len(self.current_session.steps)}")
        logger.info(
            f"   Total Time: {self.current_session.total_execution_time_ms:.2f}ms")
        logger.info(f"   Tools Used: {self._get_tools_used()}")

        # Store completed session
        if 'agent_debug_sessions' in st.session_state:
            st.session_state.agent_debug_sessions.append(
                asdict(self.current_session))
            # Keep only last 10 sessions
            if len(st.session_state.agent_debug_sessions) > 10:
                st.session_state.agent_debug_sessions = st.session_state.agent_debug_sessions[-10:]

        self.current_session = None
        self.session_start_time = None

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        if not self.current_session:
            return {}

        return {
            "session_id": self.current_session.session_id,
            "user_query": self.current_session.user_query,
            "username": self.current_session.username,
            "total_steps": len(self.current_session.steps),
            "tools_used": self._get_tools_used(),
            "current_step": self.step_counter,
            "success": all(step.success for step in self.current_session.steps)
        }

    def _get_tools_used(self) -> List[str]:
        """Get list of tools used in current session"""
        if not self.current_session:
            return []

        tools = set()
        for step in self.current_session.steps:
            if step.step_type == "TOOL_CALL" and step.data.get("tool_name"):
                tools.add(step.data["tool_name"])
        return list(tools)

    def _sanitize_data(self, data: Any, max_length: int = 500) -> Any:
        """Sanitize data for logging (remove sensitive info, limit length)"""
        if data is None:
            return None

        if isinstance(data, str):
            if len(data) > max_length:
                return data[:max_length] + "..."
            return data

        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Skip sensitive fields
                if key.lower() in ['password', 'token', 'key', 'secret']:
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self._sanitize_data(
                        value, max_length // 2)
            return sanitized

        if isinstance(data, list):
            # Limit list size
            return [self._sanitize_data(item, max_length // 2) for item in data[:10]]

        return data

    def _create_result_summary(self, result: Any, tool_name: str) -> str:
        """Create a concise summary of tool result"""
        if result is None:
            return "No result"

        try:
            if isinstance(result, str):
                if tool_name == "create_visualization":
                    # Check if it's a Plotly JSON
                    try:
                        parsed = json.loads(result)
                        if 'data' in parsed and 'layout' in parsed:
                            return f"Plotly visualization created with {len(parsed.get('data', []))} traces"
                    except:
                        pass
                    return f"String result ({len(result)} chars)"
                else:
                    return f"String result: {result[:100]}..."

            if isinstance(result, dict):
                keys = list(result.keys())[:5]
                return f"Dict with keys: {keys}"

            if isinstance(result, list):
                return f"List with {len(result)} items"

            return f"{type(result).__name__}: {str(result)[:100]}..."

        except Exception as e:
            return f"Error summarizing result: {str(e)}"

    # Agent-specific logging methods
    def log_prompt_generation(self, prompt_type: str, query: str = "", context: Dict[str, Any] = None):
        """Log prompt generation with context"""
        self.log_step(
            node_name="prompt_system",
            step_type="PROMPT_GENERATION",
            description=f"Generated {prompt_type} prompt",
            data={
                "prompt_type": prompt_type,
                "query": query[:100] if query else "",
                "context": context or {}
            }
        )

    def log_tool_selection(self, suggested_tool: str, query: str, relevance_score: float = None):
        """Log tool selection decisions"""
        self.log_step(
            node_name="tool_selector",
            step_type="TOOL_SELECTION",
            description=f"Selected tool: {suggested_tool}",
            data={
                "selected_tool": suggested_tool,
                "query": query[:100],
                "relevance_score": relevance_score
            }
        )

    def log_context_change(self, current_query: str, previous_context: str, change_detected: bool):
        """Log context change detection"""
        self.log_step(
            node_name="context_analyzer",
            step_type="CONTEXT_ANALYSIS",
            description="Context change analysis",
            data={
                "current_query": current_query[:100],
                "previous_context": previous_context[:100] if previous_context else "",
                "context_changed": change_detected
            }
        )

    def log_reflection_decision(self, reflection_result: str, suggested_action: str, reasoning: str):
        """Log reflection and retry decisions"""
        self.log_step(
            node_name="reflection_node",
            step_type="REFLECTION",
            description="Agent reflection completed",
            data={
                "result": reflection_result,
                "suggested_action": suggested_action,
                "reasoning": reasoning[:200]
            }
        )


# Global logger instance
debug_logger = AgentDebugLogger()


def log_agent_step(*args, **kwargs):
    """Convenience function for logging agent steps"""
    return debug_logger.log_step(*args, **kwargs)


def log_agent_error(*args, **kwargs):
    """Convenience function for logging agent errors"""
    return debug_logger.log_error(*args, **kwargs)
