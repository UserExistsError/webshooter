# https://github.com/puppeteer/puppeteer/blob/main/docs/troubleshooting.md#running-on-alpine

FROM python:3.9-alpine3.14

RUN apk add --no-cache \
    nodejs \
    npm \
    chromium

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true \
    PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser \
    ENV=.profile \
    WEBSHOOTER_DOCKER=yes

ARG USER=websh

# add new user
WORKDIR /web
RUN addgroup -S -g 99999 $USER && \
    adduser -S -G $USER -h /web -D -u 99999 $USER
USER $USER

# install python and node dependencies
ADD --chown=$USER:$USER requirements.txt package.json ./
RUN python -m venv .webshooter && \
    source .webshooter/bin/activate && \
    pip install --no-cache-dir -r requirements.txt && \
    echo "source .webshooter/bin/activate" > .profile
RUN npm install

# copy the app
ADD --chown=$USER:$USER . ./

# can run "python3 -m http.server" to browse html report at "http://localhost:8000/page.0.html"
# docker run -p 127.0.0.1:8000:8000/tcp -it IMAGE
EXPOSE 8000

ENTRYPOINT [ "/bin/sh" ]
