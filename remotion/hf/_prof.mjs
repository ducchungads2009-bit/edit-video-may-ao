import puppeteer from 'puppeteer-core';
const [url] = process.argv.slice(2);
const b = await puppeteer.launch({executablePath: process.env.HYPERFRAMES_BROWSER_PATH, headless: true, args: ['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const p = await b.newPage(); await p.setViewport({width:1080,height:1920});
p.on('console', m => console.log('[c]', m.text().slice(0,200)));
await p.goto(url, {waitUntil:'load'});
await p.evaluate(() => window.__hf.buildReady.remotion);
for (let f = 0; f < 20; f++) {
  const t0 = Date.now();
  const pr = p.evaluate((f) => window.__hfSeek(f), f);
  let to = setTimeout(async () => console.log('pending@', f, await p.evaluate(() => window.__hfPending())), 400);
  await pr; clearTimeout(to);
  const t1 = Date.now();
  await p.screenshot({path: '/tmp/x.png'});
  console.log(f, 'seek', t1 - t0, 'shot', Date.now() - t1);
}
await b.close();
