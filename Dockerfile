FROM python:3.7-alpine3.12

RUN apk add --no-cache \
    nodejs \
    npm \
    chromium

WORKDIR /web
COPY requirements.txt ./
RUN npm install puppeteer && \
    pip install --no-cache-dir -r requirements.txt

RUN adduser -h /web -D -u 99999 web
ADD --chown=web:web . ./
USER web

# replace chrome path with system version
RUN sed -i "s#args: \[#args: \['--disable-gpu', '--headless', #" js/screen.js && \
    sed -i "s#ignoreHTTPSErrors:#executablePath: '/usr/bin/chromium-browser', ignoreHTTPSErrors:#" js/screen.js

# can run "python3 -m http.server" to browse html report at "http://localhost:8000/page.0.html"
# docker run -p 127.0.0.1:8000:8000/tcp -it IMAGE
EXPOSE 8000

ENTRYPOINT [ "/bin/sh" ]
