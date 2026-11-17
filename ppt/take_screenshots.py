import asyncio, os
from playwright.async_api import async_playwright

BASE = r"E:\999-Dev\04-SOG\dev\ppt\screenshots"
os.makedirs(BASE, exist_ok=True)
BASE_URL = "http://localhost:5174"

async def main():
    async with async_playwright() as p:
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]
        chrome_exe = next((c for c in chrome_paths if os.path.exists(c)), None)
        if not chrome_exe:
            print("No Chrome found, using bundled chromium")
            browser = await p.chromium.launch(headless=True)
        else:
            print(f"Using Chrome: {chrome_exe}")
            browser = await p.chromium.launch(
                executable_path=chrome_exe,
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )

        ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
        page = await ctx.new_page()

        await page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=20000)
        await page.wait_for_timeout(1000)

        try:
            inputs = await page.query_selector_all("input")
            if len(inputs) >= 2:
                await inputs[0].fill("admin")
                await page.wait_for_timeout(100)
                await inputs[1].fill("admin123")
                await page.wait_for_timeout(200)
                submit = await page.query_selector('button[type="submit"], button:has-text("登录"), button:has-text("Login"), .el-button--primary')
                if submit:
                    await submit.click()
                    await page.wait_for_timeout(2000)
                    print("Logged in")
        except Exception as e:
            print(f"Login failed: {e}")

        pages = [
            ("01_login.png", "/login"),
            ("02_dashboard.png", "/dashboard"),

            ("03_system_users.png", "/system/users"),
            ("04_system_roles.png", "/system/roles"),
            ("05_system_logs.png", "/system/logs"),

            ("06_materials.png", "/materials"),
            ("07_boms.png", "/boms"),
            ("08_inspect_types.png", "/inspect-types"),
            ("09_defect_codes.png", "/defect-codes"),

            ("10_inventory_hub.png", "/inventory/hub"),
            ("11_consumables_hub.png", "/consumables/hub"),
            ("12_wip_hub.png", "/wip/hub"),
            ("13_stock_txn.png", "/stock/txn"),

            ("14_orders_work.png", "/orders/work"),
            ("15_orders_release.png", "/orders/release"),
            ("16_orders_adjust.png", "/orders/adjust"),
            ("17_orders_monitor.png", "/orders/monitor"),

            ("18_quality.png", "/quality"),
            ("19_sops.png", "/sops"),
            ("20_trace.png", "/trace"),

            ("21_devices.png", "/devices"),
        ]

        for fname, path in pages:
            print(f"Capture {path} -> {fname}")
            try:
                await page.goto(f"{BASE_URL}{path}", wait_until="networkidle", timeout=20000)
                await page.wait_for_timeout(1500)
                fpath = os.path.join(BASE, fname)
                await page.screenshot(path=fpath, full_page=True)
                sz = os.path.getsize(fpath)
                print(f"  OK ({sz//1024}KB)")
            except Exception as e:
                print(f"  FAIL: {e}")

        # BOM + kit check dialog
        print("Capture BOM with kit check dialog...")
        try:
            await page.goto(f"{BASE_URL}/boms", wait_until="networkidle", timeout=20000)
            await page.wait_for_timeout(2000)
            shortage_btn = await page.query_selector('button:has-text("齐套检查"), button:has-text("缺料检查")')
            if shortage_btn:
                await shortage_btn.click()
                await page.wait_for_timeout(1500)
            fpath = os.path.join(BASE, "22_bom_kit_check.png")
            await page.screenshot(path=fpath, full_page=True)
            print(f"  OK ({os.path.getsize(fpath)//1024}KB)")
        except Exception as e:
            print(f"  FAIL: {e}")

        await browser.close()
        print("\nAll done!")

asyncio.run(main())