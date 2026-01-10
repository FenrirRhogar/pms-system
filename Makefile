all: relaunch

stop:
	docker-compose down -v

build:
	docker-compose up --build

relaunch: stop build
