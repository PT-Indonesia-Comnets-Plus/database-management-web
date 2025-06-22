# -*- coding: utf-8 -*-
# filepath: c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\prompts\agent_prompts.py

"""
Agent-specific prompts for different phases of the agent lifecycle.
Contains prompts for error handling, debugging, and special cases.
"""


class AgentPrompts:
    """Centralized prompts for agent operations and error handling."""

    @staticmethod
    def get_error_response_template() -> str:
        """
        Get template for error response messages.

        Returns:
            str: Error response template.
        """
        return """Oops! 😅 Sepertinya ada kendala kecil saat saya memproses permintaan Anda. 

Tapi jangan khawatir, saya tetap di sini untuk membantu! Anda bisa:
✨ Coba tanyakan lagi dengan cara yang sedikit berbeda
🔄 Atau sampaikan pertanyaan lain yang ingin Anda ketahui

Saya siap membantu Anda kapan saja! 😊"""

    @staticmethod
    def get_no_messages_response() -> str:
        """
        Get response when no messages are available to process.

        Returns:
            str: No messages response.
        """
        return """Halo! 👋 Saya ICONNET Assistant yang siap membantu Anda. 

Silakan tanyakan apa saja tentang:
🏢 Informasi aset dan infrastruktur ICONNET
📍 Lokasi FAT ID atau perangkat jaringan
📊 Data dan statistik yang Anda butuhkan
📚 Dokumentasi dan panduan teknis
🌟 Layanan ICON Plus dan produk PLN

Ada yang bisa saya bantu hari ini? 😊"""

    @staticmethod
    def get_context_change_messages() -> dict:
        """
        Get messages for different types of context changes.

        Returns:
            dict: Context change message templates.
        """
        return {
            'visualization_to_simple': "�➡️💬 Baik, sekarang kita beralih dari visualisasi ke pertanyaan biasa ya!",
            'complex_to_simple': "🎯 Oke, pertanyaan kali ini lebih sederhana. Saya siap membantu!",
            'new_query_reset': "🔄 Pertanyaan baru terdeteksi - saya akan fokus ke pertanyaan ini ya!",
            'tool_not_relevant': "🎯 Saya akan menggunakan pendekatan yang lebih sesuai untuk pertanyaan '{tool}' ini"
        }

    @staticmethod
    def get_debug_messages() -> dict:
        """
        Get debug messages for logging and monitoring.

        Returns:
            dict: Debug message templates.
        """
        return {
            'building_graph': "Building Agent Graph v2.0...",
            'tools_bound': "Tools bound to LLM: {tools}",
            'calling_chatbot': "Calling Chatbot Node...",
            'generating_final': "🎯 Generating final response based on tool results...",
            'retrying_with_guidance': "🔄 Retrying with guidance for tool: {tool}",
            'llm_invocation_error': "Error in chatbot node during LLM invocation: {error}"
        }

    @staticmethod
    def get_followup_query_guidance() -> str:
        """
        Get guidance for handling follow-up queries effectively.

        Returns:
            str: Follow-up query guidance template.
        """
        return """FOLLOW-UP QUERY DETECTED: Pastikan untuk:
1. 🔍 Gunakan query_asset_database untuk semua pertanyaan lokasi/FAT ID
2. 📍 Berikan informasi lokasi yang lengkap dan spesifik
3. 🎯 Referensikan konteks percakapan sebelumnya
4. ✨ Jawab dengan ramah dan informatif"""

    @staticmethod
    def get_tool_enforcement_message(tool_name: str, query_type: str) -> str:
        """
        Get message for tool enforcement scenarios.

        Returns:
            str: Tool enforcement message.
        """
        return f"""🚫 TOOL ENFORCEMENT ACTIVATED
Tool Required: {tool_name}
Query Type: {query_type}
Forcing retry with correct tool selection..."""

    @staticmethod
    def get_session_context_prompt(fat_id: str) -> str:
        """
        Get session context prompt for FAT ID queries.

        Returns:
            str: Session context prompt.
        """
        return f"""KONTEKS SESI: Percakapan ini terkait dengan FAT ID {fat_id.upper()}
Pastikan semua pertanyaan follow-up tentang lokasi menggunakan database asset."""
