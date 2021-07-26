const puppeteer = require('puppeteer');
const devices = puppeteer.devices;
const fs = require('fs');

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
    try {
        let page_info = await capture(req.body);
        res.json(page_info);
    } catch (err) {
        console.log(err);
        res.status(500).send(err);
    }
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
    let browser = await getBrowser();
    res.json({
        userAgent: await browser.userAgent(),
        userAgentMobile: devices['iPhone X']['userAgent'],
        viewPort: viewPortDims,
        viewPortMobile: devices['iPhone X']['viewport']
    });
});

const server = app.listen(port, '127.0.0.1', () => {
    console.log('Started capture service on', port);
});

var g_browser = undefined;
async function getBrowser() {
    if (g_browser == undefined) {
        g_browser = await puppeteer.launch({
            args: ['--no-sandbox'],
            ignoreHTTPSErrors: true,
            headless: true,
            defaultViewport: {
                width: viewPortDims.width,
                height: viewPortDims.height
            }
        });
    }
    return g_browser;
}


function sleep(millisec) {
    return new Promise(resolve => setTimeout(resolve, millisec));
}

async function capture(opts) {
    const browser = await getBrowser();

    //const page = await browser.newPage();
    const context = await browser.createIncognitoBrowserContext();
    const page = await context.newPage();

    // dismiss dialogs. these can hang the screenshot
    page.on('dialog', async dialog => {
        await dialog.dismiss();
    });

    page.setExtraHTTPHeaders(opts.headers);
    if (opts.mobile) {
        // see https://github.com/puppeteer/puppeteer/blob/main/src/common/DeviceDescriptors.ts
        page.emulate(devices['iPhone X']);
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

    var page_info = {};
    if (success) {
        // give page time to render
        page_info = {
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
    } else {
        console.log('Failed to get screenshot');
    }
    await page.close();
    return page_info;
}
