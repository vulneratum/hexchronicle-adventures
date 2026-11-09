// HTML -> PDF with Playwright/Chromium. Usage: node render.js <input.html> <output.pdf>
const { chromium } = require('playwright');
const path = require('path');
const { pathToFileURL } = require('url');
(async () => {
  const [input, output] = process.argv.slice(2);
  if (!input || !output) { console.error('usage: node render.js <input.html> <output.pdf>'); process.exit(1); }
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto(pathToFileURL(path.resolve(input)).href, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: path.resolve(output), preferCSSPageSize: true, printBackground: true });
  await browser.close();
})();
