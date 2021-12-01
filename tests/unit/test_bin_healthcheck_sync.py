"""Check ctms/bin/healthcheck_sync.py"""

from datetime import datetime, timedelta, timezone

from structlog.testing import capture_logs

from ctms.bin.healthcheck_sync import main
from ctms.config import Settings
from ctms.sync import update_healthcheck


def test_main_recent_update(tmp_path):
    """healthcheck_sync succeeds on recent update."""
    health_path = tmp_path / "healthcheck"
    update_healthcheck(health_path)
    settings = Settings(
        background_healthcheck_path=str(health_path),
        background_healthcheck_age_s=30,
    )
    with capture_logs() as caplogs:
        exit_code = main(settings)
    assert exit_code == 0
    assert len(caplogs) == 1
    log = caplogs[0]
    assert log["event"] == "Healthcheck passed"
    assert log["age"] < 0.1


def test_main_old_update(tmp_path):
    """healthcheck_sync fails on old update."""
    health_path = tmp_path / "healthcheck"
    old_date = datetime.now(tz=timezone.utc) - timedelta(seconds=120)
    old_date_iso = old_date.isoformat()
    with open(health_path, "w", encoding="utf8") as health_file:
        health_file.write(old_date_iso)
    settings = Settings(
        background_healthcheck_path=str(health_file),
        background_healthcheck_age_s=30,
    )
    with capture_logs() as caplogs:
        exit_code = main(settings)
    assert exit_code == 1
    assert len(caplogs) == 1
    log = caplogs[0]
    assert log == {
        "event": "Healthcheck failed",
        "exc_info": True,
        "log_level": "error",
    }
