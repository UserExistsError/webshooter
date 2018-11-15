const puppeteer = require('puppeteer');
const devices = require('puppeteer/DeviceDescriptors');

(async () => {
    const browser = await puppeteer.launch({
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
        ignoreHTTPSErrors: true,
        headless: true,
        defaultViewport: {width: 1000, height: 600}
    });
    const page = await browser.newPage();

    // dismiss dialogs. these can hang the screenshot
    page.on('dialog', async dialog => {
	await dialog.dismiss();
    });

    page.setExtraHTTPHeaders({{ headers }});
    if ({{ mobile }}) {
        page.emulate(devices['iPhone 6']);
    }
    var success = false;
    var waitEvents = ['load', 'domcontentloaded', 'networkidle2'];
    for (i = 0; i < waitEvents.length; i++) {
        try {
            await page.goto('{{ url }}', {
                waitUntil: waitEvents[i],
                timeout: {{ timeout }}
            });
            success = true;
            break;
        } catch (e) {
	    // likely a timeout
        }
    }

    function sleep(millisec) {
	return new Promise(resolve => setTimeout(resolve, millisec));
    }

    if (success) {
	// give page time to render
	await sleep({{ screen_wait }});
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
