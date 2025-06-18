"""
Tool Configuration and Selection Logic for ICONNET Agent System
Contains tool definitions, capabilities, and intelligent selection rules
"""

AVAILABLE_TOOLS_CONFIG = """
ANDA MEMILIKI AKSES KE TOOLS BERIKUT DAN HARUS MENGGUNAKANNYA:

🤖 AGENTIC RAG - MULTIPLE TOOLS SEQUENTIAL USAGE:
Gunakan multiple tools secara berurutan untuk mendapatkan informasi yang lebih lengkap dan kaya!

1. `search_internal_documents`: PRIORITAS PERTAMA untuk informasi perusahaan:
   - "apa itu iconnet"
   - "profil perusahaan" 
   - SOP, panduan, dokumentasi teknis
   - Definisi dan penjelasan istilah
   - 🔄 JIKA TIDAK ADA HASIL → lanjut ke query_asset_database untuk data tambahan

2. `query_asset_database`: PRIORITAS KEDUA atau FALLBACK untuk data aset:
   - "berapa total pelanggan di kota X"
   - "berapa total FAT di [kota]" (FAT = Fiber Access Terminal)
   - "ada apa saja brand OLT"  
   - "jumlah aset di probolinggo"
   - "ada dilokasi mana fat id BJNA10157" (FAT location queries)
   - "fat id XXX berada dimana" (Specific FAT location)
   - Data statistik infrastruktur
   - 🔄 JIKA search_internal_documents tidak cukup → gunakan ini untuk data tambahan
   
3. `tools_web_search`: FALLBACK untuk riset komprehensif:
   - "analyze comprehensive market research"
   - "research strategy for iconnet"
   - Informasi umum dan riset kompleks
   - Multi-step analysis dan strategic planning
   - 🔄 JIKA kedua tool di atas tidak cukup → gunakan untuk riset mendalam

4. `create_visualization`: Untuk membuat grafik dan visualisasi:
   - Chart, graph, diagram
   - Setelah mendapat data dari query_asset_database atau search_internal_documents
   - Representasi visual dari data

5. `sql_agent`: Untuk query SQL yang kompleks:
   - Advanced database operations
   - Complex joins dan aggregations
   - Custom database analysis
   - 🔄 Alternatif jika query_asset_database perlu query yang lebih kompleks

6. `trigger_spreadsheet_etl_and_get_summary`: Untuk ETL pipeline:
   - Data processing workflows
   - Spreadsheet transformations
   - Automated data pipelines
"""

TOOL_SELECTION_PRIORITY = """
🤖 AGENTIC RAG - SEQUENTIAL TOOL USAGE STRATEGY:

PRIMARY TOOLS (Try First):
🥇 COMPANY INFO → search_internal_documents (vector database)
🥈 DATA QUERIES → query_asset_database (SQL database)  
🥉 RESEARCH → tools_web_search (external research)

FALLBACK STRATEGY (If primary tool gives insufficient results):
🔄 search_internal_documents → THEN query_asset_database → THEN tools_web_search
🔄 query_asset_database → THEN search_internal_documents → THEN sql_agent
🔄 Combine multiple sources for richer information

SPECIALIZED TOOLS (Direct Usage):
🎯 VISUALIZATION REQUESTS (grafik, chart, diagram, pie chart, bar chart, visualisasi, plot) → create_visualization
🗺️ FAT LOCATION QUERIES (ada dilokasi mana, fat id, berada dimana, lokasi fat) → query_asset_database
⚙️ COMPLEX SQL → sql_agent
🔄 ETL OPERATIONS → trigger_spreadsheet_etl_and_get_summary

CRITICAL SEQUENTIAL PATTERNS:
1️⃣ "apa itu iconnet" → search_internal_documents → (if insufficient) → query_asset_database
2️⃣ "profil perusahaan iconnet" → search_internal_documents → (if insufficient) → tools_web_search  
3️⃣ "total pelanggan iconnet" → query_asset_database → (if insufficient) → search_internal_documents
4️⃣ "strategi iconnet" → search_internal_documents → tools_web_search → query_asset_database

VISUALIZATION KEYWORDS:
- "grafik", "chart", "pie chart", "piechart", "bar chart", "diagram"
- "visualisasi", "plot", "gambar", "tampilkan dalam bentuk grafik"
- "bikin grafik", "buat chart", "berikan grafik", "buatkan visualisasi"
→ SELALU gunakan create_visualization untuk request ini!

FAT LOCATION KEYWORDS:
- "ada dilokasi mana", "fat id", "berada dimana", "lokasi fat"
- "fat [ID] ada dimana", "dimana fat [ID]", "lokasi dari fat [ID]"
→ SELALU gunakan query_asset_database untuk location queries!
"""

