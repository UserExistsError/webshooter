const puppeteer = require('puppeteer');
const devices = puppeteer.devices;

const express = require('express');
const app = express();
const crypto = require('crypto');

const homedir = require('os').homedir();
const pathjoin = require('path').join;
const defaultProjectRoot = pathjoin(homedir, '.webshooter', 'puppeteer');
const fs = require('fs');

const viewPortDims = {width: 1600, height: 900};

if (typeof process.env.WEBSHOOTER_PORT === 'undefined') {
    throw new Error('environment variable WEBSHOOTER_PORT is required');
}
const port = Number(process.env.WEBSHOOTER_PORT);

if (typeof process.env.WEBSHOOTER_TOKEN === 'undefined') {
    throw new Error('environment variable WEBSHOOTER_TOKEN is required');
}
const csrfToken = Buffer.from(process.env.WEBSHOOTER_TOKEN);

// see https://chromium.googlesource.com/chromium/src/+/refs/heads/main/net/base/port_util.cc#27
const restrictedPorts = [
    1,    7,    9,   11,   13,   15,   17,    19,   20,
   21,   22,   23,   25,   37,   42,   43,    53,   69,
   77,   79,   87,   95,  101,  102,  103,   104,  109,
  110,  111,  113,  115,  117,  119,  123,   135,  137,
  139,  143,  161,  179,  389,  427,  465,   512,  513,
  514,  515,  526,  530,  531,  532,  540,   548,  554,
  556,  563,  587,  601,  636,  989,  990,   993,  995,
 1719, 1720, 1723, 2049, 3659, 4045, 5060,  5061, 6000,
 6566, 6665, 6666, 6667, 6668, 6669, 6697, 10080
];

