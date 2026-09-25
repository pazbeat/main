const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const LANG = process.argv[2];
const X = {en: {accept: /^\s*Accept\s*$/, next: /^\s*Next/, occ: 'Birthday', tab: 'Amount', greet: /Add a message/, n1: 'Aigerim', n2: 'Daniyar', msg: 'Happy birthday! Wishing you a warm and peaceful day.'},
           kk: {accept: /Қабылдаймын/, next: /^\s*Әрі қарай/, occ: 'Туған күн', tab: 'Сомаға', greet: /Құттықтау қосу/, n1: 'Айгерім', n2: 'Данияр', msg: 'Туған күніңмен! Бұл күн жылы әрі тыныш өтсін.'}}[LANG];
(async () => {
  const b = await chromium.launch(); const p = await b.newPage({viewport:{width:1440,height:900},deviceScaleFactor:3}); p.setDefaultTimeout(8000);
  const vb = re => p.locator('button:visible').filter({hasText: re}).first();
  await p.goto('https://www.imbir.kz/ru', {waitUntil:'networkidle'}); await p.getByRole('button',{name:/^Принять/}).first().click().catch(()=>{});
  await p.goto(`https://www.imbir.kz/${LANG}/create`,{waitUntil:'networkidle'}); await p.waitForTimeout(1200);
  await p.locator('input[type=checkbox]').first().check({force:true}); await vb(X.accept).click(); await p.waitForTimeout(1200);
  const next = async()=>{await vb(X.next).click();await p.waitForTimeout(1400);};
  await p.getByText(X.occ,{exact:true}).first().click(); await p.waitForTimeout(900);
  if (LANG !== 'kk') { await p.getByText('›',{exact:true}).first().click(); await p.waitForTimeout(700); await p.getByText('›',{exact:true}).first().click(); await p.waitForTimeout(900); }
  await next(); await p.getByText(X.tab,{exact:true}).first().click(); await p.waitForTimeout(800); await p.getByText('50 000 ₸',{exact:false}).first().click(); await p.waitForTimeout(800); await next();
  const ins = p.locator('input:visible:not([type=checkbox])'); await ins.nth(0).fill(X.n1); await ins.nth(1).fill(X.n2);
  await vb(X.greet).click(); await p.waitForTimeout(500); await p.locator('textarea:visible').first().fill(X.msg); await p.waitForTimeout(800);
  await p.addStyleTag({content:`.stg__card{transform:none!important;box-shadow:none!important}.stg__circle,.stg__sun{visibility:hidden!important}html,body,.stg__orb,.stg__visual,.stg__main{background:transparent!important}`});
  await p.waitForTimeout(600); await p.locator('.stg__card').first().screenshot({path:`order_cert_${LANG}.png`,omitBackground:true});
  const q = await b.newPage({viewport:{width:1440,height:760},deviceScaleFactor:2});
  await q.goto('https://www.imbir.kz/ru', {waitUntil:'networkidle'}); await q.getByRole('button',{name:/^Принять/}).first().click().catch(()=>{});
  await q.goto(`https://www.imbir.kz/${LANG}/check`,{waitUntil:'networkidle'}); await q.waitForTimeout(1500);
  await q.screenshot({path:`check_page_${LANG}.jpg`,type:'jpeg',quality:90});
  await b.close();
})();
