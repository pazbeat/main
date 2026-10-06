s=open('record3.js').read()
old_lbl=s[s.index('const LBL = {'):s.index('}[LANG];')+8]
new_lbl='''const LBL = {
  ru: {nowMob: /^\\s*Сразу\\s*$/, dateMob: /^\\s*Выбрать дату\\s*$/, menu: /Подарить сертификат/, accept: /Принимаю/, next: /^\\s*Далее/, prog: 'Ты и Я', tabSum: 'На сумму', sumPc: /^\\s*50 000/, sumMob: '70 000', greet: /Добавить поздравление/, city: 'Алматы', salon: /Шанырак/, nowPc: 'Сразу после оплаты', datePc: 'В выбранную дату', total: 'Итого', card: 'Карта', pay: /Оплатить/, n1: 'Айгерим', n2: 'Данияр', msg: 'С днём рождения! Пусть этот день будет тёплым и спокойным.'},
  kk: {nowMob: /^\\s*Бірден\\s*$/, dateMob: /^\\s*Күнін таңдау\\s*$/, menu: /Сертификат сыйлау/i, accept: /Қабылдаймын/, next: /^\\s*Әрі қарай/, prog: 'Сен және Мен', tabSum: 'Сомаға', sumPc: /^\\s*50 000/, sumMob: '70 000', greet: /Құттықтау қосу/, city: 'Алматы', salon: /Шаңырақ/, nowPc: 'Төлемнен кейін бірден', datePc: 'Таңдалған күні', total: 'Барлығы', card: 'Карта', pay: /Төлеу/, n1: 'Айгерім', n2: 'Данияр', msg: 'Туған күніңмен! Бұл күн жылы әрі тыныш өтсін.'},
  en: {nowMob: /^\\s*Right away\\s*$/, dateMob: /^\\s*Pick a date\\s*$/, menu: /Gift a certificate/i, accept: /^\\s*Accept\\s*$/, next: /^\\s*Next/, prog: 'You & I', tabSum: 'Amount', sumPc: /^\\s*50,000/, sumMob: '70,000', greet: /Add a message/, city: 'Almaty', salon: /Shanyrak/, nowPc: 'Right after payment', datePc: 'On a chosen date', total: 'Total', card: 'Card', pay: /^\\s*Pay/, n1: 'Aigerim', n2: 'Daniyar', msg: 'Happy birthday! Wishing you a warm and peaceful day.'},
}[LANG];'''
s=s.replace(old_lbl,new_lbl)
def rep(a,b):
    global s
    assert a in s, a[:60]; s=s.replace(a,b)
rep("const OUT = LANG === 'ru' ? `rec2_${DEV}` : `rec3_${LANG}_${DEV}`;","const OUT = `rec4_${LANG}_${DEV}`; const DRY = !!process.env.DRY;")
rep("const LINES = JSON.parse(fs.readFileSync(LANG === 'ru' ? 'lines.json' : `lines_${LANG}.json`, 'utf8'))[DEV];","const LINES = JSON.parse(fs.readFileSync(`lines4_${LANG}.json`, 'utf8'))[DEV];")
rep("    await p.screenshot({path: fn, type: 'jpeg', quality: 90});","    if (!DRY) await p.screenshot({path: fn, type: 'jpeg', quality: 90});")
rep("meta.viewport = opts.viewport; meta.dpr = opts.deviceScaleFactor;","if (DRY) opts.deviceScaleFactor = 1; meta.viewport = opts.viewport; meta.dpr = opts.deviceScaleFactor;")
a0=s.index('  async function arc('); a1=s.index('  async function navigated()')
s=s[:a0]+'''  async function arc(target, arcY, maxSteps = 8) {   // mobile wheels: .mob-wheel__item labels on a rotating arc
    const re = target instanceof RegExp ? target : new RegExp('^\\\\s*' + target.replace(/[&]/g, '\\\\$&'));
    for (let i = 0; i < maxSteps; i++) {
      const loc = p.locator('.mob-wheel__item:visible').filter({hasText: re}).first(); const bb = await loc.boundingBox().catch(() => null);
      if (bb && bb.x > 8 && bb.x + bb.width < 382 && bb.y > 80 && bb.y < 800) { await click(loc, {ms: 500, after: 700}); return; }
      const dir = bb && bb.x < 8 ? -1 : 1; await swipe(195 + dir * 65, arcY, 195 - dir * 65, arcY, 520); await wait(500);
    }
    throw new Error('arc: ' + target);
  }
'''+s[a1:]
b0=s.index('  const A = {'); b1=s.index('  for (const L of LINES)')
s=s[:b0]+open('acts4.js').read()+s[b1:]
rep("    try { await A[L.act](); } catch (e) { console.log('ACT FAIL', L.id, L.act, e.message.split('\\n')[0]); }","""    for (const act of L.act.split(',')) { try { await A[act](); } catch (e) { console.log('ACT FAIL', L.id, act, e.message.split('\\n')[0]); } }
    if (DRY) await p.screenshot({path: `${OUT}/end_${L.id}.jpg`, type: 'jpeg', quality: 70});""")
open('record4.js','w').write(s)
