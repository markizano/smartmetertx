FROM python:3.11 as build

WORKDIR /app
COPY . .
RUN pip install -U uv
RUN uv build

FROM python:3.11

ARG VERSION 1.4.0
ENV VERSION=${VERSION}
ENV PKG=smartmetertx2mongo-${VERSION}*.tar.gz


RUN addgroup --gid=200 apps
RUN adduser --system --home=/var/lib/smartmetertx --uid=200 --gid=200 smartmetertx
USER smartmetertx
VOLUME /var/lib/smartmetertx/.config/smartmetertx
WORKDIR /var/lib/smartmetertx
RUN mkdir -m0700 ~/.gnupg

RUN python3 -m venv .

# Assume we ran `setup.py sdist` already.
COPY --from=build --chown=smartmetertx:smartmetertx /app/dist/smartmetertx2mongo-${VERSION}*.tar.gz /tmp/${PKG}

RUN . bin/activate && pip install -U pip PyYAML && pip install /tmp/${PKG} && rm -f /tmp/${PKG}

ENTRYPOINT ["/var/lib/smartmetertx/bin/python3"]
CMD ["/var/lib/smartmetertx/bin/smtx-server"]
