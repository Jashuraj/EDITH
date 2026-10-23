"""Patch index.html with MCP, Local RAG, and ChannelBridge UI components."""

from pathlib import Path

html_path = Path("edith/ui/public/index.html")
content = html_path.read_text(encoding="utf-8")

mcp_rag_section = """
        <!-- OpenJarvis Upgrades: MCP & Local RAG & Messaging Channels -->
        <div class="border-t border-os-border/80 pt-3 space-y-3">
          <div class="text-[10px] font-bold text-os-cyan uppercase tracking-wider font-chakra">Advanced Modules (OpenJarvis Primitives)</div>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div class="bg-[#080d16] p-2.5 rounded border border-os-border">
              <label class="text-slate-300 text-[10px] block mb-1">MODEL CONTEXT PROTOCOL (MCP)</label>
              <div class="flex space-x-1.5 mb-1.5">
                <input type="text" id="mcp-server-url" placeholder="http://127.0.0.1:3000" class="flex-1 bg-[#0c1320] border border-os-border/90 rounded px-2 py-1 text-[11px] text-slate-200">
                <button class="px-2.5 py-1 bg-os-cyan/20 border border-os-cyan/60 hover:bg-os-cyan/30 text-os-cyan rounded text-[10px] font-bold" onclick="connectMCP()">Connect</button>
              </div>
              <div class="text-[9px] text-slate-400 font-mono" id="mcp-status-text">Status: Checking MCP servers...</div>
            </div>

            <div class="bg-[#080d16] p-2.5 rounded border border-os-border">
              <label class="text-slate-300 text-[10px] block mb-1">LOCAL RAG KNOWLEDGE BASE</label>
              <div class="flex space-x-1.5 mb-1.5">
                <input type="text" id="rag-index-path" placeholder="./docs or file.txt" class="flex-1 bg-[#0c1320] border border-os-border/90 rounded px-2 py-1 text-[11px] text-slate-200">
                <button class="px-2.5 py-1 bg-emerald-500/20 border border-emerald-500/60 hover:bg-emerald-500/30 text-emerald-400 rounded text-[10px] font-bold" onclick="indexRAG()">Index</button>
              </div>
              <div class="text-[9px] text-slate-400 font-mono" id="rag-status-text">Indexed: 0 docs · 0 chunks</div>
            </div>
          </div>

          <div class="bg-[#080d16] p-2 rounded border border-os-border flex items-center justify-between text-[10px] font-mono">
            <div class="flex items-center space-x-2">
              <span class="text-slate-400 font-bold">CHANNELS:</span>
              <span id="channel-wa-badge" class="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">WhatsApp</span>
              <span id="channel-tg-badge" class="px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">Telegram</span>
              <span id="channel-hook-badge" class="px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700">Webhook Active</span>
            </div>
            <span class="text-slate-500 text-[9px]">OpenAI API: :8794/v1</span>
          </div>
        </div>
"""

target_btn = '<div class="flex justify-end space-x-2 pt-2 border-t border-os-border/80">'
if target_btn in content and "MODEL CONTEXT PROTOCOL (MCP)" not in content:
    content = content.replace(target_btn, mcp_rag_section.strip() + "\n\n        " + target_btn, 1)

# Add JavaScript helpers for MCP and RAG
js_helpers = """
    async function loadMCPAndRAGStatus() {
      try {
        const mcpRes = await fetch('/api/mcp/status');
        if (mcpRes.ok) {
          const d = await mcpRes.json();
          const el = document.getElementById('mcp-status-text');
          if (el) el.textContent = `Connected Servers: ${d.servers.length} · Tools: ${d.tools_count}`;
        }
      } catch (_) {}

      try {
        const ragRes = await fetch('/api/rag/status');
        if (ragRes.ok) {
          const d = await ragRes.json();
          const el = document.getElementById('rag-status-text');
          if (el) el.textContent = `Indexed: ${d.indexed_documents} docs · ${d.indexed_chunks} chunks`;
        }
      } catch (_) {}

      try {
        const chanRes = await fetch('/api/channels/status');
        if (chanRes.ok) {
          const d = await chanRes.json();
          const waBadge = document.getElementById('channel-wa-badge');
          if (waBadge && d.channels.whatsapp.configured) {
            waBadge.className = 'px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700';
          }
          const tgBadge = document.getElementById('channel-tg-badge');
          if (tgBadge && d.channels.telegram.configured) {
            tgBadge.className = 'px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-700';
          }
        }
      } catch (_) {}
    }

    async function connectMCP() {
      const url = document.getElementById('mcp-server-url')?.value.trim();
      if (!url) return;
      logActivity(`Connecting to MCP server: ${url}`);
      try {
        const res = await fetch('/api/mcp/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url })
        });
        const d = await res.json();
        if (d.success) {
          logActivity(`MCP Connected: ${d.tools_count} new tools registered.`);
          loadMCPAndRAGStatus();
        } else {
          logActivity(`MCP Failed: ${d.error || 'Server error'}`);
        }
      } catch (err) {
        logActivity(`MCP error: ${err.message}`);
      }
    }

    async function indexRAG() {
      const pathVal = document.getElementById('rag-index-path')?.value.trim() || '.';
      logActivity(`Indexing documents into local RAG: ${pathVal}`);
      try {
        const res = await fetch('/api/rag/index', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: pathVal })
        });
        const d = await res.json();
        if (d.success) {
          logActivity(`RAG complete: ${d.indexed_count} items indexed.`);
          loadMCPAndRAGStatus();
        }
      } catch (err) {
        logActivity(`RAG index error: ${err.message}`);
      }
    }
"""

if "function loadMCPAndRAGStatus()" not in content:
    content = content.replace("async function loadProviderSettings() {", js_helpers + "\n    async function loadProviderSettings() {", 1)
    content = content.replace("if (name === 'settings') loadProviderSettings();", "if (name === 'settings') { loadProviderSettings(); loadMCPAndRAGStatus(); }", 1)

html_path.write_text(content, encoding="utf-8")
print("Patch successfully applied to index.html")
