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
        await page.goto('{{ url }}', {
            waitUntil: 'load',
            timeout: {{ timeout }}
        });
        success = true;
    } catch (e) {
    }
    if (!success) {
        try {
            await page.goto('{{ url }}', {
                waitUntil: 'domcontentloaded',
                timeout: {{ timeout }}
            });
            success = true;
        } catch (e) {
        }
    }
    if (success) {
        await page.screenshot({
            path: '{{ image }}',
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
