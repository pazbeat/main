// Scripted screen recording of the imbir.kz certificate purchase flow.
// Usage: node record.js pc|mob
// Every narration line gets its own slot: actions run while the line is "spoken",
// then we wait until the line's audio length has elapsed. Output: rec_<dev>/frames/*.jpg + log.json
const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const fs = require('fs');
const DEV = process.argv[2] || 'pc';
const PC = DEV === 'pc';
const OUT = `rec_${DEV}`;
const LINES = JSON.parse(fs.readFileSync('lines.json', 'utf8'))[DEV];
fs.rmSync(OUT, {recursive: true, force: true}); fs.mkdirSync(`${OUT}/frames`, {recursive: true}); fs.mkdirSync(`${OUT}/shots`, {recursive: true});
const sleep = ms => new Promise(r => setTimeout(r, ms));
const now = () => Date.now() / 1000;
const log = {frames: [], shots: [], pointer: [], events: [], lines: [], viewport: null, dpr: null};

(async () => {
  const b = await chromium.launch();
  const opts = PC ? {viewport: {width: 1440, height: 768}, deviceScaleFactor: 1.5}
                  : {viewport: {width: 390, height: 844}, deviceScaleFactor: 3, isMobile: true, hasTouch: true};
  log.viewport = opts.viewport; log.dpr = opts.deviceScaleFactor;
  const ctx = await b.newContext({...opts, locale: 'ru-RU'});
  const p = await ctx.newPage();
  // pre-accept cookies so the banner never shows in the recording
  await p.goto('https://www.imbir.kz/ru', {waitUntil: 'networkidle'}); await sleep(1200);
  await p.getByRole('button', {name: /^Принять/}).first().click().catch(() => {});
  await sleep(500);
  await p.goto('https://www.imbir.kz/ru', {waitUntil: 'networkidle'}); await sleep(2500);
  const cdp = await ctx.newCDPSession(p);
  let fi = 0;
  cdp.on('Page.screencastFrame', async f => {
    const t = now(); const fn = `${OUT}/frames/${String(fi++).padStart(6, '0')}.jpg`;
    fs.writeFileSync(fn, Buffer.from(f.data, 'base64'));
    log.frames.push({t, f: fn, sy: f.metadata.scrollOffsetY || 0});
    cdp.send('Page.screencastFrameAck', {sessionId: f.sessionId}).catch(() => {});
  });
  const W = opts.viewport.width * opts.deviceScaleFactor, H = opts.viewport.height * opts.deviceScaleFactor;
  await cdp.send('Page.startScreencast', {format: 'jpeg', quality: 86, maxWidth: W, maxHeight: H, everyNthFrame: 1});
  p.setDefaultTimeout(5000);
  // parallel high-resolution stills (used whenever the screen is static)
  let rec = true, si = 0;
  const shooter = (async () => { while (rec) { const t = now(); const fn = `${OUT}/shots/${String(si++).padStart(6, '0')}.jpg`;
    try { await p.screenshot({path: fn, type: 'jpeg', quality: 88}); log.shots.push({t, t1: now(), f: fn}); } catch (e) {} await sleep(120); } })();

  // ---------- pointer helpers ----------
  let mx = PC ? 1060 : 200, my = PC ? 520 : 600;
  const plog = (x, y, kind = 'move') => log.pointer.push({t: now(), x, y, kind});
  const ease = k => k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
  async function moveTo(x, y, ms = 700) {
    if (!PC) { mx = x; my = y; return; }
    const x0 = mx, y0 = my, n = Math.max(8, Math.round(ms / 16)); const t0 = Date.now();
    for (let i = 1; i <= n; i++) { const k = ease(i / n); const cx = x0 + (x - x0) * k + Math.sin(k * Math.PI) * (y - y0) * .06, cy = y0 + (y - y0) * k;
      await p.mouse.move(cx, cy); plog(cx, cy); const target = t0 + ms * i / n; const d = target - Date.now(); if (d > 0) await sleep(d); }
    mx = x; my = y;
  }
  async function box(loc) { await loc.scrollIntoViewIfNeeded().catch(() => {}); await sleep(120); const bb = await loc.boundingBox(); if (!bb) throw new Error('no box'); return bb; }
  async function click(loc, {ms = 650, dx = .5, dy = .5, after = 350} = {}) {
    const bb = await box(loc); const x = bb.x + bb.width * dx, y = bb.y + bb.height * dy;
    if (PC) { await moveTo(x, y, ms); await sleep(140); plog(x, y, 'down'); log.events.push({t: now(), type: 'click', x, y}); await p.mouse.click(x, y); }
    else { await sleep(ms * .5); plog(x, y, 'tap'); log.events.push({t: now(), type: 'tap', x, y}); await p.touchscreen.tap(x, y); }
    await sleep(after); return bb;
  }
  async function hover(loc, ms = 600) { const bb = await box(loc); if (PC) await moveTo(bb.x + bb.width / 2, bb.y + bb.height / 2, ms); else await sleep(ms); return bb; }
  async function type(text, delay = 95) { for (const ch of text) { await p.keyboard.type(ch); await sleep(delay + (Math.random() - .5) * 40); } }
  async function focus(loc, pad = 30) { const bb = await box(loc).catch(() => null); if (bb) log.events.push({t: now(), type: 'focus', x: bb.x - pad, y: bb.y - pad, w: bb.width + pad * 2, h: bb.height + pad * 2}); return bb; }
  function unfocus() { log.events.push({t: now(), type: 'unfocus'}); }
  function ring(bb) { log.events.push({t: now(), type: 'ring', x: bb.x, y: bb.y, w: bb.width, h: bb.height}); }
  async function swipe(x0, y0, x1, y1, ms = 520) {
    const n = 22; log.events.push({t: now(), type: 'swipe', x0, y0, x1, y1, ms});
    await cdp.send('Input.dispatchTouchEvent', {type: 'touchStart', touchPoints: [{x: x0, y: y0}]}); plog(x0, y0, 'touch');
    for (let i = 1; i <= n; i++) { const k = ease(i / n); const x = x0 + (x1 - x0) * k, y = y0 + (y1 - y0) * k; await cdp.send('Input.dispatchTouchEvent', {type: 'touchMove', touchPoints: [{x, y}]}); plog(x, y, 'touch'); await sleep(ms / n); }
    await cdp.send('Input.dispatchTouchEvent', {type: 'touchEnd', touchPoints: []}); plog(x1, y1, 'up');
  }
  const T = (s, exact = true) => p.getByText(s, {exact}).locator('visible=true').first();
  const btn = re => p.getByRole('button', {name: re}).locator('visible=true').first();
  const inputs = () => p.locator('input:visible:not([type=checkbox]):not([type=radio]), textarea:visible');
  async function tapArcLabel(target, maxSteps = 8, arcY = 690, exact = true) {
    // mobile arcs: tap the visible label closest to the target direction until the target is centred
    for (let i = 0; i < maxSteps; i++) {
      const loc = p.locator('[role=listbox]:visible [role=option]').filter({hasText: new RegExp('^\\s*' + target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))}).first(); const bb = await loc.boundingBox().catch(() => null);
      if (bb && bb.x > 15 && bb.x + bb.width < 375 && bb.y > 80 && bb.y < 800) { await click(loc, {ms: 500, after: 800}); return; }
      // swipe the arc to bring more labels into view
      const dir = bb && bb.x < 20 ? -1 : 1; await swipe(195 + dir * 90, arcY, 195 - dir * 90, arcY, 560); await sleep(650);
    }
    throw new Error('arc label not reachable: ' + target);
  }

  // ---------- actions per narration line ----------
  const A = {
    wait: async () => {},
    home: async () => {
      if (PC) { await sleep(600); await click(p.locator('a.btn-gold:visible').first(), {ms: 1300, after: 200}); }
      else { await sleep(900); await click(p.locator('header button:visible').last(), {ms: 700, after: 1100}); await click(p.getByRole('link', {name: /Подарить сертификат/}).locator('visible=true').first(), {ms: 600, after: 200}); }
      await p.waitForURL(/create/); await p.waitForLoadState('networkidle').catch(() => {}); await sleep(700);
    },
    consent_read: async () => {
      const dlg = p.locator('[role=dialog]:visible, .modal:visible').first();
      await sleep(400); await focus(dlg, 16).catch(() => {});
      if (PC) { const bb = await dlg.boundingBox(); for (let i = 0; i < 4; i++) await moveTo(bb.x + 60 + i * 12, bb.y + 110 + i * 42, 700); }
      else { await sleep(1200); await swipe(200, 600, 200, 330, 900); await sleep(600); }
    },
    consent_accept: async () => {
      await click(p.locator('input[type=checkbox]').locator('visible=true').first().locator('xpath=..'), {ms: 700, after: 500}).catch(async () => click(p.locator('label:has(input[type=checkbox])').first()));
      await click(btn(/Принимаю/), {ms: 600, after: 600}); unfocus(); await sleep(600);
    },
    occasion: async () => {
      if (PC) await click(T('День рождения'), {ms: 900, after: 700});
      else { await tapArcLabel('Без повода', 3, 590); await tapArcLabel('День рождения', 6, 590); }
    },
    designs: async () => {
      if (PC) { const r = T('›'); await click(r, {ms: 800, after: 900}); await click(r, {ms: 250, after: 900}); }
      else { await swipe(250, 705, 130, 705, 480); await sleep(1000); await swipe(250, 705, 130, 705, 480); await sleep(800); }
    },
    next: async () => { await click(btn(/^Далее/), {ms: 700, after: 1100}); },
    program: async () => {
      if (PC) { await click(T('Ты и Я'), {ms: 900, after: 700}); await focus(T('70 000 ₸').locator('xpath=..'), 40).catch(() => {}); await hover(T('70 000 ₸'), 700).catch(() => {}); await sleep(1200); unfocus(); }
      else { await swipe(290, 690, 110, 690, 600); await sleep(800); await tapArcLabel('Ты и Я', 8, 690); await sleep(900); }
    },
    amount: async () => {
      await click(T('На сумму'), {ms: 800, after: 900});
      if (PC) await click(T('50 000 ₸', false), {ms: 900, after: 800});
      else await tapArcLabel('70 000', 6, 660);
    },
    name: async () => { const i = inputs().nth(0); await click(i, {ms: 800, after: 200}); await type('Айгерим', 120); await sleep(300); await focus(p.locator('.stg__plate, .stg__card').first(), 20).catch(() => {}); await sleep(1400); unfocus(); },
    from: async () => { const i = inputs().nth(1); await click(i, {ms: 600, after: 200}); await type('Данияр', 120); },
    greeting: async () => { await click(btn(/Добавить поздравление/), {ms: 700, after: 700}); const ta = p.locator('textarea:visible').first(); await click(ta, {ms: 500, after: 200}); await type('С днём рождения! Пусть этот день будет тёплым и спокойным.', 62); },
    branch: async () => { if (PC) { await click(T('Алматы'), {ms: 800, after: 900}); await click(T('Имбирь в ЖК «Шанырак»'), {ms: 800, after: 500}); } else { await tapArcLabel('Алматы', 5, 660); await click(p.locator('button:visible').filter({hasText: /Шанырак/}).first(), {ms: 500, after: 500}); } },
    when_now: async () => { await sleep(1800); const bb = await hover(PC ? T('Сразу после оплаты') : p.locator('button:visible').filter({hasText: /^\s*Сразу\s*$/}).first(), 800); ring(bb); },
    when_date: async () => { await click(PC ? T('В выбранную дату') : p.locator('button:visible').filter({hasText: /^\s*Выбрать дату\s*$/}).first(), {ms: 600, after: 800}); if (PC) { await focus(T('Дата и время отправки').locator('xpath=..'), 30).catch(() => {}); } await sleep(1500); unfocus(); },
    email_buyer: async () => { await click(PC ? T('Сразу после оплаты') : p.locator('button:visible').filter({hasText: /^\s*Сразу\s*$/}).first(), {ms: 500, after: 500}); const i = p.locator('input[type=email]:visible, input[placeholder*="mail"]:visible').nth(0); await click(i, {ms: 700, after: 200}); await type('you@example.com', 85); if (PC) await focus(T('Сюда придут сертификат и чек', false), 20).catch(() => {}); await sleep(1500); unfocus(); },
    email_rcpt: async () => { const i = p.locator('input[type=email]:visible, input[placeholder*="mail"]:visible').nth(1); await click(i, {ms: 700, after: 200}); await type('friend@example.com', 85); if (PC) await focus(T('Знаете почту того, кому дарите?', false), 20).catch(() => {}); await sleep(1600); unfocus(); },
    summary: async () => { await sleep(400); const s = T('Итого', false); const bb = await box(s).catch(() => null); if (bb) { if (PC) await moveTo(bb.x + 260, bb.y - 90, 900); } await sleep(1600); },
    promo: async () => { await click(btn(/Промокод/), {ms: 800, after: 800}); const i = p.locator('input:visible').filter({hasNot: p.locator('[type=checkbox]')}); const pi = p.locator('input[placeholder]:visible').last(); await click(pi, {ms: 500, after: 300}).catch(() => {}); await focus(pi, 40).catch(() => {}); await sleep(1500); unfocus(); },
    paymethod: async () => { await click(PC ? T('Карта', false) : p.locator('button:visible').filter({hasText: /^\s*Карта/}).first(), {ms: 800, after: 1200}); await click(PC ? T('Kaspi.kz', false) : p.locator('button:visible').filter({hasText: /Kaspi/}).first(), {ms: 600, after: 800}); },
    pay: async () => { const lab = p.locator('label:has(input[type=checkbox])').locator('visible=true').last(); const lb = await box(lab); const cb = p.locator('input[type=checkbox]').last(); const cbb = await cb.boundingBox().catch(() => null); const tx = cbb && cbb.width > 2 ? cbb.x + cbb.width / 2 : lb.x + 12, ty = cbb && cbb.width > 2 ? cbb.y + cbb.height / 2 : lb.y + 12;
      if (PC) { await moveTo(tx, ty, 800); await sleep(140); plog(tx, ty, 'down'); log.events.push({t: now(), type: 'click', x: tx, y: ty}); } else { log.events.push({t: now(), type: 'tap', x: tx, y: ty}); }
      await cb.check({force: true}).catch(() => {}); if (!(await cb.isChecked().catch(() => false))) await lab.click({position: {x: 10, y: 10}}).catch(() => {}); await sleep(600);
      const pb = btn(/Оплатить/); const bb = await hover(pb, 800); ring(bb); await sleep(1800); },
  };

  // ---------- run ----------
  let cur = null;
  for (const L of LINES) {
    if (L.kind !== 's') continue;
    const t0 = now(); log.lines.push({id: L.id, t0});
    try { await A[L.act](); } catch (e) { console.log('ACT FAIL', L.id, L.act, e.message.split('\n')[0]); }
    const need = L.dur + 0.45; const el = now() - t0; if (el < need) await sleep((need - el) * 1000);
    log.lines[log.lines.length - 1].t1 = now();
    console.log(L.id, 'slot', (now() - t0).toFixed(2), 'voice', L.dur.toFixed(2));
  }
  await sleep(600);
  rec = false; await shooter;
  await cdp.send('Page.stopScreencast');
  fs.writeFileSync(`${OUT}/log.json`, JSON.stringify(log));
  console.log('frames', log.frames.length);
  await b.close();
})();
