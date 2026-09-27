.PHONY: install build test lint lint-fix format format-check clean

install:
	npm install

build:
	npm run build

test:
	npm test

lint:
	npm run lint

lint-fix:
	npm run lint:fix

format:
	npm run format

format-check:
	npm run format:check

clean:
	npm run clean
