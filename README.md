# webshooter
Take screenshots of web sites and generate an HTML report.

## Installation
Requires python3.4+, nodejs, and npm

```
 npm install puppeteer

 pip3 install -r requirements.txt
```

## Usage
```
webshooter.py --session myscreens [URL [... URL]]
```
This will generate page-0.html which can be opened and used to navigate to all other existing pages. The session name can be used to resume a scan and re-generate a report.

You can also provide a file with 1 url per line (scheme required) and pass it in with -u. An nmap xml file can also be used with -x. Open ports that are considered HTTP (80,8080) or HTTPS (443,8443) will be scanned. You can override these ports with --http-ports and --https-ports.

## Report
Pagination can be set with the "-p" option. Navigate pages using the index or by using the left and right arrow keys.