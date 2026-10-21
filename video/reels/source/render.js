const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const { spawn } = require('child_process');
const FF = '/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2';
const WK = 3;
(async () => {
  const b = await chromium.launch();
  const pr = await b.newPage({viewport: {width: 1080, height: 1920}}); await pr.goto('http://127.0.0.1:8123/reel/reel.html'); const TOTAL = await pr.evaluate(() => window.ready); await pr.close();
  const per = Math.ceil(TOTAL / WK);
  await Promise.all([...Array(WK).keys()].map(async w => {
    const f0 = w * per, f1 = Math.min(TOTAL, (w + 1) * per);
    const p = await b.newPage({viewport: {width: 1080, height: 1920}}); p.on('pageerror', e => console.log('ERR', e.message));
    await p.goto('http://127.0.0.1:8123/reel/reel.html'); await p.evaluate(() => window.ready);
    const ff = spawn(FF, ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', '30', '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', '30', `seg_${w}.mp4`], {stdio: ['pipe', 'inherit', 'inherit']});
    for (let f = f0; f < f1; f++) { await p.evaluate(fi => seek(fi), f); const buf = await p.screenshot({type: 'jpeg', quality: 95}); if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r)); }
    ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log('done', w);
  }));
  await b.close();
})();
