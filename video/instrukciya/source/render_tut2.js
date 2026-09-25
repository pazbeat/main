const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const { spawn } = require('child_process');
const FF = '/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2';
const DEV = process.argv[2], WK = +process.argv[3] || 4, LANG = process.argv[4] || 'ru'; const SUF = LANG === 'ru' ? DEV : `${LANG}_${DEV}`; const PC = DEV === 'pc';
(async () => {
  const b = await chromium.launch();
  const vp = PC ? {width: 1920, height: 1080} : {width: 1080, height: 1920};
  const probe = await b.newPage({viewport: vp}); await probe.goto(`http://127.0.0.1:8123/tut/tut2.html?dev=${DEV}&lang=${LANG}`); const TOTAL = await probe.evaluate(() => window.ready); await probe.close();
  const per = Math.ceil(TOTAL / WK);
  await Promise.all([...Array(WK).keys()].map(async w => {
    const f0 = w * per, f1 = Math.min(TOTAL, (w + 1) * per);
    const p = await b.newPage({viewport: vp}); p.on('pageerror', e => console.log('ERR', e.message));
    await p.goto(`http://127.0.0.1:8123/tut/tut2.html?dev=${DEV}&lang=${LANG}`); await p.evaluate(() => window.ready);
    const ff = spawn(FF, ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-r', '30', `seg2_${SUF}_${w}.mp4`], {stdio: ['pipe', 'inherit', 'inherit']});
    for (let f = f0; f < f1; f++) { await p.evaluate(fi => seek(fi), f); const buf = await p.screenshot({type: 'jpeg', quality: 93}); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); if ((f - f0) % 500 === 0) console.log(DEV, 'w' + w, f - f0, '/', f1 - f0); }
    ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log('done', DEV, w);
  }));
  await b.close();
})();
