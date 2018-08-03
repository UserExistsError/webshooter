const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        ignoreHTTPSErrors: true,
        headless: true,
        defaultViewport: {width: 1400, height: 900}
    });
    const page = await browser.newPage();
    var success = false;
    try {
        await page.goto('::URL::', {
            waitUntil: 'load',
            timeout: ::TIMEOUT::
        });
        success = true;
    } catch {
    }
    if (!success) {
        try {
            await page.goto('::URL::', {
                waitUntil: 'domcontentloaded',
                timeout: ::TIMEOUT::
            });
            success = true;
        } catch {
        }
    }
    if (success) {
        await page.screenshot({
            path: '::IMAGE::',
            //fullPage: true
            clip: {
                x: 0,
                y: 0,
                width: 1000,
                height: 600
            }
        });
    }
    await browser.close();
})();
