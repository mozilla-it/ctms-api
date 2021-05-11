from typing import Any, Tuple

import pytest

@pytest.mark.parametrize("method", ("HEAD", "GET"))
@pytest.mark.parametrize("path", ("/__lbheartbeat__", "/__heartbeat__"))
def test_monitoring_endpoints(anon_client, db_session, method, path):
    """Monitoring endpoints can be called without credentials"""
    resp = anon_client.request(method, path)
    assert resp.status_code == 200
