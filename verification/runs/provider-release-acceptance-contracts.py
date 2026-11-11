"""Authored provider failures, bounded backoff and original page-chain recovery."""
from pathlib import Path

import httpx
import pytest

from backend.lab.provider import Alpaca, ProviderError


@pytest.fixture
def local_provider(tmp_path, monkeypatch):
    credentials = tmp_path / "authored-provider-credentials.txt"
    credentials.write_text("ALPACA_API_KEY=fixture-key\nALPACA_SECRET_KEY=fixture-secret\n", encoding="utf-8")
    now, sleeps = [10.0], []
    monkeypatch.setattr("backend.lab.provider.time.monotonic", lambda: now[0])
    def sleep(seconds):
        sleeps.append(seconds)
        now[0] += seconds
    monkeypatch.setattr("backend.lab.provider.time.sleep", sleep)
    return credentials, tmp_path / "cache", sleeps


@pytest.mark.parametrize("status", [401, 403])
def test_invalid_or_revoked_credentials_report_status_without_secrets(local_provider, status):
    credentials, cache, _ = local_provider
    seen = []
    def reject(request):
        seen.append(request)
        return httpx.Response(status, text="fixture-key fixture-secret", headers={"x-secret": "fixture-secret"})
    with Alpaca(credentials, cache, httpx.MockTransport(reject)) as provider:
        with pytest.raises(ProviderError) as caught:
            provider.bars(["SPY"], "2022-01-03", "2022-01-03")
    text = str(caught.value)
    assert f"HTTP {status}" in text and "fixture-key" not in text and "fixture-secret" not in text
    assert len(seen) == 1 and seen[0].url.params["feed"] == "sip"


@pytest.mark.parametrize("failure", [429, 503, "timeout"])
def test_retry_budget_and_error_state_are_bounded(local_provider, failure):
    credentials, cache, sleeps = local_provider
    calls = []
    def unavailable(request):
        calls.append(request)
        if failure == "timeout":
            raise httpx.ReadTimeout("fixture-secret", request=request)
        return httpx.Response(failure, text="fixture-secret")
    with Alpaca(credentials, cache, httpx.MockTransport(unavailable)) as provider:
        with pytest.raises(ProviderError) as caught:
            provider.bars(["SPY"], "2022-01-03", "2022-01-03")
        assert provider.last_query_receipt["complete"] is False
    assert len(calls) == 5
    assert sleeps == [.25] * 60 and sum(sleeps) == 15
    assert "fixture-secret" not in str(caught.value)
    assert ("timed out or failed" if failure == "timeout" else f"HTTP {failure}") in str(caught.value)
    assert all(request.url.path == "/v2/stocks/bars" and request.url.params["feed"] == "sip" for request in calls)


def test_interrupted_page_chain_resumes_without_repeating_accepted_pages(local_provider):
    credentials, cache, _ = local_provider
    calls, canceled = [], [False]
    def page(request):
        calls.append(request.url.params.get("page_token"))
        second = calls[-1] == "second"
        symbol = "SPY" if second else "QQQ"
        return httpx.Response(200, json={
            "bars": {symbol: [{"t": "2022-01-03T14:30:00Z", "o": 100, "h": 101, "l": 99, "c": 100, "v": 1000}]},
            "next_page_token": None if second else "second",
        })
    def stop_after_first_page(_):
        canceled[0] = True
    with Alpaca(credentials, cache, httpx.MockTransport(page)) as provider:
        with pytest.raises(InterruptedError):
            provider.bars(["SPY", "QQQ"], "2022-01-03", "2022-01-03",
                          cancel=lambda: canceled[0], progress=stop_after_first_page)
        assert provider.last_query_receipt["complete"] is False and len(calls) == 1
        assert len(list(cache.rglob("page-*.json"))) == 1
        canceled[0] = False
        frame, metadata = provider.bars(["SPY", "QQQ"], "2022-01-03", "2022-01-03",
                                        cancel=lambda: canceled[0])
        assert calls == [None, "second"] and set(frame.symbol) == {"SPY", "QQQ"} and len(frame) == 2
        assert metadata["page_receipt"]["complete"] is True
        assert [page["cached"] for page in metadata["page_receipt"]["pages"]] == [True, False]
        reread, repeated = provider.bars(["SPY", "QQQ"], "2022-01-03", "2022-01-03")
        assert len(calls) == 2 and reread.to_dict("records") == frame.to_dict("records")
        assert all(page["cached"] for page in repeated["page_receipt"]["pages"])
