from contextlib import contextmanager

import pytest

from app import raghu_vast as vast, store


@pytest.mark.parametrize(
    "reason,destroyed,tries",
    [
        ("SSH port did not respond", True, 2),
        ("SSH port did not respond", False, 1),
        ("SSH key authentication failed", True, 1),
        ("SSH host identity check failed", True, 1),
    ],
)
def test_startup_replacement_requires_retryable_error_and_verified_cleanup(
    monkeypatch, tmp_path, reason, destroyed, tries
):
    calls = []
    progress = []

    @contextmanager
    def attempt(folder, ident, check, **options):
        calls.append(options)
        if len(calls) == 1:
            store.save(folder / "raghu-rental.json", {
                "id": 42, "destroyed": destroyed, "started": 900, "rate": 0.72,
            })
            raise vast.VastStartupError(reason)
        yield "replacement"

    monkeypatch.setattr(vast, "_rent_once", attempt)
    monkeypatch.setattr(vast.time, "time", lambda: 1000)
    operation = vast.rent(tmp_path, "job", lambda: None, progress=lambda *event: progress.append(event))
    if tries == 2:
        with operation as rental:
            assert rental == "replacement"
        assert calls[1]["startup_spent"] == pytest.approx(0.02)
        assert progress and "First rental released" in progress[0][0]
    else:
        with pytest.raises(vast.VastStartupError, match=reason), operation:
            pytest.fail("A rental was unexpectedly opened")
    assert len(calls) == tries


def test_distinct_vast_ssh_endpoints(tmp_path):
    row = {"public_ipaddr": "192.0.2.10", "ports": {"22/tcp": [{"HostPort": "30022"}]},
           "ssh_host": "ssh.example.com", "ssh_port": "50022"}
    direct = vast.Remote(row, tmp_path, tmp_path, 0, lambda: None)
    reported = vast.Remote(row, tmp_path, tmp_path, 0, lambda: None, reported_endpoint=True)
    assert (direct.host, direct.port) == ("root@192.0.2.10", 30022)
    assert (reported.host, reported.port) == ("root@ssh.example.com", 50022)


def test_failed_container_requires_stopped_contract_to_switch_hosts():
    row = dict(actual_status="loading", cur_state="stopped", next_state="stopped",
               intended_status="stopped", status_msg="dial /run/containerd/containerd.sock: refused")
    assert vast.stopped_failed_start(row)
    assert not vast.stopped_failed_start({**row, "next_state": "running"})
    assert not vast.stopped_failed_start({**row, "uptime_mins": 1})
    assert not vast.stopped_failed_start({**row, "actual_status": "running"})


def test_preservation_stops_without_destroying(monkeypatch, tmp_path):
    journal = tmp_path / "raghu-rental.json"
    store.save(journal, {"id": 42, "label": "job", "destroyed": False})
    row = {"id": 42, "label": "job", "actual_status": "running"}
    monkeypatch.setattr(vast, "instances", lambda: [row])
    calls = []

    def stop(action, ident):
        calls.append((action, ident))
        row["actual_status"] = "stopped"

    monkeypatch.setattr(vast, "request_instance_state", stop)
    vast.close_rental(journal, preserve=True)
    assert calls == [("stop", 42)]
    assert store.read(journal)["recovery_stop"]
    assert not store.read(journal)["destroyed"]
