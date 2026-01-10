all: relaunch

stop:
	docker-compose down

build:
	docker-compose up --build

relaunch: stop build
