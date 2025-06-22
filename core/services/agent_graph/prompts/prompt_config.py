# -*- coding: utf-8 -*-
# filepath: c:\Users\rizky\OneDrive\Dokumen\GitHub\intern-iconnet\core\services\agent_graph\prompts\prompt_config.py

"""
Configuration file for prompts.
This file allows for easy modification of prompts without touching the code.
"""

# Tool relevance keywords configuration
TOOL_RELEVANCE_KEYWORDS = {
    'query_asset_database': [
        'berapa', 'total', 'jumlah', 'pelanggan', 'brand', 'data', 'kota',
        'dimana', 'letak', 'lokasi', 'posisi', 'alamat', 'berada', 'terletak',
        'fat', 'fdt', 'olt', 'fat id', 'fatid', 'cluster', 'koordinat',
        'latitude', 'longitude', 'tempat', 'area', 'wilayah', 'daerah'
    ],
    'create_visualization': [
        'grafik', 'chart', 'visualisasi', 'pie', 'bar', 'diagram', 'buat grafik', 'pie chart',
        'sekarang buat', 'buatkan chart', 'buatkan grafik', 'visualisasikan', 'tampilkan grafik',
        'chart nya', 'grafik nya', 'pie nya', 'bar chart', 'line chart'
    ],
    'search_internal_documents': [
        'panduan', 'dokumentasi', 'sop', 'cara', 'apa itu', 'iconnet', 'icon', 'plus',
        'pln', 'telkom', 'perusahaan', 'profil', 'fat', 'fdt', 'ont', 'olt',
        'definisi', 'jelaskan', 'adalah'
    ],
    'enhanced_web_research': [
        'informasi', 'berita', 'terbaru', 'internet', 'siapa', 'apa', 'kapan',
        'dimana', 'mengapa', 'bagaimana', 'pemenang', 'juara', 'terbaru', 'update', 'news'
    ],
    'enhanced_intent_analysis': ['analisis', 'strategi', 'pendekatan', 'kompleks', 'multi-step', 'rencana', 'optimal']
}

# Context change detection keywords
CONTEXT_CHANGE_KEYWORDS = {
    'visualization': [
        'grafik', 'chart', 'visualisasi', 'pie', 'bar', 'diagram', 'buat grafik', 'pie chart',
        'sekarang buat', 'buatkan chart', 'buatkan grafik', 'chart nya', 'grafik nya'
    ]
}

# Context change thresholds
CONTEXT_CHANGE_CONFIG = {
    'simple_query_word_threshold': 3,  # Queries with <= 3 words are considered simple
    # Hints with > 25 words are considered complex (lebih strict)
    'complex_hint_word_threshold': 25,
    'fat_id_pattern': r'\b[A-Z]{3,4}\d{3,4}\b',  # Pattern untuk FAT ID
    # Disable context change untuk FAT ID queries
    'disable_context_change_for_fat_id': True
}

# Available tools list for system prompt
AVAILABLE_TOOLS = [
    {
        'name': 'enhanced_intent_analysis',
        'description': 'For deep analysis of user intent and optimal tool selection planning (use FIRST for complex/unclear queries)'
    },
    {
        'name': 'tools_web_search',
        'description': 'For comprehensive web research with advanced citation handling (ONLY for external information)'
    },
    {
        'name': 'enhanced_web_research',
        'description': 'For basic web research (FALLBACK if tools_web_search fails due to quota)'
    },    {
        'name': 'query_asset_database',
        'description': 'For FAT ID location queries, asset data, database queries about location, counts, totals'
    },
    {
        'name': 'search_internal_documents',
        'description': 'For documentation and guides, technical term definitions (NOT for specific FAT ID locations), COMPANY INFORMATION'
    },
    {
        'name': 'create_visualization',
        'description': 'For creating charts and graphs'
    },
    {
        'name': 'trigger_spreadsheet_etl_and_get_summary',
        'description': 'For spreadsheet processing'
    },
    {
        'name': 'sql_agent',
        'description': 'For SQL database operations'
    }
]

# Priority hierarchy for tool selection
TOOL_PRIORITY_HIERARCHY = {
    'HIGHEST': {
        'category': 'FAT ID Lookup & Asset Location',
        'tool': 'query_asset_database',
        'examples': 'FAT ID, location queries, asset data, dimana letak fat'
    },
    'PRIMARY': {
        'category': 'Company/Product information',
        'tool': 'search_internal_documents',
        'examples': 'ICONNET, ICON Plus, PLN, company profiles'
    },
    'SECONDARY': {
        'category': 'Technical documentation',
        'tool': 'search_internal_documents',
        'examples': 'technical terms definitions'
    },
    'TERTIARY': {
        'category': 'External research',
        'tool': 'tools_web_search',
        'examples': 'general internet research'
    },
    'FALLBACK': {
        'category': 'Basic web research',
        'tool': 'enhanced_web_research',
        'examples': 'if quota exceeded'
    }
}

# Company-specific mandatory rules
COMPANY_QUERY_RULES = [
    "ANY query about ICONNET, ICON Plus, PLN, Telkom, company info → ALWAYS use 'search_internal_documents' FIRST",
    "Queries starting with 'apa itu' about company products → ALWAYS use 'search_internal_documents' FIRST",
    "Company profile, product information, technical terms → ALWAYS use 'search_internal_documents' FIRST"
]
