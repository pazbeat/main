  // occasion chips (PC) sit in one row under the card; their set changes with the season, so pick by position
  async function chips() {
    const all = await p.locator('button:visible').all(); const out = [];
    for (const b of all) { const bb = await b.boundingBox().catch(() => null); const t = (await b.innerText().catch(() => '')).trim(); if (bb && bb.y > 560 && bb.y < 670 && bb.x > 300 && bb.x < 1150 && t && !/[‹›]/.test(t)) out.push(b); }
    return out;
  }
  const A = {
    wait: async () => {},
    home: async () => {
      if (PC) { await wait(700); await click(p.locator('a.btn-gold:visible').first(), {ms: 1300, after: 150}); }
      else { await wait(700); await click(p.locator('header button:visible').last(), {ms: 700, after: 900}); await click(p.getByRole('link', {name: LBL.menu}).locator('visible=true').first(), {ms: 600, after: 150}); }
      await navigated();
    },
    consent: async () => {
      const dlg = p.locator('[role=dialog]:visible, .modal:visible').first(); await wait(300);
      if (PC) { await cam(dlg.locator('ul, ol').first(), 60); const bb = await dlg.boundingBox(); await wait(300); for (let i = 0; i < 2; i++) await moveTo(bb.x + 70 + i * 10, bb.y + 140 + i * 60, 650); }
      else { await wait(500); await swipe(200, 620, 200, 380, 900); await wait(300); }
      const cbl = p.locator('input[type=checkbox]').locator('visible=true').first().locator('xpath=..');
      if (PC) await cam(dlg, 30);
      await click(cbl, {ms: 700, after: 400}); await click(vbtn(LBL.accept), {ms: 600, after: 300});
      if (PC) await cam(null); await wait(500);
    },
    occasion: async () => {
      if (PC) { const c = await chips(); if (c.length > 1) await click(c[1], {ms: 800, after: 700}); if (c.length > 0) await click(c[0], {ms: 600, after: 600}); }
      else { const items = p.locator('.mob-lbl--occ:visible'); const t = (await items.nth(1).innerText().catch(() => '')).trim(); const t0 = (await items.nth(0).innerText().catch(() => '')).trim();
        if (t) await arc(new RegExp('^\\s*' + t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), 575, 3); if (t0) await arc(new RegExp('^\\s*' + t0.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')), 575, 3); }
    },
    designs: async () => {   // browse forward, then come back to the first card of the occasion
      if (PC) { await click(T('›'), {ms: 700, after: 700}); await click(T('‹'), {ms: 600, after: 700}); }
      else { await swipe(250, 695, 130, 695, 480); await wait(700); await swipe(130, 695, 250, 695, 480); await wait(500); }
    },
    next: async () => { await click(vbtn(LBL.next), {ms: 650, after: 800}); },
    program: async () => {
      if (PC) { await click(T(LBL.prog), {ms: 900, after: 400}); await cam(T(LBL.prog).locator('xpath=../..'), 60).catch(() => {}); await wait(1500); await cam(null); }
      else { await swipe(290, 690, 110, 690, 600); await wait(500); await arc(LBL.prog, 690); await wait(600); }
    },
    amount: async () => { await click(T(LBL.tabSum), {ms: 700, after: 700}); if (PC) await click(p.getByText(LBL.sumPc).locator('visible=true').first(), {ms: 800, after: 700}); else await arc(LBL.sumMob, 660, 6); },
    name: async () => { const i = inputs().nth(0); if (PC) await cam(p.locator('form:visible, .stg__content:visible').first(), 30).catch(() => {}); await click(i, {ms: 700, after: 150}); await type(LBL.n1, 3); },
    from: async () => { await click(inputs().nth(1), {ms: 500, after: 150}); await type(LBL.n2, 3); },
    greeting: async () => { await click(vbtn(LBL.greet), {ms: 600, after: 400}); await click(p.locator('textarea:visible').first(), {ms: 400, after: 150}); await type(LBL.msg, 1); },
    branch: async () => {
      if (PC) await cam(null);
      if (PC) await click(T(LBL.city), {ms: 700, after: 700}); else await arc(LBL.city, 660, 5);
      await click(vbtn(LBL.salon), {ms: 600, after: 400}).catch(() => {});
    },
    when_now: async () => { await wait(600); const bb = await hover(PC ? T(LBL.nowPc) : vbtn(new RegExp(LBL.nowPc.split(' ')[0])), 700); ring(bb); },
    when_date: async () => { await click(PC ? T(LBL.datePc) : vbtn(new RegExp(LBL.datePc.split(' ').slice(-1)[0])), {ms: 600, after: 1200}); },
    email_buyer: async () => {
      await click(PC ? T(LBL.nowPc) : vbtn(new RegExp(LBL.nowPc.split(' ')[0])), {ms: 500, after: 300});
      if (PC) await cam(emailIn(0).locator('xpath=../..'), 90).catch(() => {});
      await click(emailIn(0), {ms: 600, after: 150}); await type('you@example.com', 2);
    },
    email_rcpt: async () => { if (PC) await cam(emailIn(1).locator('xpath=../..'), 90).catch(() => {}); await click(emailIn(1), {ms: 600, after: 150}); await type('friend@example.com', 2); await wait(300); if (PC) await cam(null); },
    summary: async () => { if (PC) await cam(null); await wait(300); const bb = await box(T(LBL.total, false)).catch(() => null); if (bb && PC) await moveTo(bb.x + 260, bb.y - 90, 800); await wait(500); },
    promo: async () => { const pi = p.locator('input[type=text]:visible, input:not([type]):visible').last(); if (PC) await cam(pi.locator('xpath=../..'), 120).catch(() => {}); await click(pi, {ms: 700, after: 600}).catch(() => {}); },
    paymethod: async () => { if (PC) await cam(T(LBL.card, false).locator('xpath=../..'), 120).catch(() => {}); await click(PC ? T(LBL.card, false) : vbtn(new RegExp('^\\s*' + LBL.card)), {ms: 700, after: 700}); await click(PC ? T('Kaspi.kz', false) : vbtn(/Kaspi/), {ms: 500, after: 500}); },
    pay: async () => {
      const lab = p.locator('label:has(input[type=checkbox])').locator('visible=true').last(); await box(lab); const cb = p.locator('input[type=checkbox]').last();
      const lb = await lab.boundingBox(); const cbb = await cb.boundingBox().catch(() => null);
      const tx = cbb && cbb.width > 2 ? cbb.x + cbb.width / 2 : lb.x + 12, ty = cbb && cbb.width > 2 ? cbb.y + cbb.height / 2 : lb.y + 12;
      if (PC) { await cam(null); await moveTo(tx, ty, 700); await wait(100); } else await wait(250);
      fx.push([PC ? 'click' : 'tap', tx, ty]); await cb.check({force: true}).catch(() => {}); if (!(await cb.isChecked().catch(() => false))) await lab.click({position: {x: 10, y: 10}}).catch(() => {});
      await wait(400); const pb = vbtn(LBL.pay); const bb = await hover(pb, 700); ring(bb); await wait(800);
    },
  };

