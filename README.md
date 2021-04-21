# CTMS API

This is a work-in-progress for the Contact Management System (CTMS) API.

While the app is running, the API documentation can found at the following relative paths: /docs, /redoc.

OAS spec can be found at the following path: /openapi.json

---
## Template Docs

[View All Docs](./guides/)
- [Developer Setup](guides/developer_setup.md)
- [First Steps](guides/first_steps.md)
- [Deployment Guide](guides/deployment_guide.md)
- [Configuration](guides/configuration.md)
- [Testing Strategy](guides/testing_strategy.md)
- [Auto Documentation Setup](guides/auto_documentation.md)

---
## Prerequisites

Please ensure following the [Developer Setup](guides/developer_setup.md) before developing \
for this project to ensure correct environment setup.

Then please view the [First Steps](guides/first_steps.md) for some basics.

[Others docs here as well](./guides/).

---
## Project Structure

The project is structured with the following in mind:

- docs/*
    - Auto-generated Sphinx docs live here.
- guides/*
    - Documentation to guide others around the project interactions
- ctms/*
    - Operational source code exists here
    - app.py
        - FastAPI Handling of HTTP Requests and routing to services
    - bin/*
        - Scripts intended for background machinery
    - schemas/*
        - Pydantic Models for Data Modeling, and Contract Validation
        - SQLAlchemy models
- tests/unit/*
    - Test suite using pytest

---
### Based on containerized-microservice-template

[containerized-microservice-template](https://github.com/mozilla-it/containerized-microservice-template)
is a mozilla-it github repo template.

### References & Regards
- https://github.com/tiangolo/fastapi
- https://github.com/samuelcolvin/pydantic
- https://github.com/michael0liver/python-poetry-docker-example
