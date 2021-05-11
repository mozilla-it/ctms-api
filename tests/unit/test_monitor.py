from typing import Any, Tuple

import pytest

MONITOR_API_TEST_CASES: Tuple[Tuple[str, str, Any], ...] = (
    ("HEAD", "/__lbheartbeat__", None),
    ("GET", "/__lbheartbeat__", None),
    ("HEAD", "/__heartbeat__", None),
    ("GET", "/__heartbeat__", None),
)


@pytest.mark.parametrize("method,path,params", MONITOR_API_TEST_CASES)
def test_unauthorized_api_call_fails(
    anon_client, example_contact, method, path, params
):
    """Calling the API without credentials fails."""
    _map = {  # METHOD: ( {_REQUEST_PARAMS} , {_EXPECTED_RESULTS}
        "GET": ({"method": "GET", "url": path, "params": params}, {200}),
        "HEAD": ({"method": "HEAD", "url": path}, {200}),
    }
    if method in _map.keys():
        _request, _results = _map.get(method)
        resp = anon_client.request(**_request)
        assert resp.status_code in _results


@pytest.mark.parametrize("method,path,params", MONITOR_API_TEST_CASES)
def test_authorized_api_call_succeeds(client, example_contact, method, path, params):
    """Calling the API without credentials fails."""
    _map = {  # METHOD: ( {_REQUEST_PARAMS} , {_EXPECTED_RESULTS}
        "GET": ({"method": "GET", "url": path, "params": params}, {200}),
        "HEAD": ({"method": "HEAD", "url": path}, {200}),
    }
    if method in _map.keys():
        _request, _results = _map.get(method)
        resp = client.request(**_request)
        assert resp.status_code in _results
