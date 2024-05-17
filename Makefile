
all: build dist
VERSION := $(shell cat VERSION).$(shell cat .build-id)

build:
	setup.py sdist
	docker build -t markizano/smartmetertx:$(VERSION) --build-arg=VERSION=$(VERSION) .
