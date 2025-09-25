const $ = s => document.querySelector(s);
const fab = $('#cbFab'), panel = $('#cbPanel'), closeBtn = $('#cbClose');
const stream = $('#cbStream'), input = $('#cbInput'), sendBtn = $('#cbSend');

let sessionId = localStorage.getItem("ecolite_session") || (crypto?.randomUUID?.() || String(Date.now()));
localStorage.setItem("ecolite_session", sessionId);

function openPanel() {
  panel.style.display = 'flex';
  if (stream.childElementCount === 0) {
    pushBot("👋 Hola, soy tu asistente de Ecolite. ¿Qué espacio quieres iluminar (oficina, piscina, bodega…)?");
  }
}
function closePanel() { panel.style.display = 'none'; }
fab.addEventListener('click', openPanel);
closeBtn.addEventListener('click', closePanel);

function el(t, c, h) { const n = document.createElement(t); if (c) n.className = c; if (h !== undefined) n.innerHTML = h; return n; }
function push(role, html) { const row = el('div', 'msg' + (role === 'me' ? ' me' : '')); row.appendChild(el('div', 'bubble', html)); stream.appendChild(row); stream.scrollTo({ top: stream.scrollHeight, behavior: 'smooth' }); }
function pushMe(text) { push('me', text); }
function pushBot(text) {
  const parsed = renderProductsIfAny(text); // { html, hasProducts }
  push('bot', parsed.html);

  if (parsed.hasProducts) {
    let ctx = '';
    if (/piscina|ip68|sumergible/i.test(text)) ctx = 'para piscina';
    else if (/riel|magn[eé]tico|track/i.test(text)) ctx = 'para riel magnético';
    else if (/12v/i.test(text)) ctx = '12V';
    else if (/24v/i.test(text)) ctx = '24V';
    addShowMoreContext(ctx);
  }
}

function typing(on = true) {
  let t = $('#typing');
  if (on && !t) { t = el('div', 'msg'); t.id = 'typing'; t.appendChild(el('div', 'bubble', 'Escribiendo…')); stream.appendChild(t); }
  if (!on && t) { t.remove(); }
  stream.scrollTo({ top: stream.scrollHeight, behavior: 'smooth' });
}

async function sendMessage() {
  const msg = (input.value || "").trim();
  if (!msg) return;
  pushMe(msg); input.value = "";
  typing(true);
  try {
    const res = await fetch("/chat/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: msg, session_id: sessionId })
    });
    const data = await res.json();
    typing(false);
    pushBot(data.reply);
  } catch (e) {
    typing(false);
    pushBot("⚠️ No me pude conectar, intenta de nuevo.");
  }
}
sendBtn.addEventListener('click', sendMessage);
input.addEventListener('keydown', e => { if (e.key === 'Enter') sendMessage(); });

function renderProductsIfAny(text) {
  const lines = text.split('\n').map(l => l.trim().replace(/^[-•]\s*/, '')).filter(Boolean);
  const prods = [];
  for (const l of lines) {
    const m = l.match(/^(.+?)\s+—\s+([$\d\.\,kK]+)\s+—\s+(https?:\/\/\S+)\s+—\s*(\S+)?$/);
    if (m) { prods.push({ name: m[1], price: m[2], url: m[3], img_url: m[4] || '' }); }
  }
  if (!prods.length) return { html: text, hasProducts: false };

  const html = `
    <div class="prod-inline">
      ${prods.map(p => `
        <div class="prod-item">
          <img src="${p.img_url || 'https://dummyimage.com/120x120/0b1325/ffffff&text=LED'}" alt="${p.name}">
          <div class="prod-info">
            <div class="prod-name">${p.name}</div>
            <div class="prod-price">${p.price}</div>
            <a class="prod-link" href="${p.url}" target="_blank" rel="noopener">Ver producto</a>
          </div>
        </div>
      `).join('')}
    </div>
  `;
  return { html, hasProducts: true };
}

function addShowMoreContext(ctxText) {
  const tpl = document.getElementById('tplShowMore');
  let node, btn;
  if (tpl && 'content' in tpl) {
    node = tpl.content.cloneNode(true);
    btn = node.querySelector('.cb-cta');
  } else {
    const wrap = document.createElement('div');
    wrap.className = 'msg';
    wrap.innerHTML = `<div class="bubble"><button class="cb-cta" type="button">Ver más</button></div>`;
    node = wrap;
    btn = wrap.querySelector('.cb-cta');
  }
  btn.dataset.context = (ctxText || '').trim();
  btn.addEventListener('click', () => {
    const extra = btn.dataset.context ? ` ${btn.dataset.context}` : '';
    input.value = `muestrame otras${extra}`;
    sendMessage();
  });
  if (node instanceof DocumentFragment) stream.appendChild(node); else stream.appendChild(node);
  stream.scrollTo({ top: stream.scrollHeight, behavior: 'smooth' });
}
