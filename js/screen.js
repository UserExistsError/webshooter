const puppeteer = require('puppeteer');
const devices = puppeteer.devices;

const express = require('express');
const app = express();
const crypto = require('crypto');
const port = {{ port }};
const csrfToken = Buffer.from('{{ token }}');

const viewPortDims = {width: 1600, height: 900};

// Add CSRF middleware
app.use((req, res, next) => {
    //console.log('Request to', req.url, 'from', req.ip);
    const tok = req.headers.token;
    if (tok != undefined) {
        if (tok.length == csrfToken.length) {
            if (crypto.timingSafeEqual(Buffer.from(tok), csrfToken)) {
                next();
                return;
            }
        }
    }
    console.log('Bad token:', req.header.token);
    res.status(400).send('bad request');
});

app.use(express.json());

/*
Capture Request
{
    url: <string>,
    timeout_ms: <int>,
    mobile: <bool>,
    render_wait_ms: <int>,
    headers: <array>
}
*/
app.post('/capture', async (req, res) => {
    //console.log(req.body);
    const browser = await getBrowser();
    const context = await browser.createIncognitoBrowserContext();
    try {
        let page_info = await capture(context, req.body);
        res.json(page_info);
    } catch (err) {
        res.status(500).json({error: err});
    }
    await context.close();
});

app.post('/shutdown', async (req, res) => {
    res.send('Ok')
    server.close(() => {
        console.log('Capture service going down');
    });
    getBrowser().then((b) => {
        b.close();
        console.log('Closed browser instance');
    });
});

app.post('/status', async (req, res) => {
    getUserAgent().then(userAgent => {
        res.json({
            userAgent: userAgent,
            userAgentMobile: devices['iPhone X']['userAgent'],
            viewPort: viewPortDims,
            viewPortMobile: devices['iPhone X']['viewport']
        });
    }).catch(err => {
        res.status(500).json({error: err})
    })
});

const server = app.listen(port, '127.0.0.1', () => {
    console.log('Started capture service on', port);
});

var getBrowser = function() {
    let browser = undefined;
    let cliArgs = [];
    if (process.env.WEBSHOOTER_DOCKER === 'yes') {
        // This was necessary even after following the docs
        // https://github.com/puppeteer/puppeteer/blob/main/docs/troubleshooting.md#running-puppeteer-in-docker
        cliArgs.push('--no-sandbox');
    }
    return (async function() {
        if (browser == undefined) {
            browser = await puppeteer.launch({
                args: cliArgs,
                ignoreHTTPSErrors: true,
                defaultViewport: {
                    width: viewPortDims.width,
                    height: viewPortDims.height
                }
            });
        }
        return browser;
    });
}();

var getUserAgent = function() {
    let userAgent = undefined;
    return (async function() {
        if (userAgent == undefined) {
            const userAgentHeadless = await getBrowser().then(browser => browser.userAgent());
            userAgent = userAgentHeadless.replace('Headless', '');
        }
        return userAgent;
    });
}();

function sleep(millisec) {
    return new Promise(resolve => setTimeout(resolve, millisec));
}

async function capture(context, opts) {
    const page = await context.newPage();

    // dismiss dialogs. these can hang the screenshot
    page.on('dialog', async dialog => {
        await dialog.dismiss();
    });

    page.setExtraHTTPHeaders(opts.headers);
    if (opts.mobile) {
        // see https://github.com/puppeteer/puppeteer/blob/main/src/common/DeviceDescriptors.ts
        page.emulate(devices['iPhone X']);
    } else {
        const userAgent = await getUserAgent();
        await page.setUserAgent(userAgent);
    }
    var success = false;
    const waitEvents = ['load', 'domcontentloaded', 'networkidle2'];
    var response = null;
    for (i = 0; i < waitEvents.length; i++) {
        try {
            response = await page.goto(opts.url, {
                waitUntil: waitEvents[i],
                timeout: opts.timeout_ms
            });
            success = true;
            break;
        } catch (e) {
            // likely a timeout
        }
    }

    if (!success) {
        throw 'failed to navigate to URL';
    }

    // give page time to render
    let page_info = {
        url_final: page.url(),
        title: await page.title().catch(function(r) { return '' }),
        headers: response.headers(),
        status: response.status(),
        security: response.securityDetails(),
        image: ''
    };
    await sleep(opts.render_wait_ms);
    page_info.image = await page.screenshot({
        encoding: 'base64',
        //path: opts.image_path,
        //fullPage: true
        clip: {
            x: 0,
            y: 0,
            width: page.viewport().width,
            height: page.viewport().height
        }
    });
    return page_info;
}
