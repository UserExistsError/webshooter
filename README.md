# webshooter
Take screenshots of web sites and generate an HTML report.

## Installation
Requires python3.4+, nodejs, and npm. Puppeteer is used for rendering pages and taking screenshots. Jinja2 is used for html and javascript templating.

```
 npm install puppeteer
 pip3 install -r requirements.txt
```

## Usage
```
webshooter.py --session myscreens scan [-u URL_FILE] [-x NMAP_XML] [URL [... URL]]
```
This will grab screenshots of all supplied urls. The session file can be used to resume a scan and generate a report. This command can be run multiple times with new urls to add. Once a url is added, it will be remembered in the session file. A screenshot will be attempted once for each url. Failed screenshots can be reattempted with --retry.

You can also provide a file with 1 url per line and pass it in with -u. Positional arguments are also treated as urls. In addition to urls, you can also specify HOST[:PORT] and CIDR ranges.

An nmap xml file can also be used with -x. Open ports that are considered HTTP (80,8080) or HTTPS (443,8443) will be scanned. You can override these ports with --ports-http and --ports-https. --all-open will treat all open ports as http/s and overrides --ports-http and --ports-https. Note that port specification options only apply to nmap xml. When providing urls as positional arguments or with -u, the port must be specified in the url (or omitted).

Recommended usage is to provide an nmap xml file generated like so:
```
nmap -p 80,443,8000,8080,8443,8888 -oX http.xml ...
```
Additional HTTP ports can be added.

## Report
```
webshooter.py --session myscreens report
```
The default report generates one screen per row. Use --tiles to get a more dense report. Pagination can be set with the -p option. Navigate pages using the navigation bar or by using the left and right arrow keys. Screenshots are sorted by page title (or Server header if no title). The file index.html is generated with the report that links to the first instance of each unique page title.

For easy viewing, try running with the following options:
```webshooter.py --session myscreens report --tiles -p 8```
This will put 8 items per page which should be viewable without scrolling. Then use the left and right arrow keys to navigate between pages.
