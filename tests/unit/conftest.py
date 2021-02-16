"""pytest fixtures for the CTMS app"""
import pytest
from fastapi.testclient import TestClient

from ctms.app import app


@pytest.fixture
def client():
    return TestClient(app)
