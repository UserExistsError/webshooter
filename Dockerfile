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
ARG UID=99999
ARG GID=99999

# add new user
WORKDIR /web
RUN addgroup -S -g $GID $USER && \
    adduser -S -G $USER -h /web -D -u $UID $USER
USER $USER

# install python dependencies in a virtualenv
ADD --chown=$USER:$USER requirements.txt ./
RUN python -m venv .webshooter && \
    source .webshooter/bin/activate && \
    pip install --no-cache-dir -r requirements.txt && \
    echo "source .webshooter/bin/activate" > .profile

# copy the app and install
ADD --chown=$USER:$USER . ./
RUN source .webshooter/bin/activate && \
    pip install .

# allow running the container as a different user
RUN chmod -R o+rw ./

# can run "python3 -m http.server" to browse html report at "http://localhost:8000/page.0.html"
# docker run -p 127.0.0.1:8000:8000/tcp -it IMAGE
EXPOSE 8000

ENTRYPOINT [ "/bin/sh" ]
