FROM python:3.11

ARG VERSION 1.2.0
ENV VERSION ${VERSION}
ENV PKG smartmetertx2mongo-${VERSION}.tar.gz


RUN addgroup --gid=200 apps
RUN adduser --system --home=/var/lib/smartmetertx --uid=200 --gid=200 smartmetertx
USER smartmetertx
VOLUME /var/lib/smartmetertx/.config/smartmetertx
WORKDIR /var/lib/smartmetertx
RUN mkdir -m0700 ~/.gnupg

RUN python3 -m venv .

# Assume we ran `setup.py sdist` already.
COPY dist/${PKG} /tmp/${PKG}

RUN . bin/activate && pip install -U pip PyYAML
RUN . bin/activate && pip install /tmp/${PKG}

ENTRYPOINT ["/usr/bin/python3.11"]
CMD ["/var/lib/smartmetertx/bin/smtx-server.py"]
