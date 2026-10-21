const { chromium } = require('/opt/node22/lib/node_modules/playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});p.on('pageerror',e=>console.log('ERR',e.message));
await p.goto('http://127.0.0.1:8123/reel/reel.html');await p.evaluate(()=>window.ready);
for(const t of process.argv.slice(2).map(Number)){await p.evaluate(f=>seek(f),Math.round(t*30));await p.screenshot({path:`st_${t}.jpg`,type:'jpeg',quality:80});}
await b.close();})();
