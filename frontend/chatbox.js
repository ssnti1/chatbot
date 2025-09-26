// frontend/chatbox.js
const $ = s => document.querySelector(s);

const fab = $('#cbFab'), panel = $('#cbPanel'), closeBtn = $('#cbClose');
const stream = $('#cbStream'), input = $('#cbInput'), sendBtn = $('#cbSend');

let sessionId = localStorage.getItem("ecolite_session") || (crypto?.randomUUID?.() || String(Date.now()));
localStorage.setItem("ecolite_session", sessionId);

// Estado 100% en cliente (stateless server)
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
function push(role, html) { const row = el('div', 'msg' + (role === 'me' ? ' me' : '')); row.appendChild(el('div', 'bubble', html)); stream.appendChild(row); stream.scrollTo({ top: stream.scrollHeight, behavior: 'smooth' }); }
function pushMe(text) { push('me', escapeHtml(text)); }

function pushBot(text, products = []) {
  const htmlParts = [];
  if (text && typeof text === 'string') htmlParts.push(`<div class="bot-text">${linkify(escapeHtml(text))}</div>`);
  if (Array.isArray(products) && products.length) htmlParts.push(renderProducts(products));
  push('bot', htmlParts.join(''));
  maybeToggleShowMore(products);
}

function typing(on = true) {
  let t = $('#typing');
  if (on && !t) { t = el('div', 'msg'); t.id = 'typing'; t.appendChild(el('div', 'bubble', 'Escribiendo…')); stream.appendChild(t); }
  if (!on && t) { t.remove(); }
  stream.scrollTo({ top: stream.scrollHeight, behavior: 'smooth' });
}

// ---- utilidades UI ----
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

// Saneado mínimo
function escapeHtml(s) { return String(s).replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
function escapeAttr(s) { return escapeHtml(s).replace(/"/g, '&quot;'); }
function linkify(text) { return text.replace(/(https?:\/\/[^\s)]+)/g, '<a href="$1" target="_blank" rel="noopener">$1</a>'); }

// ---- envío ----
async function sendMessage(raw, isShowMore = false) {
  const msg = (raw ?? input.value ?? "").trim();
  if (!msg && !isShowMore) return;

  // Gestión de paginación en cliente
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
      body: JSON.stringify({
        session_id: sessionId,
        message: effectiveQuery,
        last_query: lastQuery,
        page
      })
    });

    if (!res.ok) {
      typing(false);
      pushBot(`⚠️ Error del servidor (${res.status}). Intenta de nuevo.`);
      return;
    }

    const data = await res.json();
    typing(false);

    // Backend devuelve { content, products, page, last_query }
    const text = (data && (data.content || data.reply)) || "Aquí tienes algunas opciones recomendadas:";
    const products = Array.isArray(data?.products) ? data.products : [];

    // Fallback: si vinieran productos “embebidos” en texto con el formato Nombre — Precio — URL — IMG_URL
    const parsedFromText = (!products.length) ? parseInlineProducts(text) : [];
    pushBot(text, products.length ? products : parsedFromText);

  } catch (e) {
    typing(false);
    pushBot("⚠️ No me pude conectar, intenta de nuevo.");
  }
}

function parseInlineProducts(text) {
  if (!text || typeof text !== 'string') return [];
  const lines = text.split('\n').map(l => l.trim()).filter(Boolean);
  const out = [];
  for (const l of lines) {
    const m = l.match(/^(.+?)\s+—\s+([$\d\.\,kK]+)\s+—\s+(https?:\/\/\S+)\s+—\s*(\S+)?$/);
    if (m) out.push({ name: m[1], price: m[2], url: m[3], img_url: m[4] || '' });
  }
  return out;
}

sendBtn.addEventListener('click', () => sendMessage());
input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });
