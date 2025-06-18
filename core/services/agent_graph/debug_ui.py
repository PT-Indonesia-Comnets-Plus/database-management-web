# -*- coding: utf-8 -*-
# filepath: c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\debug_ui.py

import streamlit as st
import json
from datetime import datetime
from typing import Dict, Any, List
import pandas as pd


def display_agent_debug_panel():
    """Display comprehensive agent debug information in Streamlit"""

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🔍 Agent Debug Panel")

    # Show/hide debug panel
    show_debug = st.sidebar.checkbox("Show Debug Info", value=False)

    if not show_debug:
        return

    # Get debug sessions from session state
    sessions = st.session_state.get('agent_debug_sessions', [])

    if not sessions:
        st.sidebar.info("No debug sessions recorded yet")
        return

    # Session selector
    session_options = [
        f"{s['session_id']} - {s['user_query'][:30]}..." for s in sessions]
    selected_idx = st.sidebar.selectbox(
        "Select Session",
        range(len(session_options)),
        format_func=lambda i: session_options[i],
        index=len(sessions) - 1  # Default to latest session
    )

    if selected_idx is not None:
        session = sessions[selected_idx]
        display_session_details(session)


def display_session_details(session: Dict[str, Any]):
    """Display detailed information about a specific session"""

    with st.sidebar.expander("📊 Session Overview", expanded=True):
        st.markdown(f"**Session ID:** {session['session_id']}")
        st.markdown(f"**User:** {session['username']}")
        st.markdown(f"**Query:** {session['user_query']}")
        st.markdown(f"**Start Time:** {session['start_time']}")
        st.markdown(f"**Total Steps:** {len(session['steps'])}")

        if session.get('total_execution_time_ms'):
            st.markdown(
                f"**Total Time:** {session['total_execution_time_ms']:.2f}ms")

        success_icon = "✅" if session.get('success', True) else "❌"
        st.markdown(f"**Status:** {success_icon}")

    # Tools used summary
    tools_used = set()
    for step in session['steps']:
        if step['step_type'] == 'TOOL_CALL' and step['data'].get('tool_name'):
            tools_used.add(step['data']['tool_name'])

    if tools_used:
        with st.sidebar.expander("🔧 Tools Used"):
            for tool in sorted(tools_used):
                st.markdown(f"• {tool}")

    # Step-by-step breakdown
    with st.sidebar.expander("📝 Execution Steps", expanded=False):
        for step in session['steps']:
            display_step_summary(step)


def display_step_summary(step: Dict[str, Any]):
    """Display summary of a single execution step"""

    # Step icon based on type and success
    if step['step_type'] == 'NODE_ENTRY':
        icon = "🚪"
    elif step['step_type'] == 'TOOL_CALL':
        icon = "🔧"
    elif step['step_type'] == 'TOOL_RESULT':
        icon = "📊"
    elif step['step_type'] == 'LLM_CALL':
        icon = "🤖"
    elif step['step_type'] == 'REFLECTION':
        icon = "🤔"
    elif step['step_type'] == 'DECISION':
        icon = "🎯"
    elif step['step_type'] == 'ERROR':
        icon = "💥"
    else:
        icon = "📌"

    success_indicator = "✅" if step['success'] else "❌"
    time_info = f" ({step['execution_time_ms']:.1f}ms)" if step.get(
        'execution_time_ms') else ""

    st.markdown(f"{icon} **{step['step_id']}** {success_indicator}")
    st.markdown(f"   {step['description']}{time_info}")

    # Show additional details for specific step types
    if step['step_type'] == 'TOOL_CALL' and step['data'].get('tool_name'):
        st.markdown(f"   🔧 Tool: `{step['data']['tool_name']}`")

    if step['step_type'] == 'REFLECTION':
        action = step['data'].get('reflection_action', 'UNKNOWN')
        st.markdown(f"   🎯 Action: {action}")
        if step['data'].get('suggested_tool'):
            st.markdown(f"   💡 Suggested: `{step['data']['suggested_tool']}`")

    if step['error_message']:
        st.markdown(f"   💥 Error: {step['error_message'][:100]}...")

    st.markdown("---")


def display_debug_metrics_dashboard():
    """Display comprehensive debug metrics in main area"""

    st.header("🔍 Agent Debug Dashboard")

    sessions = st.session_state.get('agent_debug_sessions', [])

    if not sessions:
        st.info("No debug sessions recorded yet")
        return

    # Metrics overview
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Sessions", len(sessions))

    with col2:
        successful_sessions = sum(
            1 for s in sessions if s.get('success', True))
        st.metric("Successful Sessions", successful_sessions)

    with col3:
        total_steps = sum(len(s['steps']) for s in sessions)
        avg_steps = total_steps / len(sessions) if sessions else 0
        st.metric("Avg Steps/Session", f"{avg_steps:.1f}")

    with col4:
        total_times = [s.get('total_execution_time_ms', 0)
                       for s in sessions if s.get('total_execution_time_ms')]
        avg_time = sum(total_times) / len(total_times) if total_times else 0
        st.metric("Avg Execution Time", f"{avg_time:.1f}ms")

    # Tools usage analysis
    st.subheader("🔧 Tools Usage Analysis")

    tool_usage = {}
    tool_success_rate = {}

    for session in sessions:
        for step in session['steps']:
            if step['step_type'] == 'TOOL_CALL':
                tool_name = step['data'].get('tool_name')
                if tool_name:
                    tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
            elif step['step_type'] == 'TOOL_RESULT':
                tool_name = step['data'].get('tool_name')
                if tool_name:
                    if tool_name not in tool_success_rate:
                        tool_success_rate[tool_name] = {
                            'success': 0, 'total': 0}
                    tool_success_rate[tool_name]['total'] += 1
                    if step['success']:
                        tool_success_rate[tool_name]['success'] += 1

    if tool_usage:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Tool Usage Count**")
            usage_df = pd.DataFrame(list(tool_usage.items()), columns=[
                                    'Tool', 'Usage Count'])
            st.dataframe(usage_df, hide_index=True)

        with col2:
            st.markdown("**Tool Success Rate**")
            success_data = []
            for tool, stats in tool_success_rate.items():
                success_rate = (stats['success'] / stats['total']
                                ) * 100 if stats['total'] > 0 else 0
                success_data.append(
                    {'Tool': tool, 'Success Rate (%)': f"{success_rate:.1f}%"})

            if success_data:
                success_df = pd.DataFrame(success_data)
                st.dataframe(success_df, hide_index=True)

    # Recent sessions table
    st.subheader("📊 Recent Sessions")

    if sessions:
        recent_sessions_data = []
        for session in sessions[-10:]:  # Show last 10 sessions
            tools_used = set()
            for step in session['steps']:
                if step['step_type'] == 'TOOL_CALL' and step['data'].get('tool_name'):
                    tools_used.add(step['data']['tool_name'])

            recent_sessions_data.append({
                'Session ID': session['session_id'],
                'User': session['username'],
                'Query': session['user_query'][:50] + '...' if len(session['user_query']) > 50 else session['user_query'],
                'Steps': len(session['steps']),
                'Tools Used': ', '.join(sorted(tools_used)),
                'Time (ms)': f"{session.get('total_execution_time_ms', 0):.1f}",
                'Success': "✅" if session.get('success', True) else "❌"
            })

        recent_df = pd.DataFrame(recent_sessions_data)
        st.dataframe(recent_df, hide_index=True, use_container_width=True)

    # Session details expander
    st.subheader("🔍 Session Details")

    session_options = [
        f"{s['session_id']} - {s['user_query'][:30]}..." for s in sessions]
    selected_session_idx = st.selectbox(
        "Select session for detailed view",
        range(len(session_options)),
        format_func=lambda i: session_options[i],
        index=len(sessions) - 1  # Default to latest
    )

    if selected_session_idx is not None:
        display_detailed_session_view(sessions[selected_session_idx])


def display_detailed_session_view(session: Dict[str, Any]):
    """Display detailed view of a specific session"""

    st.markdown(f"### Session: {session['session_id']}")

    # Session metadata
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"**User:** {session['username']}")
        st.markdown(f"**Start Time:** {session['start_time']}")

    with col2:
        st.markdown(f"**Total Steps:** {len(session['steps'])}")
        success_icon = "✅" if session.get('success', True) else "❌"
        st.markdown(f"**Status:** {success_icon}")

    with col3:
        if session.get('total_execution_time_ms'):
            st.markdown(
                f"**Total Time:** {session['total_execution_time_ms']:.2f}ms")
        if session.get('final_result'):
            st.markdown(
                f"**Final Result:** {session['final_result'][:100]}...")

    st.markdown(f"**User Query:** {session['user_query']}")

    # Steps timeline
    st.markdown("### 📝 Execution Timeline")

    for i, step in enumerate(session['steps']):
        with st.expander(f"{step['step_id']} - {step['description']}", expanded=(i == len(session['steps']) - 1)):
            col1, col2 = st.columns([1, 2])

            with col1:
                st.markdown(f"**Type:** {step['step_type']}")
                st.markdown(f"**Node:** {step['node_name']}")
                st.markdown(f"**Time:** {step['timestamp']}")
                if step.get('execution_time_ms'):
                    st.markdown(
                        f"**Duration:** {step['execution_time_ms']:.2f}ms")

                success_indicator = "✅ Success" if step['success'] else "❌ Failed"
                st.markdown(f"**Status:** {success_indicator}")

            with col2:
                st.markdown("**Step Data:**")
                if step['data']:
                    st.json(step['data'])

                if step['error_message']:
                    st.error(f"Error: {step['error_message']}")


def clear_debug_sessions():
    """Clear all debug sessions"""
    if 'agent_debug_sessions' in st.session_state:
        st.session_state.agent_debug_sessions = []
    st.success("Debug sessions cleared!")

# Export debug data


def export_debug_data():
    """Export debug data as JSON"""
    sessions = st.session_state.get('agent_debug_sessions', [])
    if sessions:
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_sessions': len(sessions),
            'sessions': sessions
        }
        return json.dumps(export_data, indent=2)
    return None
