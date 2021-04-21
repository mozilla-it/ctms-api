## Prerequisites

Please ensure following the [Developer Setup](guides/developer_setup.md) before developing \
for this project to ensure correct environment setup.

---
## Approaching this repo

After you've done the necessary developer setup, look through here for some quick first steps.

> Use `make help` to see additional make commands that help with setup, starting, and testing.

### Helpful Scripts
```sh
poetry run scripts/{lint|test|build|run|kill|update_baseline}.sh
```

#### Caveat
These may need to be made executable...
```sh
chmod +x scripts/<file_name>
```

---
## Running the Server

### Poetry

Run a reloading server through poetry and uvicorn locally (CTRL+C to kill):
```sh
poetry run uvicorn ctms.app:app  --host 0.0.0.0 --port 80 --reload
```

### Docker

Run a container image locally in the background with (the return is the CONTAINER ID of the image):
```sh
docker run -d -p 80:80 ctms-api:latest
```

View running containers:
```sh
docker ps
```

Tail the logs with:
```sh
docker logs <CONTAINER ID> -f
```

Kill the running container with (teardown might take a few moments):
```sh
docker stop <CONTAINER ID>
```

---
## Viewing the Server

View the app at [0.0.0.0:80/](http://0.0.0.0:80/)
You should be redirected to the /docs page.

---
[View All Docs](./)
