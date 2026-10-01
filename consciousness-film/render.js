// Renders index.html frame by frame in headless Chromium and encodes an MP4.
//
//   node render.js [out.mp4]            full film
//   STILLS=1,120,400 node render.js     only save PNG stills of those frames
//
// Needs: playwright (Chromium) and ffmpeg on PATH.
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

const OUT = process.argv[2] || path.join(__dirname, 'day-0-until-now.mp4');
const STILLS = process.env.STILLS ? process.env.STILLS.split(',').map(Number) : null;

(async () => {
  const browser = await chromium.launch(
    fs.existsSync('/opt/pw-browsers/chromium') ? { executablePath: '/opt/pw-browsers/chromium' } : {});
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
  await page.goto('file://' + path.join(__dirname, 'index.html') + '?export');
  const { total, fps } = await page.evaluate(() => ({ total: window.TOTAL_FRAMES, fps: window.FPS }));
  const grab = i => page.evaluate(i => {
    window.renderFrame(i);
    return document.getElementById('out').toDataURL('image/jpeg', 0.95).split(',')[1];
  }, i);

  if (STILLS) {
    const last = Math.max(...STILLS);
    for (let i = 0; i <= last; i++) {
      const b64 = await grab(i);
      if (STILLS.includes(i)) fs.writeFileSync(path.join(__dirname, `still-${i}.jpg`), Buffer.from(b64, 'base64'));
    }
    await browser.close();
    return;
  }

  const secs = total / fps;
  // A slow ambient drone: an open fifth over A2 that breathes, plus a faint high shimmer.
  const drone =
    `aevalsrc='0.10*sin(2*PI*110*t)*(0.7+0.3*sin(2*PI*0.05*t))` +
    `+0.07*sin(2*PI*164.81*t)*(0.6+0.4*sin(2*PI*0.07*t+1))` +
    `+0.05*sin(2*PI*220.4*t)*(0.5+0.5*sin(2*PI*0.031*t+2))` +
    `+0.02*sin(2*PI*659.3*t)*(0.5+0.5*sin(2*PI*0.11*t))|` +
    `0.10*sin(2*PI*110.3*t)*(0.7+0.3*sin(2*PI*0.05*t+0.5))` +
    `+0.07*sin(2*PI*164.5*t)*(0.6+0.4*sin(2*PI*0.07*t+2))` +
    `+0.05*sin(2*PI*219.8*t)*(0.5+0.5*sin(2*PI*0.031*t))` +
    `+0.02*sin(2*PI*660.1*t)*(0.5+0.5*sin(2*PI*0.13*t))':s=48000:d=${secs}`;
  const ff = spawn('ffmpeg', [
    '-y', '-loglevel', 'error',
    '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
    '-f', 'lavfi', '-i', drone,
    '-filter_complex', `[1:a]lowpass=f=1800,afade=t=in:d=3,afade=t=out:st=${secs - 3}:d=3[a]`,
    '-map', '0:v', '-map', '[a]',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
    '-c:a', 'aac', '-b:a', '128k', '-shortest', OUT,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });

  for (let i = 0; i < total; i++) {
    const buf = Buffer.from(await grab(i), 'base64');
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if (i % 150 === 0) process.stdout.write(`frame ${i}/${total}\n`);
  }
  ff.stdin.end();
  await new Promise((res, rej) => ff.on('close', c => (c === 0 ? res() : rej(new Error('ffmpeg exit ' + c)))));
  await browser.close();
  console.log('wrote', OUT);
})().catch(e => { console.error(e); process.exit(1); });
