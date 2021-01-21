## Prerequisites

Please ensure following the [Developer Setup](guides/developer_setup.md) before developing \
for this project to ensure correct environment setup.

---
## Approaching this repo

After you've done the necessary developer setup, look through here for some quick first steps.

### Helpful Scripts
Lint with isort and black (or use pre-commit):
> poetry run scripts/lint.sh

Run the tests:
> poetry run scripts/test.sh

Create a docker image:
> poetry run scripts/build.sh

Run the created image like so:
> poetry run scripts/run.sh

Kill all running images with this namespace:
> poetry run scripts/kill.sh


#### Hint
These may need to be made executable...
> chmod +x scripts/<file_name>

---
## Running the Server

### Poetry

Run a reloading server through poetry and uvicorn locally (CTRL+C to kill):
> poetry run uvicorn containerized_microservice_template.app:app  --host 0.0.0.0 --port 80 --reload

### Docker

Run a container image locally in the background with (the return is the CONTAINER ID of the image):
> docker run -d -p 80:80 containerized_microservice_template:latest

View running containers:
> docker ps

Tail the logs with:
> docker logs <CONTAINER ID> -f

Kill the running container with (teardown might take a few moments):
> docker stop <CONTAINER ID>

---
## Viewing the Server

View the app at [0.0.0.0:80/](0.0.0.0:80/)
You should be redirected to the /docs page.
