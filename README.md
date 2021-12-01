# ConTact Management System (CTMS)

While the app is running, interactive API documentation can found at the following relative paths: /docs, /redoc.

OpenApiSpec(OAS) formatted in JSON can be found at the following path: /openapi.json

---

[View All Docs](docs/README.md)

---

## Prerequisites

Please ensure following the [Developer Setup](docs/developer_setup.md) before developing \
for this project to ensure correct environment setup.

Then please view the [First Steps](docs/first_steps.md) for some basics.

---
## Project Structure

The project is structured with the following in mind:

- docs/*
    - Documentation to guide others around the project interactions
- ctms/*
    - Operational source code exists here
    - app.py
        - FastAPI Handling of HTTP Requests and routing to services
    - bin/*
        - Scripts intended for background machinery
    - models.py
        - SQLAlchemy models for ORM tool, SqlAlchemy
    - schemas/*
        - Pydantic Models for Data Modeling and Contract Validation, Pydantic
- tests/unit/*
    - Test suite using pytest
