"""
Common test configuration both unit and integration tests.
"""

from datetime import datetime

import pytest


class Whatever:
    """
    This class is a testing helper that provides flexible equality
    of values.

    .. code-block::

        >>> Whatever(lambda x: x.startswith("a")) == "abc"
        True
        >>> Whatever(lambda x: x % 2 == 0) == 11
        False

    It is mainly used to make sure fields contain valid dates
    without having to hardcode values:

    .. code-block::

        >>> Whatever.iso8601() == "2020-01-01"
        True
        >>> Whatever.iso8601() == None
        False
    """

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
