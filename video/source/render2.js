const { chromium } = require('/opt/node22/lib/node_modules/playwright');
const { spawn } = require('child_process');
const FF='/usr/local/lib/python3.11/dist-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2';
const FPS=30, DUR=62.5, TOTAL=FPS*DUR;
const W = +process.argv[2]||4;
(async () => {
  const b = await chromium.launch({args:['--allow-file-access-from-files']});
  const per = Math.ceil(TOTAL/W);
  await Promise.all([...Array(W).keys()].map(async w => {
    const f0=w*per, f1=Math.min(TOTAL,(w+1)*per);
    const p = await b.newPage({viewport:{width:1920,height:1080}});
    p.on('pageerror', e=>console.log('ERR',e.message));
    await p.goto('file://'+__dirname+'/film.html');
    const ok = await p.evaluate(()=>window.ready); if(!ok) console.log('fonts not ok', w);
    const ff = spawn(FF,['-loglevel','error','-y','-f','image2pipe','-framerate',String(FPS),'-c:v','mjpeg','-i','-','-c:v','libx264','-preset','medium','-crf','17','-pix_fmt','yuv420p','-r',String(FPS),`v2/seg_${w}.mp4`],{stdio:['pipe','inherit','inherit']});
    for (let f=f0; f<f1; f++) {
      await p.evaluate(t=>seek(t), f/FPS);
      const buf = await p.screenshot({type:'jpeg',quality:95});
      if(!ff.stdin.write(buf)) await new Promise(r=>ff.stdin.once('drain',r));
      if((f-f0)%150===0) console.log(`w${w} ${f-f0}/${f1-f0}`);
    }
    ff.stdin.end(); await new Promise(r=>ff.on('close',r));
    console.log('done',w);
  }));
  await b.close();
})();
