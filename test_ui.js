const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  await page.goto('http://127.0.0.1:5002');

  await page.screenshot({ path: 'dashboard_initial.png' });

  const filePath = path.resolve('./data/archive/20250613-614-Compensation Reports_unlocked.pdf');
  const inputUploadHandle = await page.$('input[type=file]');
  await inputUploadHandle.uploadFile(filePath);

  await page.click('button[type="submit"]');

  await page.waitForNavigation({ waitUntil: 'networkidle0' });

  await page.screenshot({ path: 'dashboard_after_upload.png' });

  await browser.close();
})();