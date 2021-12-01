# ConTact Management System (CTMS)

While the app is running, interactive API documentation can found at the following relative paths: /docs, /redoc.

OpenApiSpec(OAS) formatted in JSON can be found at the following path: /openapi.json

---

[View All Docs](docs/README.md)

---

## Prerequisites

Please ensure following the [Developer Setup](docs/developer_setup.md) before developing \
for this project to ensure correct environment setup.

---
## Project Structure

The project is structured with the following in mind:

- [docs/*](docs/)
    - Documentation to guide others around the project interactions
- [ctms/*](ctms/)
    - [bin/*](ctms/bin/)
        - Scripts intended for background machinery
    - [schemas/*](ctms/schemas/)
        - Pydantic Models for Data Modeling and Contract Validation, Pydantic
- [migrations/*](migrations/)
    - Alembic migrations that act as a changelog or version control system for implementing DB changes in an ordered fashion
- [scripts/*](scripts/)
    - Some scripts that have proven useful within the CTMS ecosystem
- [tests/unit/*](test/unit)
    - Test suite using pytest

---
## Important Files

Below are some files that are worth making note of:
- [MAKEFILE](Makefile)
    - Enabling commands such as: make {build | lint | setup | start | test | shell | test-shell | db-only}
- [ctms/app.py](ctms/app.py)
    - FastAPI handling of HTTP Requests and routing to services
- [ctms/bin/acoustic_sync.py](ctms/bin/acoustic_sync.py)
    - Background job for synchronizing pending records to Acoustic
- [ctms/config.py](ctms/config.py)
    - Environment variables are initialized here
- [ctms/models.py](ctms/models.py)
    - SQLAlchemy models for ORM tool
