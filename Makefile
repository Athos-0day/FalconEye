NETWORK=falconnet

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f

alerts:
	./src/alerts/alerts.sh
