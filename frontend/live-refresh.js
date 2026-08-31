(() => {
  'use strict';

  const REFRESH_MS = 3 * 60 * 1000;
  const MAX_LIST_QUOTES = 10;
  const TAIPEI_TZ = 'Asia/Taipei';

  let refreshBusy = false;
  let lastRefreshAt = 0;
  let lastQuoteMap = new Map();

  function taipeiParts(date = new Date()) {
    const parts = new Intl.DateTimeFormat('en-CA', {
      timeZone: TAIPEI_TZ,
      year: 'numeric', month: '2-digit', day: '2-digit',
      weekday: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit',
      hourCycle: 'h23',
    }).formatToParts(date);
    return Object.fromEntries(parts.map(p => [p.type, p.value]));
  }

  function taipeiDateString(date = new Date()) {
    const p = taipeiParts(date);
    return `${p.year}-${p.month}-${p.day}`;
  }

  function isTradingWindow(date = new Date()) {
    const p = taipeiParts(date);
    if (p.weekday === 'Sat' || p.weekday === 'Sun') return false;
    const minutes = Number(p.hour) * 60 + Number(p.minute);
    return minutes >= 8 * 60 + 55 && minutes <= 13 * 60 + 35;
  }

  function timeLabel(date = new Date()) {
    return new Intl.DateTimeFormat('zh-TW', {
      timeZone: TAIPEI_TZ,
      hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
    }).format(date);
  }

  function ensureStatus() {
    const header = document.getElementById('hdr');
    if (!header) return null;

    let wrap = document.getElementById('live-refresh-status');
    if (wrap) return wrap;

    wrap = document.createElement('div');
    wrap.id = 'live-refresh-status';
    wrap.style.cssText = [
      'margin-left:auto', 'display:flex', 'align-items:center', 'gap:6px',
      'font-size:10px', 'color:var(--tx2)', 'white-space:nowrap',
    ].join(';');
    wrap.innerHTML = `
      <span id="live-refresh-dot" style="width:7px;height:7px;border-radius:50%;background:#8b949e;display:inline-block"></span>
      <span id="live-refresh-text">準備更新</span>
      <button id="live-refresh-button" type="button" title="立即更新"
        style="border:1px solid var(--bd);background:var(--bg3);color:var(--tx2);border-radius:5px;padding:1px 6px;cursor:pointer;font-size:11px">↻</button>`;
    header.appendChild(wrap);
    document.getElementById('live-refresh-button')?.addEventListener('click', () => refreshQuotes(true));
    return wrap;
  }

  function setStatus(kind, text) {
    ensureStatus();
    const dot = document.getElementById('live-refresh-dot');
    const label = document.getElementById('live-refresh-text');
    const button = document.getElementById('live-refresh-button');
    const colors = { live: '#3fb950', busy: '#f0ad4e', idle: '#8b949e', error: '#f85149' };
    if (dot) dot.style.background = colors[kind] || colors.idle;
    if (label) label.textContent = text;
    if (button) button.disabled = kind === 'busy';
  }

  function currentListIds() {
    const ids = [];
    if (typeof sel !== 'undefined' && sel?.id) ids.push(sel.id);

    document.querySelectorAll('#slist .si').forEach(el => {
      if (ids.length >= MAX_LIST_QUOTES) return;
      const id = el.id?.replace(/^si-/, '');
      if (id && !ids.includes(id)) ids.push(id);
    });

    if (!ids.length && typeof DEFAULT_IDS !== 'undefined') {
      DEFAULT_IDS.slice(0, MAX_LIST_QUOTES).forEach(id => ids.push(id));
    }
    return ids.slice(0, MAX_LIST_QUOTES);
  }

  function numberOr(value, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function applyListQuote(q) {
    const price = numberOr(q.price);
    const change = numberOr(q.change);
    const pct = numberOr(q.change_pct);
    if (!price) return;

    if (typeof priceCache !== 'undefined') {
      priceCache[q.id] = { close: price, chg: change, pct };
    }

    const pe = document.getElementById(`sp-${q.id}`);
    const ce = document.getElementById(`sc-${q.id}`);
    const cls = change >= 0 ? 'up' : 'dn';
    if (pe) {
      pe.textContent = price.toFixed(1);
      pe.className = `si-p ${cls}`;
    }
    if (ce) {
      ce.textContent = `${change >= 0 ? '+' : ''}${pct.toFixed(2)}%`;
      ce.className = `si-c ${cls}`;
    }
  }

  function mergeSelectedDailyQuote(q) {
    if (typeof sel === 'undefined' || sel?.id !== q.id || typeof fullData === 'undefined') return;
    if (!q.date || !q.price) return;

    const liveRow = {
      date: q.date,
      open: numberOr(q.open, q.price),
      max: numberOr(q.high, q.price),
      min: numberOr(q.low, q.price),
      close: numberOr(q.price),
      Trading_Volume: numberOr(q.volume_shares),
    };

    const index = fullData.findIndex(row => row.date === q.date);
    if (index >= 0) fullData[index] = { ...fullData[index], ...liveRow };
    else fullData.push(liveRow);
    fullData.sort((a, b) => String(a.date).localeCompare(String(b.date)));

    if (typeof updateAllRangePcts === 'function') updateAllRangePcts();

    const active = document.querySelector('.rb.on');
    const days = Number(active?.dataset?.d || 180);
    if (days > 5 && typeof renderRangeFromFull === 'function') {
      renderRangeFromFull(active);
    }

    if (typeof activeFundTab !== 'undefined' && activeFundTab === 'val' && typeof renderValuation === 'function') {
      renderValuation();
    }
  }

  function updateSelectedInfo(q) {
    if (typeof sel === 'undefined' || sel?.id !== q.id) return;

    const price = numberOr(q.price);
    const change = numberOr(q.change);
    const pct = numberOr(q.change_pct);
    const cls = change >= 0 ? 'up' : 'dn';
    const sign = change >= 0 ? '+' : '';

    const priceEl = document.getElementById('ibar-price');
    if (priceEl) {
      priceEl.textContent = price.toFixed(1);
      priceEl.className = cls;
    }
    if (typeof set === 'function') {
      set('iv-chg', `${sign}${change.toFixed(1)}`, cls);
      set('iv-pct', `${sign}${pct.toFixed(2)}%`, cls);
      set('iv-hi', numberOr(q.high, price).toFixed(1));
      set('iv-lo', numberOr(q.low, price).toFixed(1));
      const volume = numberOr(q.volume_shares);
      set('iv-vol', volume > 1e6 ? `${(volume / 1e6).toFixed(1)}M` : volume > 1e3 ? `${(volume / 1e3).toFixed(0)}K` : String(volume));
      set('iv-date', `${q.date || ''}${q.time ? ` ${q.time.slice(0, 5)}` : ''}`.trim());
    }

    const oneDay = document.getElementById('rp-1d');
    if (oneDay) {
      oneDay.textContent = `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`;
      oneDay.className = `rp ${pct >= 0 ? 'up' : 'dn'}`;
    }
  }

  function applyQuote(q) {
    lastQuoteMap.set(q.id, q);
    applyListQuote(q);
    mergeSelectedDailyQuote(q);
    updateSelectedInfo(q);
  }

  async function renderMinuteRange(days, button) {
    if (typeof sel === 'undefined' || !sel) return false;
    if (typeof setChartHint === 'function') setChartHint('載入分鐘資料…');

    try {
      const response = await fetch(`${API}/stock/${sel.id}/minutes?days=${days}&_=${Date.now()}`, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      if (!Array.isArray(data) || !data.length) throw new Error('no minute data');

      if (typeof setChartHint === 'function') setChartHint('');
      if (typeof drawMinuteChart === 'function') drawMinuteChart(data);

      const quote = lastQuoteMap.get(sel.id);
      if (quote) updateSelectedInfo(quote);
      else if (typeof updateIbar === 'function') {
        updateIbar(data[data.length - 1], data.length > 1 ? data[data.length - 2] : null, true);
      }

      const pctId = days === 1 ? 'rp-1d' : 'rp-5d';
      if (typeof setPct === 'function') setPct(pctId, +data[data.length - 1].close, +data[0].close);
      return true;
    } catch {
      if (typeof renderRangeFromFull === 'function' && button) renderRangeFromFull(button);
      return false;
    }
  }

  function installRangeOverrides() {
    const originalSwitchRange = window.switchRange;
    if (typeof originalSwitchRange === 'function') {
      window.switchRange = function liveSwitchRange(button) {
        const days = Number(button?.dataset?.d || 0);
        if (days !== 1 && days !== 5) return originalSwitchRange(button);

        document.querySelectorAll('.rb').forEach(b => b.classList.remove('on'));
        button.classList.add('on');
        if (typeof activeRangeBtn !== 'undefined') activeRangeBtn = button;
        if (typeof sel === 'undefined' || !sel) return;
        renderMinuteRange(days, button);
      };
    }

    const originalPickStock = window.pickStock;
    if (typeof originalPickStock === 'function') {
      window.pickStock = async function livePickStock(id, name) {
        await originalPickStock(id, name);
        await refreshQuotes(true);
        const active = document.querySelector('.rb.on');
        const days = Number(active?.dataset?.d || 0);
        if (days === 1 || days === 5) await renderMinuteRange(days, active);
      };
    }
  }

  async function refreshQuotes(force = false) {
    if (refreshBusy || document.hidden || !navigator.onLine) return;
    if (!force && !isTradingWindow()) {
      setStatus('idle', lastRefreshAt ? `已收盤 · ${timeLabel(new Date(lastRefreshAt))}` : '非交易時間');
      return;
    }

    const ids = currentListIds();
    if (!ids.length) return;

    refreshBusy = true;
    setStatus('busy', '更新中…');
    try {
      const response = await fetch(`/api/live/quotes?ids=${encodeURIComponent(ids.join(','))}&_=${Date.now()}`, {
        cache: 'no-store',
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      const quotes = Array.isArray(payload.quotes) ? payload.quotes : [];
      quotes.forEach(applyQuote);

      lastRefreshAt = Date.now();
      const today = taipeiDateString();
      const hasToday = quotes.some(q => q.date === today);
      if (isTradingWindow() && hasToday) setStatus('live', `盤中自動更新 · ${timeLabel()}`);
      else if (isTradingWindow()) setStatus('idle', `尚未有今日成交 · ${timeLabel()}`);
      else setStatus('idle', `最新資料 · ${timeLabel()}`);

      const active = document.querySelector('.rb.on');
      const days = Number(active?.dataset?.d || 0);
      if (typeof sel !== 'undefined' && sel && (days === 1 || days === 5)) {
        await renderMinuteRange(days, active);
      }
    } catch (error) {
      console.warn('Live quote refresh failed:', error);
      setStatus('error', '即時更新失敗');
    } finally {
      refreshBusy = false;
    }
  }

  function start() {
    ensureStatus();
    installRangeOverrides();
    setTimeout(() => refreshQuotes(true), 1200);
    setInterval(() => refreshQuotes(false), REFRESH_MS);

    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && Date.now() - lastRefreshAt > REFRESH_MS - 5000) refreshQuotes(true);
    });
    window.addEventListener('online', () => refreshQuotes(true));
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
})();
