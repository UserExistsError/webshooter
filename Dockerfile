FROM python:3.13-slim

ENV WEBSHOOTER_DOCKER=yes

ARG USER=websh
ARG UID=54321

# add new user
RUN groupadd --gid $UID $USER && \
    useradd --shell /bin/bash --create-home --home-dir /web --uid $UID --gid $UID $USER
USER $USER
WORKDIR /web

# install python dependencies in a virtualenv
ADD --chown=$USER:$USER requirements.txt ./
RUN python -m venv .webshooter && \
    . .webshooter/bin/activate && \
    pip install --no-cache-dir -r requirements.txt && \
    echo >> .bashrc && \
    echo ". .webshooter/bin/activate" >> .bashrc

# copy the app and install
ADD --chown=$USER:$USER . ./
RUN . .webshooter/bin/activate && \
    pip install .

# allow running the container as a different user
#RUN chmod -R o+rw ./

# can run "python3 -m http.server" to browse html report at "http://localhost:8000/page.0.html"
# docker run -p 127.0.0.1:8000:8000/tcp -it IMAGE
EXPOSE 8000

ENTRYPOINT [ "/bin/bash" ]
