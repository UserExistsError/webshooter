FROM alpine:3.10

RUN apk add --no-cache \
    python3 \
    nodejs \
    npm \
    chromium

COPY requirements.txt /tmp/
RUN npm install puppeteer && \
    pip3 install -r /tmp/requirements.txt

RUN adduser -h /web -D -u 99999 web
WORKDIR /web
ADD --chown=web:web . /web/

# replace chrome path with system version
RUN sed -i "s#args: \[#args: \['--disable-gpu', '--headless', #" js/screen.js && \
    sed -i "s#ignoreHTTPSErrors:#executablePath: '/usr/bin/chromium-browser', ignoreHTTPSErrors:#" js/screen.js

# can run "python3 -m http.server" to browse html report at "http://localhost:8000/page.0.html"
# docker run -p 127.0.0.1:8000:8000/tcp -it IMAGE
EXPOSE 8000

USER web
ENTRYPOINT [ "/bin/sh" ]