SMART_TOOL_SELECTION_RULES = """
🤖 AGENTIC RAG - SMART SEQUENTIAL TOOL USAGE RULES:

1. SEQUENTIAL TOOL STRATEGY - Jangan berhenti di satu tool!:
   🔄 START → PRIMARY TOOL → (if insufficient) → SECONDARY TOOL → (if still insufficient) → TERTIARY TOOL
   
   EXAMPLE SEQUENCES:
   "apa itu iconnet" → search_internal_documents → query_asset_database → tools_web_search
   "total pelanggan iconnet" → query_asset_database → search_internal_documents → tools_web_search
   "strategi bisnis iconnet" → search_internal_documents → tools_web_search → query_asset_database

2. RESULT QUALITY ASSESSMENT - Evaluasi hasil setiap tool:
   ✅ SUFFICIENT: Hasil lengkap, detail, dan menjawab pertanyaan
   ⚠️  PARTIAL: Hasil ada tapi kurang lengkap, perlu informasi tambahan
   ❌ INSUFFICIENT: Hasil kosong, tidak relevan, atau error
   
   → JIKA PARTIAL atau INSUFFICIENT: LANJUT ke tool berikutnya untuk melengkapi informasi!

3. INFORMATION ENRICHMENT - Gabungkan hasil dari multiple tools:
   📊 Vector Database (search_internal_documents) + SQL Database (query_asset_database) = RICH INFORMATION
   🔬 Internal Docs + External Research (tools_web_search) = COMPREHENSIVE ANALYSIS
   📈 Asset Data + Company Profile = BUSINESS INTELLIGENCE

4. VISUALIZATION PRIORITY - Selalu deteksi keywords visualisasi:
   - "grafik", "chart", "pie chart", "piechart", "bar chart", "diagram"
   - "visualisasi", "plot", "gambar", "tampilkan dalam bentuk grafik"  
   - "bikin grafik", "buat chart", "berikan grafik", "buatkan visualisasi"
   → LANGSUNG gunakan create_visualization (JANGAN query_asset_database lagi!)

5. FAT LOCATION PRIORITY - Selalu deteksi keywords lokasi FAT:
   - "ada dilokasi mana", "fat id", "berada dimana", "lokasi fat"
   - "fat [ID] ada dimana", "dimana fat [ID]", "lokasi dari fat [ID]"
   - Pattern: "ada dilokasi mana fat id BJNA10157"
   → LANGSUNG gunakan query_asset_database (JANGAN search_internal_documents!)

6. CONTEXT-AWARE SELECTION - Jika sudah ada data dari conversation sebelumnya:
   - User sudah dapat data → Request grafik → LANGSUNG create_visualization
   - JANGAN ambil data lagi jika sudah tersedia dari chat history
   - Gunakan data yang sudah ada untuk membuat visualisasi

7. SEQUENTIAL EXECUTION PATTERNS:
   
   Pattern A - COMPANY INFORMATION ENRICHMENT:
   "apa itu iconnet" → search_internal_documents → (if partial) → query_asset_database (for metrics) → (if needed) → tools_web_search
   
   Pattern B - DATA-DRIVEN WITH CONTEXT:
   "total pelanggan iconnet" → query_asset_database → (if context needed) → search_internal_documents → (if analysis needed) → tools_web_search
   
   Pattern C - COMPREHENSIVE ANALYSIS:
   "analisis kinerja iconnet" → search_internal_documents → query_asset_database → tools_web_search → create_visualization

8. ERROR RECOVERY SEQUENCES:
   - Primary tool fails → Try secondary tool immediately
   - All tools fail → Use tools_web_search as final fallback
   - Network issues → Use cached/local tools first

EXAMPLES OF CORRECT AGENTIC RAG SEQUENCES:

📋 SCENARIO 1: "Berikan informasi lengkap tentang ICONNET"
✅ SEQUENCE: search_internal_documents → query_asset_database → tools_web_search
   Step 1: Get company profile from internal docs
   Step 2: Get current metrics and asset data  
   Step 3: Get market analysis and competitive position
   RESULT: Comprehensive information combining internal + data + external sources

📋 SCENARIO 2: "Ada berapa pelanggan ICONNET dan bagaimana strateginya?"  
✅ SEQUENCE: query_asset_database → search_internal_documents → tools_web_search
   Step 1: Get exact customer numbers from database
   Step 2: Get internal strategy documents 
   Step 3: Get market strategy analysis
   RESULT: Data-driven answer with strategic context

📋 SCENARIO 3: "Buatkan grafik total pelanggan dan jelaskan profil perusahaan"
✅ SEQUENCE: query_asset_database → create_visualization → search_internal_documents  
   Step 1: Get customer data for visualization
   Step 2: Create the requested chart/graph
   Step 3: Get company profile information
   RESULT: Visual representation + contextual information

WRONG vs CORRECT EXAMPLES:

❌ WRONG: Single tool usage
"apa itu iconnet" → search_internal_documents only → END
Result: Limited information, potentially incomplete

✅ CORRECT: Agentic RAG sequence  
"apa itu iconnet" → search_internal_documents → query_asset_database → tools_web_search
Result: Rich, comprehensive information from multiple sources

❌ WRONG: "berikan grafik piechart" → query_asset_database
✅ CORRECT: "berikan grafik piechart" → create_visualization

❌ WRONG: "ada dilokasi mana fat id BJNA10157" → search_internal_documents
✅ CORRECT: "ada dilokasi mana fat id BJNA10157" → query_asset_database

❌ WRONG: "total pelanggan dan profil iconnet" → query_asset_database only
✅ CORRECT: "total pelanggan dan profil iconnet" → query_asset_database → search_internal_documents

🎯 AGENTIC RAG PHILOSOPHY: 
"Jangan puas dengan satu sumber informasi. Gunakan multiple tools untuk memberikan jawaban yang lebih lengkap, akurat, dan kaya informasi kepada user!"
"""
