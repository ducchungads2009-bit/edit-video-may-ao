// Điều khiển trình duyệt cho bộ dựng HyperFrames (ngoài phần dựng video do HyperFrames lo):
//   node drive.mjs audio <url> <ra.json>                — chạy cả dòng thời gian, ghi tiếng từng khung
//   node drive.mjs still <url> <khung,khung,...> <ra_%d.png> — chụp từng khung
// Trình duyệt: biến HYPERFRAMES_BROWSER_PATH (Chrome Headless Shell) hoặc NHM_BROWSER.
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';

const [mode, url, a3, a4] = process.argv.slice(2);
const exe = process.env.HYPERFRAMES_BROWSER_PATH || process.env.NHM_BROWSER;
if (!exe) { console.error('Thiếu trình duyệt (HYPERFRAMES_BROWSER_PATH)'); process.exit(2); }
const browser = await puppeteer.launch({
  executablePath: exe,
  headless: true,
  protocolTimeout: 600000,
  args: ['--no-sandbox', '--disable-dev-shm-usage', '--hide-scrollbars', '--mute-audio', '--use-gl=angle', '--use-angle=swiftshader',
    '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--font-render-hinting=none', '--force-color-profile=srgb',
    '--disable-background-networking', '--disable-component-update', '--disable-domain-reliability', '--no-pings', '--disable-sync',
    '--metrics-recording-only', '--no-first-run', '--disable-breakpad'],
});
let code = 0;
try {
  const page = await browser.newPage();
  page.on('console', (m) => { const t = m.text(); if (/\[hf\]|Error|error/.test(t)) console.error('[trang]', t.slice(0, 400)); });
  page.on('pageerror', (e) => console.error('[trang lỗi]', String(e).slice(0, 400)));
  const W = Number(process.env.HF_W || 1080), H = Number(process.env.HF_H || 1920);
  await page.setViewport({width: W, height: H, deviceScaleFactor: 1});
  await page.goto(url, {waitUntil: 'load', timeout: 120000});
  if (mode === 'audio') {
    await page.waitForFunction(() => document.title === 'AUDIO_DONE' || document.title === 'HF_ERROR', {timeout: 600000, polling: 200});
    const err = await page.evaluate(() => window.__hfError);
    if (err) throw new Error(err);
    const data = await page.evaluate(() => JSON.stringify(window.__AUDIO));
    fs.writeFileSync(a3, data);
  } else if (mode === 'still') {
    const frames = a3.split(',').map(Number);
    await page.waitForFunction(() => window.__hf && window.__hf.buildReady && window.__hf.buildReady.remotion, {timeout: 60000});
    await page.evaluate(() => window.__hf.buildReady.remotion);
    for (let i = 0; i < frames.length; i++) {
      await page.evaluate((f) => window.__hfSeek(f), frames[i]);
      await page.screenshot({path: a4.replace('%d', String(i)), clip: {x: 0, y: 0, width: W, height: H}, omitBackground: true});
      console.log(`still ${i + 1}/${frames.length}`);
    }
  } else throw new Error('chế độ lạ: ' + mode);
} catch (e) {
  console.error('[!] ' + (e && e.stack || e));
  code = 1;
} finally {
  await browser.close().catch(() => {});
}
process.exit(code);
