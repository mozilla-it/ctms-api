"""
Common test configuration both unit and integration tests.
"""

from datetime import datetime

import pytest


class Whatever:
    def __init__(self, test=lambda x: True, name="unnamed"):
        self.test = test
        self.name = name

    def __eq__(self, other):
        return self.test(other)

    def __repr__(self):
        return f"<{self.__class__.__name__}.{self.name}>"

    @classmethod
    def iso8601(cls):
        def is_iso8601_date(sdate):
            if not isinstance(sdate, str):
                return False
            try:
                datetime.fromisoformat(sdate)
                return True
            except ValueError:
                return False

        return cls(is_iso8601_date, name="datetime")


@pytest.fixture
def whatever():
    return Whatever
