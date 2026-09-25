// Frame-stepped (virtual time) capture of the imbir.kz purchase flow.
// The page clock is paused and advanced exactly 1/30 s before every high-res screenshot,
// so site animations are smooth and every frame is a crisp still. Usage: node record2.js pc|mob
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const DEV = process.argv[2] || 'pc'; const PC = DEV === 'pc';
const OUT = `rec2_${DEV}`; const FPS = 30, DT = 1000 / FPS;
const LINES = JSON.parse(fs.readFileSync('lines.json', 'utf8'))[DEV];
fs.rmSync(OUT, {recursive: true, force: true}); fs.mkdirSync(`${OUT}/f`, {recursive: true});
const sleep = ms => new Promise(r => setTimeout(r, ms));
const meta = {viewport: null, dpr: null, frames: [], lines: [], cams: []};

(async () => {
  const b = await chromium.launch();
  const opts = PC ? {viewport: {width: 1440, height: 768}, deviceScaleFactor: 1.5}
                  : {viewport: {width: 390, height: 844}, deviceScaleFactor: 3, isMobile: true, hasTouch: true};
  meta.viewport = opts.viewport; meta.dpr = opts.deviceScaleFactor;
  const ctx = await b.newContext({...opts, locale: 'ru-RU'});
  const p = await ctx.newPage(); p.setDefaultTimeout(8000);
  // cookies accepted beforehand (no banner in the recording)
  await p.goto('https://www.imbir.kz/ru', {waitUntil: 'networkidle'}); await sleep(1000);
  await p.getByRole('button', {name: /^Принять/}).first().click().catch(() => {});
  await sleep(400);
  await p.clock.install();
  const cdp = await ctx.newCDPSession(p);
  async function settle(url) {
    if (url) await p.goto(url, {waitUntil: 'networkidle'});
    else await p.waitForLoadState('networkidle').catch(() => {});
    await sleep(600);
    const now = await p.evaluate(() => Date.now()); await p.clock.pauseAt(now + 20);
    await cdp.send('Animation.enable').catch(() => {}); await cdp.send('Animation.setPlaybackRate', {playbackRate: 0.12}).catch(() => {});
    await p.evaluate(() => document.querySelectorAll('video').forEach(v => { try { v.pause(); v.currentTime = 2.2; } catch (e) {} })).catch(() => {});
  }
  await settle('https://www.imbir.kz/ru');

  // ---------- frame capture ----------
  let fi = 0; let mx = PC ? 1060 : 200, my = PC ? 520 : 600; let fx = [];   // fx: per-frame effects (click/tap/swipe/ring)
  async function frame() {
    await p.clock.runFor(DT);
    const fn = `${OUT}/f/${String(fi).padStart(6, '0')}.jpg`;
    await p.screenshot({path: fn, type: 'jpeg', quality: 90});
    meta.frames.push({p: [Math.round(mx * 10) / 10, Math.round(my * 10) / 10], fx}); fx = []; fi++;
  }
  async function wait(ms) { const n = Math.max(1, Math.round(ms / DT)); for (let i = 0; i < n; i++) await frame(); }
  const ease = k => k < .5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
  async function moveTo(x, y, ms = 700) {
    const x0 = mx, y0 = my, n = Math.max(6, Math.round(ms / DT));
    for (let i = 1; i <= n; i++) { const k = ease(i / n); mx = x0 + (x - x0) * k + Math.sin(k * Math.PI) * (y - y0) * .05; my = y0 + (y - y0) * k; if (PC) await p.mouse.move(mx, my); await frame(); }
  }
  // smooth scrolling of whatever container holds the element
  async function scrollTo(loc) {
    const h = await loc.elementHandle(); if (!h) return;
    const plan = await h.evaluate(el => { const r = el.getBoundingClientRect(); let s = el.parentElement; while (s && !(/(auto|scroll)/.test(getComputedStyle(s).overflowY) && s.scrollHeight > s.clientHeight + 2)) s = s.parentElement;
      const sc = s || document.scrollingElement; const vh = s ? s.getBoundingClientRect() : {top: 0, height: innerHeight}; const want = r.top + r.height / 2 - (vh.top + vh.height * .5);
      if (r.top > vh.top + 60 && r.bottom < vh.top + vh.height - 60) return null; window.__sc = sc; return {from: sc.scrollTop, delta: want}; });
    if (!plan) return;
    const n = Math.round(Math.min(900, 300 + Math.abs(plan.delta)) / DT);
    for (let i = 1; i <= n; i++) { const k = ease(i / n); await p.evaluate(v => { window.__sc.scrollTop = v; }, plan.from + plan.delta * k); await frame(); }
  }
  async function box(loc) { await scrollTo(loc).catch(() => {}); const bb = await loc.boundingBox(); if (!bb) throw new Error('no box'); return bb; }
  async function click(loc, {ms = 650, dx = .5, dy = .5, after = 350} = {}) {
    const bb = await box(loc); const x = bb.x + bb.width * dx, y = bb.y + bb.height * dy;
    if (PC) { await moveTo(x, y, ms); await wait(120); fx.push(['click', x, y]); await p.mouse.click(x, y); }
    else { await wait(ms * .5); mx = x; my = y; fx.push(['tap', x, y]); await p.touchscreen.tap(x, y); }
    await wait(after); return bb;
  }
  async function hover(loc, ms = 600) { const bb = await box(loc); if (PC) await moveTo(bb.x + bb.width / 2, bb.y + bb.height / 2, ms); else await wait(ms); return bb; }
  async function type(text, per = 3) { for (const ch of text) { await p.keyboard.type(ch); await wait(per * DT); } }
  async function swipe(x0, y0, x1, y1, ms = 520) {
    const n = Math.round(ms / DT);
    await cdp.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [{x: x0, y: y0}]}); fx.push(['touch', x0, y0]); await frame();
    for (let i = 1; i <= n; i++) { const k = ease(i / n); const x = x0 + (x1 - x0) * k, y = y0 + (y1 - y0) * k; await cdp.send('Input.dispatchTouchEvent', {type: 'touchMove', touchPoints: [{x, y}]}); fx.push(['touch', x, y]); await frame(); }
    await cdp.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []}); await frame();
  }
  // camera: rectangle (css px of the viewport) to frame, or null for the full page
  async function cam(loc, pad = 40) {
    if (loc === null) { meta.cams.push({f: fi, r: null}); return; }
    const bb = await loc.boundingBox().catch(() => null); if (bb) meta.cams.push({f: fi, r: [bb.x - pad, bb.y - pad, bb.width + 2 * pad, bb.height + 2 * pad]});
  }
  function ring(bb) { fx.push(['ring', bb.x, bb.y, bb.width, bb.height]); }
  const T = (s, exact = true) => p.getByText(s, {exact}).locator('visible=true').first();
  const btn = re => p.getByRole('button', {name: re}).locator('visible=true').first();
  const vbtn = re => p.locator('button:visible').filter({hasText: re}).first();
  const inputs = () => p.locator('input:visible:not([type=checkbox]):not([type=radio]), textarea:visible');
  const emailIn = k => p.locator('input[type=email]:visible, input[placeholder*="mail"]:visible').nth(k);
  async function arc(target, arcY, maxSteps = 8) {
    for (let i = 0; i < maxSteps; i++) {
      const loc = p.locator('[role=listbox]:visible [role=option]').filter({hasText: new RegExp('^\\s*' + target)}).first(); const bb = await loc.boundingBox().catch(() => null);
      if (bb && bb.x > 15 && bb.x + bb.width < 375 && bb.y > 80 && bb.y < 800) { await click(loc, {ms: 500, after: 700}); return; }
      const dir = bb && bb.x < 20 ? -1 : 1; await swipe(195 + dir * 90, arcY, 195 - dir * 90, arcY, 560); await wait(500);
    }
    throw new Error('arc: ' + target);
  }
  async function navigated() {   // a click that leaves the page: let the new page load in real time, then resume stepping
    await p.waitForURL(/create/, {timeout: 15000}); await settle(); await wait(200);
  }

  // ---------- actions ----------
  const A = {
    wait: async () => {},
    home: async () => {
      if (PC) { await wait(700); await click(p.locator('a.btn-gold:visible').first(), {ms: 1300, after: 150}); }
      else { await wait(900); await click(p.locator('header button:visible').last(), {ms: 700, after: 900}); await click(p.getByRole('link', {name: /Подарить сертификат/}).locator('visible=true').first(), {ms: 600, after: 150}); }
      await navigated();
    },
    consent_read: async () => {
      const dlg = p.locator('[role=dialog]:visible, .modal:visible').first(); await wait(300);
      if (PC) { await cam(dlg.locator('ul, ol').first(), 60); const bb = await dlg.boundingBox(); await wait(500); for (let i = 0; i < 4; i++) await moveTo(bb.x + 70 + i * 10, bb.y + 120 + i * 40, 750); }
      else { await wait(900); await swipe(200, 620, 200, 360, 1100); await wait(600); }
    },
    consent_accept: async () => {
      const cbl = p.locator('input[type=checkbox]').locator('visible=true').first().locator('xpath=..');
      if (PC) await cam(p.locator('[role=dialog]:visible, .modal:visible').first(), 30);
      await click(cbl, {ms: 800, after: 500}); await click(btn(/Принимаю/), {ms: 700, after: 300});
      if (PC) await cam(null); await wait(700);
    },
    occasion: async () => { if (PC) await click(T('День рождения'), {ms: 900, after: 700}); else { await arc('Без повода', 590, 3); await arc('День рождения', 590, 6); } },
    designs: async () => {
      if (PC) { const r = T('›'); await click(r, {ms: 800, after: 800}); await click(r, {ms: 250, after: 800}); }
      else { await swipe(250, 705, 130, 705, 520); await wait(900); await swipe(250, 705, 130, 705, 520); await wait(700); }
    },
    next: async () => { await click(btn(/^Далее/), {ms: 700, after: 900}); },
    program: async () => {
      if (PC) { await click(T('Ты и Я'), {ms: 900, after: 400}); await cam(T('70 000 ₸').locator('xpath=../..'), 60); await hover(T('70 000 ₸'), 700).catch(() => {}); await wait(1300); await cam(null); }
      else { await swipe(290, 690, 110, 690, 650); await wait(700); await arc('Ты и Я', 690); await wait(800); }
    },
    amount: async () => { await click(T('На сумму'), {ms: 800, after: 800}); if (PC) await click(T('50 000 ₸', false), {ms: 900, after: 700}); else await arc('70 000', 660, 6); },
    name: async () => { const i = inputs().nth(0); if (PC) await cam(p.locator('form:visible, .stg__content:visible').first(), 30).catch(() => {}); await click(i, {ms: 800, after: 150}); await type('Айгерим', 4); },
    from: async () => { await click(inputs().nth(1), {ms: 600, after: 150}); await type('Данияр', 4); },
    greeting: async () => { await click(btn(/Добавить поздравление/), {ms: 700, after: 500}); await click(p.locator('textarea:visible').first(), {ms: 500, after: 150}); await type('С днём рождения! Пусть этот день будет тёплым и спокойным.', 2); },
    branch: async () => {
      if (PC) await cam(null);
      if (PC) { await click(T('Алматы'), {ms: 800, after: 800}); await click(T('Имбирь в ЖК «Шанырак»'), {ms: 800, after: 400}); }
      else { await arc('Алматы', 660, 5); await click(vbtn(/Шанырак/), {ms: 500, after: 400}); }
    },
    when_now: async () => { await wait(1500); const bb = await hover(PC ? T('Сразу после оплаты') : vbtn(/^\s*Сразу\s*$/), 800); ring(bb); },
    when_date: async () => { await click(PC ? T('В выбранную дату') : vbtn(/^\s*Выбрать дату\s*$/), {ms: 600, after: 1400}); },
    email_buyer: async () => {
      await click(PC ? T('Сразу после оплаты') : vbtn(/^\s*Сразу\s*$/), {ms: 500, after: 400});
      if (PC) await cam(emailIn(0).locator('xpath=../..'), 90).catch(() => {});
      await click(emailIn(0), {ms: 700, after: 150}); await type('you@example.com', 3);
    },
    email_rcpt: async () => { if (PC) await cam(emailIn(1).locator('xpath=../..'), 90).catch(() => {}); await click(emailIn(1), {ms: 700, after: 150}); await type('friend@example.com', 3); await wait(500); },
    summary: async () => { if (PC) await cam(null); await wait(400); const bb = await box(T('Итого', false)).catch(() => null); if (bb && PC) await moveTo(bb.x + 260, bb.y - 90, 900); await wait(800); },
    promo: async () => { await click(btn(/Промокод/), {ms: 800, after: 500}); const pi = p.locator('input[placeholder]:visible').last(); if (PC) await cam(pi.locator('xpath=../..'), 120).catch(() => {}); await click(pi, {ms: 500, after: 800}).catch(() => {}); },
    paymethod: async () => { if (PC) await cam(T('Карта', false).locator('xpath=../..'), 120).catch(() => {}); await click(PC ? T('Карта', false) : vbtn(/^\s*Карта/), {ms: 800, after: 1000}); await click(PC ? T('Kaspi.kz', false) : vbtn(/Kaspi/), {ms: 600, after: 600}); },
    pay: async () => {
      const lab = p.locator('label:has(input[type=checkbox])').locator('visible=true').last(); await box(lab); const cb = p.locator('input[type=checkbox]').last();
      const lb = await lab.boundingBox(); const cbb = await cb.boundingBox().catch(() => null);
      const tx = cbb && cbb.width > 2 ? cbb.x + cbb.width / 2 : lb.x + 12, ty = cbb && cbb.width > 2 ? cbb.y + cbb.height / 2 : lb.y + 12;
      if (PC) { await cam(null); await moveTo(tx, ty, 800); await wait(120); } else await wait(300);
      fx.push([PC ? 'click' : 'tap', tx, ty]); await cb.check({force: true}).catch(() => {}); if (!(await cb.isChecked().catch(() => false))) await lab.click({position: {x: 10, y: 10}}).catch(() => {});
      await wait(500); const pb = btn(/Оплатить/); const bb = await hover(pb, 800); ring(bb); await wait(900);
    },
  };

  for (const L of LINES) {
    if (L.kind !== 's') continue;
    const f0 = fi; meta.lines.push({id: L.id, f0});
    try { await A[L.act](); } catch (e) { console.log('ACT FAIL', L.id, L.act, e.message.split('\n')[0]); }
    const need = Math.round((L.dur + 0.45) * FPS); if (fi - f0 < need) await wait((need - (fi - f0)) * DT);
    meta.lines[meta.lines.length - 1].f1 = fi;
    console.log(L.id, 'frames', fi - f0, 'voice', Math.round(L.dur * FPS));
  }
  await wait(400);
  fs.writeFileSync(`${OUT}/meta.json`, JSON.stringify(meta));
  console.log('total frames', fi);
  await b.close();
})();
