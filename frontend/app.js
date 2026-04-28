async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}

function pretty(el, data) {
  el.textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
}

const $ = (id) => document.getElementById(id);

async function runCognition() {
  const input = $('inputText').value || '';
  const out = await api('/cog/process', {
    method: 'POST',
    body: JSON.stringify({ data: input }),
  });
  pretty($('result'), out);
}

async function getStatus() {
  const s = await api('/status');
  pretty($('result'), s);
}

async function loadRules() {
  const r = await api('/cog/rules');
  $('rulesText').value = JSON.stringify(r.rules, null, 2);
}

async function saveRules() {
  let rules;
  try {
    rules = JSON.parse($('rulesText').value || '{}');
  } catch (e) {
    alert('Invalid JSON for rules');
    return;
  }
  const r = await api('/cog/rules', {
    method: 'PUT',
    body: JSON.stringify({ rules }),
  });
  $('rulesText').value = JSON.stringify(r.rules, null, 2);
}

async function memSnapshot() {
  const m = await api('/cog/memory');
  pretty($('memory'), m);
}

async function memClear() {
  await api('/cog/memory', { method: 'DELETE' });
  await memSnapshot();
}

async function getPrime() {
  const p = await api('/cog/prime');
  pretty($('prime'), p);
}

async function getSuggestions() {
  const s = await api('/cog/suggest');
  pretty($('sugg'), s);
}

async function syncUpdate() {
  const agent = $('agentName').value || 'Sentinel';
  let state = {};
  try { state = JSON.parse($('agentState').value || '{}'); } catch (e) { alert('Bad JSON'); return; }
  const out = await api('/sync/update', { method: 'POST', body: JSON.stringify({ agent, state }) });
  pretty($('syncOut'), out);
}

async function syncSnapshot() {
  const snap = await api('/sync/snapshot');
  pretty($('syncOut'), snap);
}

async function validateSymbols() {
  let sequence = [];
  try { sequence = JSON.parse($('glyphSeq').value || '[]'); } catch (e) { alert('Bad JSON'); return; }
  const res = await api('/symbols/validate', { method: 'POST', body: JSON.stringify({ sequence }) });
  pretty($('syncOut'), res);
}

async function bootSequence() {
  const res = await api('/symbols/boot');
  pretty($('syncOut'), res);
}

window.addEventListener('DOMContentLoaded', () => {
  $('runBtn').addEventListener('click', runCognition);
  $('statusBtn').addEventListener('click', getStatus);
  $('loadRules').addEventListener('click', loadRules);
  $('saveRules').addEventListener('click', saveRules);
  $('memSnap').addEventListener('click', memSnapshot);
  $('memClear').addEventListener('click', memClear);
  $('primeBtn').addEventListener('click', getPrime);
  $('suggBtn').addEventListener('click', getSuggestions);
  $('syncUpdate').addEventListener('click', syncUpdate);
  $('syncSnap').addEventListener('click', syncSnapshot);
  $('validateGlyphs').addEventListener('click', validateSymbols);
  $('bootSeq').addEventListener('click', bootSequence);
  // WebSocket live sync
  let ws = null;
  const connectWS = () => {
    if (ws && ws.readyState === WebSocket.OPEN) return;
    try {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws';
      // Optional API key via query param if set in localStorage
      const apiKey = localStorage.getItem('QNF_API_KEY');
      const qs = apiKey ? `?api_key=${encodeURIComponent(apiKey)}` : '';
      ws = new WebSocket(`${proto}://${location.host}/ws/sync${qs}`);
      ws.onopen = () => {
        $('wsConnect').textContent = 'WS Connected';
        $('wsConnect').disabled = true;
      };
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data);
          const prev = $('syncOut').textContent.trim();
          const next = (prev ? prev + "\n" : '') + JSON.stringify(data, null, 2);
          $('syncOut').textContent = next;
        } catch (e) {
          $('syncOut').textContent += `\n${ev.data}`;
        }
      };
      ws.onclose = () => {
        $('wsConnect').textContent = 'Connect WS';
        $('wsConnect').disabled = false;
      };
      ws.onerror = () => {
        $('syncOut').textContent += "\n[ws] error";
      };
    } catch (e) {
      $('syncOut').textContent += `\n[ws] failed: ${String(e)}`;
    }
  };
  $('wsConnect').addEventListener('click', connectWS);
  // initial loads
  loadRules().catch(console.error);
  memSnapshot().catch(console.error);
  // Profile controls
  $('loadProfile').addEventListener('click', async () => {
    try {
      const prof = await api('/profile_get');
      pretty($('profileOut'), prof);
    } catch (e) { pretty($('profileOut'), String(e)); }
  });
  $('reinitProfile').addEventListener('click', async () => {
    const ok = prompt('Type: Confirm Default Reset');
    if (ok !== 'Confirm Default Reset') return;
    try {
      const prof = await api('/profile_initialize', { method: 'POST' });
      pretty($('profileOut'), prof);
      alert('Sentinel profile reinitialized (Default Reset).');
    } catch (e) { alert(String(e)); }
  });
});
