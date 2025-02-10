import pytest
from click.testing import CliRunner


@pytest.fixture
def clirunner() -> CliRunner:
    """Provides a CLI test runner."""
    return CliRunner()
