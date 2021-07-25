const puppeteer = require('puppeteer');
const devices = puppeteer.devices;
const fs = require('fs');
const poolSize = 1;

const express = require('express');
const app = express();
const crypto = require('crypto');
const port = {{ port }};
const csrfToken = Buffer.from('{{ token }}');


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
    image_path: <string>,
    timeout: <int>,
    mobile: <bool>,
    render_wait: <int>,
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
        'userAgent': await browser.userAgent(),
        'poolSize': poolSize
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
            defaultViewport: {width: 1600, height: 900, isMobile: false}
        });
    }
    return g_browser;
}

async function capture(opts) {
    let browser = await getBrowser();
    const page = await browser.newPage();

    // dismiss dialogs. these can hang the screenshot
    page.on('dialog', async dialog => {
        await dialog.dismiss();
    });

    page.setExtraHTTPHeaders(opts.headers);
    if (opts.mobile) {
        page.emulate(devices['iPhone 6']);
    }
    var success = false;
    var waitEvents = ['load', 'domcontentloaded', 'networkidle2'];
    var response = null;
    for (i = 0; i < waitEvents.length; i++) {
        try {
            response = await page.goto(opts.url, {
                waitUntil: waitEvents[i],
                timeout: opts.timeout
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

    var page_info = {};
    if (success) {
	// give page time to render
        page_info = {
            url_final: page.url(),
            title: await page.title().catch(function(r) { return '' }),
            headers: response.headers(),
            status: response.status(),
            security: response.securityDetails(),
            image_path: opts.image_path
        };
        await sleep(opts.screen_wait);
        await page.screenshot({
            //encoding: 'base64',
            path: opts.image_path,
            //fullPage: true
            clip: {
                x: 0,
                y: 0,
                width: 1600,
                height: 900
            }
        });
    } else {
        console.log('Failed to get screenshot');
    }
    //await browser.close();
    return page_info;
}