// Add CSRF middleware
app.use((req, res, next) => {
    const tok = req.headers.token;
    if (typeof tok !== 'undefined') {
        if (tok.length === csrfToken.length) {
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
    const context = await getBrowserContext();
    //const context = await getBrowser().then(b => b.defaultBrowserContext());
    const page = await context.newPage();
    const startTime = Date.now();
    try {
        const page_info = await capture(page, req.body);
        res.json(page_info);
    } catch (err) {
        res.status(500).json({
            error: {
                name: err.name,
                message: err.message,
                elapsed: Date.now() - startTime
            }
        });
    }
    // wait for page to close to ensure we limit open windows. this should only matter for
    // the default browser context since in that case, we can't close the context like we
    // do for incognito mode.
    await page.close();
    if (context.isIncognito()) {
        context.close().catch(() => {/* browser was probably closed */});
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

// Track browser download progress. For bundled JavaScript, the browser is not
// included and must be downloaded during the first run.
const browserDownloadStatus = {
    progress: 0, // takes a value in [0,1] computed as bytes_downloaded / total_bytes
};

app.post('/status', async (req, res) => {
    getUserAgent().then(userAgent => {
        res.json({
            userAgent: userAgent,
            userAgentMobile: devices['iPhone X']['userAgent'],
            viewPort: viewPortDims,
            viewPortMobile: devices['iPhone X']['viewport']
        });
    }).catch(err => {
        res.status(500).json({
            error: {
                name: err.name,
                message: err.message
            },
            browserDownloadProgress: browserDownloadStatus.progress
        });
    })
});

const server = app.listen(port, '127.0.0.1', () => {
    console.log('Started capture service on', port);
});

async function getBrowserContext() {
    // Must call close() on returned context when finished
    const config = {};
    if (typeof process.env.WEBSHOOTER_PROXY !== 'undefined') {
        config.proxyServer = process.env.WEBSHOOTER_PROXY;
    }
    const browser = await getBrowser();
    const context = await browser.createIncognitoBrowserContext(config);
    return context;
}

// Checks if a browser is installed. If not, downloads one. Updates download
// progress and returns on download completion.
async function ensureBrowserInstall() {
    if (typeof puppeteer._projectRoot === 'undefined') {
        console.log('No projectRoot defined. Using', defaultProjectRoot);
        if (!fs.existsSync(defaultProjectRoot)) {
            console.log('Creating projectRoot at', defaultProjectRoot);
            fs.mkdirSync(defaultProjectRoot, { recursive: true });
        }
        puppeteer._projectRoot = defaultProjectRoot;
    }
    const fetcher = puppeteer.createBrowserFetcher();
    const revisions = await fetcher.localRevisions();
    revisions.forEach(rev => console.log('Local revision:', rev));
    if (revisions.length === 0) {
        console.log('No local Chromium available. Downloading one.');
        // see https://github.com/puppeteer/puppeteer/blob/main/src/revisions.ts
        const revision = await fetcher.download(puppeteer._preferredRevision, (have, need) => {
            browserDownloadStatus.progress = have / need;
        });
        console.log('Downloaded new browser revision:', revision);
    }
    browserDownloadStatus.progress = 1;
}

const getBrowser = function() {
    ensureBrowserInstall();
    let browser = undefined;
    const launchArgs = {
        args: [],
        headless: true,
        userDataDir: undefined,
        ignoreHTTPSErrors: true,
        defaultViewport: {
            width: viewPortDims.width,
            height: viewPortDims.height
        }
    };
    if (process.env.WEBSHOOTER_DOCKER === 'yes') {
        // This was necessary even after following the docs
        // https://github.com/puppeteer/puppeteer/blob/main/docs/troubleshooting.md#running-puppeteer-in-docker
        launchArgs.args.push('--no-sandbox');
    }
    if (typeof process.env.WEBSHOOTER_PROXY !== 'undefined') {
        // this probably isn't necessary since we specify the proxy for each new window that is opened
        launchArgs.args.push(`--proxy-server=${process.env.WEBSHOOTER_PROXY}`);
    }
    if (typeof process.env.WEBSHOOTER_TEMP !== 'undefined') {
        // this prevents loading the user's chromium settings including plugins
        //cliArgs.push(`--user-data-dir=${process.env.WEBSHOOTER_TEMP}`);
        launchArgs.userDataDir = process.env.WEBSHOOTER_TEMP;
    }
    if (typeof process.env.DISPLAY !== 'undefined') {
        launchArgs.headless = false;
    }
    // allow unsafe ports. this may not work with --headless option
    launchArgs.args.push('--explicitly-allowed-ports='+restrictedPorts.join(','));
    return (async function() {
        if (typeof browser === 'undefined') {
            browser = await puppeteer.launch(launchArgs);
        }
        return browser;
    });
}();

const getUserAgent = function() {
    let userAgent = undefined;
    return (async function() {
        if (typeof userAgent === 'undefined') {
            const userAgentHeadless = await getBrowser().then(browser => browser.userAgent());
            userAgent = userAgentHeadless.replace('Headless', '');
        }
        return userAgent;
    });
}();

function sleep(millisec) {
    return new Promise(resolve => setTimeout(resolve, millisec));
}

async function capture(page, opts) {
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

    const response = await page.goto(opts.url, {
        // See https://puppeteer.github.io/puppeteer/docs/puppeteer.page.goto#remarks
        waitUntil: ['load'],
        timeout: opts.timeout_ms
    }).
        catch(err => {
            if (err.name === 'TimeoutError') {
                console.log('Timeout waiting for `load` event. Trying again with `domcontentloaded`.');
                return page.goto(opts.url, {
                    waitUntil: ['domcontentloaded'],
                    timeout: opts.timeout_ms
                });
            }
            throw err;
        });

    const page_info = {
        url_final: page.url(),
        title: await page.title().catch((r) => { return '' }),
        headers: response.headers(),
        status: response.status(),
        security: response.securityDetails(),
        image: ''
    };
    // give page time to render
    await sleep(opts.render_wait_ms);
    page_info.image = await page.screenshot({
        encoding: 'base64',
    });
    return page_info;
}
