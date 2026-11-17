import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const OUT = path.resolve('E:/999-Dev/04-SOG/dev/ppt/screenshots');
if (!fs.existsSync(OUT)) fs.mkdirSync(OUT, { recursive: true });

const BASE = 'http://localhost:5173';

const PAGES = [
  { url: '/login', file: '01_login.png', wait: 1500 },
  { url: '/dashboard', file: '02_dashboard.png', wait: 2500 },
  { url: '/materials', file: '03_materials.png', wait: 2000 },
  { url: '/boms', file: '04_boms.png', wait: 2000 },
  { url: '/inspect-types', file: '05_inspect_types.png', wait: 2000 },
  { url: '/defect-codes', file: '06_defect_codes.png', wait: 1500 },
  { url: '/orders/work', file: '07_orders_work.png', wait: 2000 },
  { url: '/orders/monitor', file: '08_orders_monitor.png', wait: 2000 },
  { url: '/quality', file: '09_quality.png', wait: 2000 },
  { url: '/sops', file: '10_sops.png', wait: 2000 },
  { url: '/trace', file: '11_trace.png', wait: 2000 },
  { url: '/devices', file: '12_devices.png', wait: 2000 },
  { url: '/inventory/hub?tab=query', file: '13_inventory.png', wait: 2000 },
  { url: '/wip/hub', file: '14_wip.png', wait: 2000 },
  { url: '/system/users', file: '15_users.png', wait: 1500 },
  { url: '/system/roles', file: '16_roles.png', wait: 2000 },
  { url: '/system/logs', file: '17_logs.png', wait: 2000 },
];

async function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
  const browser = await chromium.launch({
    headless: true,
    channel: 'chrome',
    args: ['--force-device-scale-factor=1', '--window-size=1440,900']
  });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  // Login first
  console.log('[1/2] Logging in as admin...');
  await page.goto(BASE + '/login', { waitUntil: 'networkidle' });
  await sleep(500);
  await page.fill('input[type="text"], input[placeholder*="用户名"], input:first-of-type', 'admin');
  await page.fill('input[type="password"]', 'admin123');
  await sleep(200);
  await page.click('button[type="submit"], button:has-text("登录"), button:has-text("登 录")');
  await sleep(2500);
  const token = await page.evaluate(() => localStorage.getItem('sog_token'));
  console.log('    Token:', token ? 'OK' : 'MISSING');

  // Screenshot all pages
  console.log('[2/2] Taking screenshots...');
  for (let i = 0; i < PAGES.length; i++) {
    const p = PAGES[i];
    try {
      console.log(`  [${i+1}/${PAGES.length}] ${p.url}`);
      await page.goto(BASE + p.url, { waitUntil: 'networkidle', timeout: 15000 });
      await sleep(p.wait);
      const fullPath = path.join(OUT, p.file);
      await page.screenshot({ path: fullPath, fullPage: false });
      console.log(`    -> ${p.file}`);
    } catch (e) {
      console.log(`    FAIL: ${e.message}`);
    }
  }

  await browser.close();
  console.log('\nDone! All screenshots saved to', OUT);
}

main().catch(e => { console.error(e); process.exit(1); });