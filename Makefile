default:

run:
	vault2env -k secret/private/mqttcli -- envrun -- ./.venv/bin/python main.py

requirements: .venv
	./.venv/bin/pip install -r requirements.txt

.venv:
	python -m venv .venv
