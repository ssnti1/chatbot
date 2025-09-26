// frontend/chatbox.js
const $ = s => document.querySelector(s);

const fab = $('#cbFab'), panel = $('#cbPanel'), closeBtn = $('#cbClose');
const stream = $('#cbStream'), input = $('#cbInput'), sendBtn = $('#cbSend');

let sessionId = localStorage.getItem("ecolite_session") || (crypto?.randomUUID?.() || String(Date.now()));
localStorage.setItem("ecolite_session", sessionId);

// Paginación 100% en cliente (server stateless)
let lastQuery = "";
let page = 0;
const PAGE_SIZE = 5;

function openPanel() {
  panel.style.display = 'flex';
  if (stream.childElementCount === 0) {
    pushBot("👋 Hola, soy tu asistente de Ecolite. ¿Qué necesitas iluminar hoy?");
  }
}
function closePanel() { panel.style.display = 'none'; }

fab.addEventListener('click', openPanel);
closeBtn.addEventListener('click', closePanel);

function el(t, c, h) { const n = document.createElement(t); if (c) n.className = c; if (h !== undefined) n.innerHTML = h; return n; }
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
function escapeAttr(s) { return escapeHtml(s).replace(/"/g, '&quot;'); }
function linkify(text) { return text.replace(/(https?:\/\/[^\s)]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>'); }

function push(role, html) {
  const row = el('div', 'msg' + (role === 'me' ? ' me' : ''));
  row.appendChild(el('div', 'bubble', html));
  stream.appendChild(row);
  stream.scrollTo({ top: stream.scrollHeight, behavior: 'smooth' });
}
function pushMe(text) { push('me', escapeHtml(text)); }

function renderProducts(items) {
  return `
  <div class="prod-inline">
    ${items.map(p => `
      <div class="prod-item">
        <a class="img-wrap" href="${escapeAttr(p.url || '#')}" target="_blank" rel="noopener">
          <img loading="lazy" src="${escapeAttr(p.img_url || '')}" alt="${escapeAttr(p.name || '')}">
        </a>
        <div class="prod-name">${escapeHtml(p.name || '')}</div>
        <div class="prod-price">${escapeHtml(p.price || '')}</div>
        <a class="prod-link" href="${escapeAttr(p.url || '#')}" target="_blank" rel="noopener">Ver producto</a>
      </div>
    `).join('')}
  </div>`;
}

function parseInlineProducts(text) {
  const lines = (text || "").split('\n').map(l => l.trim()).filter(Boolean);
  const out = [];
  for (const l of lines) {
    const m = l.match(/^(.+?)\s+—\s+([$\d\.\,kK]+)\s+—\s+(https?:\/\/\S+)\s+—\s*(\S+)?$/);
    if (m) out.push({ name: m[1], price: m[2], url: m[3], img_url: m[4] || '' });
  }
  return out;
}

function maybeToggleShowMore(products) {
  let btn = $('#cbShowMore');
  if (Array.isArray(products) && products.length === PAGE_SIZE) {
    if (!btn) {
      btn = el('button', 'show-more');
      btn.id = 'cbShowMore';
      btn.textContent = 'Ver más';
      btn.addEventListener('click', () => sendMessage('más', true));
      stream.appendChild(btn);
    }
  } else {
    if (btn) btn.remove();
  }
}

function pushBot(text, products = []) {
  const htmlParts = [];
  if (text && typeof text === 'string') htmlParts.push(`<div class="bot-text">${linkify(escapeHtml(text))}</div>`);
  const items = (Array.isArray(products) && products.length) ? products : parseInlineProducts(text);
  if (items.length) htmlParts.push(renderProducts(items));
  push('bot', htmlParts.join(''));
  maybeToggleShowMore(items);
}

function typing(on = true) {
  let t = $('#typing');
  if (on && !t) { t = el('div', 'msg'); t.id = 'typing'; t.appendChild(el('div', 'bubble', 'Escribiendo…')); stream.appendChild(t); }
  if (!on && t) { t.remove(); }
  stream.scrollTo({ top: stream.scrollHeight, behavior: 'smooth' });
}

async function sendMessage(raw, isShowMore = false) {
  const msg = (raw ?? input.value ?? "").trim();
  if (!msg && !isShowMore) return;

  let effectiveQuery = msg;
  if (isShowMore || /^m(a|á)s|ver\s+m(a|á)s|siguiente|continuar$/i.test(msg)) {
    if (!lastQuery) return;
    page += 1;
    effectiveQuery = lastQuery;
  } else {
    page = 0;
    lastQuery = msg;
  }

  if (!isShowMore) pushMe(msg);
  input.value = "";
  typing(true);

    try {
      const res = await fetch("/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: effectiveQuery, last_query: lastQuery, page })
      });

      // Lee cuerpo como texto primero (para mensajes de error no-JSON)
      const raw = await res.text();
      let data = null;
      try { data = raw ? JSON.parse(raw) : null; } catch { /* no JSON */ }

      if (!res.ok) {
        typing(false);
        const detail = (data && (data.detail || data.error || data.message)) || raw || "";
        console.error("Error /chat/:", res.status, detail);
        pushBot(`⚠️ Error del servidor (${res.status}). ${detail ? "Detalle: " + escapeHtml(String(detail)).slice(0, 240) : "Intenta de nuevo."}`);
        return;
      }

      typing(false);
      const text = (data && (data.content || data.reply)) || "Aquí tienes algunas opciones recomendadas:";
      const products = Array.isArray(data?.products) ? data.products : [];
      pushBot(text, products);

    } catch (e) {
      typing(false);
      console.error("Network error /chat/:", e);
      pushBot("⚠️ No me pude conectar, intenta de nuevo.");
    }
  }

sendBtn.addEventListener('click', () => sendMessage());
input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });
