"""Bounded, read-only market-data checks. Credentials never enter output files."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.request import Request, urlopen, HTTPRedirectHandler, build_opener
from urllib.parse import urlencode
from urllib.error import HTTPError
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'research' / 'alpaca_probe'


def load_credentials():
    fields = {}
    for line in (ROOT / '.env').read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('export '):
            line = line[7:].strip()
        if '=' not in line:
            continue
        name, value = line.split('=', 1)
        value = value.strip()
        if value.startswith(('"', "'")) and value[-1:] == value[:1]:
            value = value[1:-1]
        else:
            value = value.split(' #', 1)[0].strip()
        fields[name.strip()] = value
    key = next((fields.get(k) for k in ['ALPACA_API_KEY', 'APCA_API_KEY_ID'] if fields.get(k)), '')
    secret = next((fields.get(k) for k in ['ALPACA_SECRET_KEY', 'ALPACA_API_SECRET', 'ALPACA_API_SECRET_KEY', 'APCA_API_SECRET_KEY'] if fields.get(k)), '')
    return key, secret


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    key, secret = load_credentials()
    if not key or not secret:
        print(json.dumps({'status': 'missing_credentials', 'key_present': bool(key), 'secret_present': bool(secret)}))
        return 2
    OUT.mkdir(exist_ok=True)

    def safe(text):
        for value in [key, secret]:
            text = text.replace(value, '[REDACTED]')
        return text[:500]

    def fetch(name, params):
        request = Request('https://data.alpaca.markets/v2/stocks/bars?' + urlencode(params), headers={
            'APCA-API-KEY-ID': key, 'APCA-API-SECRET-KEY': secret,
            'Accept': 'application/json', 'User-Agent': 'PriceActionResearch-ReadOnlyProbe/1.0'})
        record = {'test': name, 'parameters': params}
        try:
            with build_opener(NoRedirects()).open(request, timeout=25) as response:
                payload = response.read()
                record['http_status'] = response.status
            body = json.loads(payload)
            bars = body.get('bars') or {}
            problems = []
            summaries = {}
            for symbol, rows in bars.items():
                timestamps = [row['t'] for row in rows]
                if timestamps != sorted(timestamps) or len(timestamps) != len(set(timestamps)):
                    problems.append(symbol + ': invalid timestamp ordering/duplicates')
                for row in rows:
                    if not (0 < row['l'] <= min(row['o'], row['c']) <= max(row['o'], row['c']) <= row['h']) or row['v'] < 0:
                        problems.append(symbol + ': invalid OHLCV')
                summaries[symbol] = {'count': len(rows), 'first': timestamps[0] if timestamps else None,
                                     'last': timestamps[-1] if timestamps else None}
            destination = OUT / (name + '.json')
            destination.write_bytes(payload)
            record.update({'symbols': summaries, 'has_next_page': bool(body.get('next_page_token')),
                           'validation_errors': problems, 'response_file': destination.name,
                           'sha256': hashlib.sha256(payload).hexdigest()})
            return record, body
        except HTTPError as exc:
            record.update({'http_status': exc.code, 'error': safe(exc.read(4096).decode('utf-8', errors='replace'))})
        except Exception as exc:
            record.update({'error_type': type(exc).__name__, 'error': safe(str(exc))})
        return record, None

    def params(symbols, start, end, feed='sip', adjustment='raw', limit=1000):
        return dict(symbols=symbols, timeframe='1Min', start=start, end=end,
                    feed=feed, adjustment=adjustment, limit=limit, sort='asc')

    jobs = [
        ('recent_sip', params('SPY,QQQ,IWM,DIA,AAPL,MSFT', '2026-11-05T14:30:00Z', '2026-11-05T14:34:59Z')),
        ('recent_iex', params('SPY,QQQ,IWM,DIA,AAPL,MSFT', '2026-11-05T14:30:00Z', '2026-11-05T14:34:59Z', feed='iex')),
        ('history_2016_sip', params('SPY,QQQ,IWM,DIA', '2016-01-04T14:30:00Z', '2016-01-04T14:34:59Z')),
        ('history_2022_sip', params('SPY,QQQ,IWM,DIA', '2022-01-03T14:30:00Z', '2022-01-03T14:34:59Z')),
        ('split_raw', params('AAPL', '2020-08-28T13:30:00Z', '2020-08-28T13:34:59Z')),
        ('split_adjusted', params('AAPL', '2020-08-28T13:30:00Z', '2020-08-28T13:34:59Z', adjustment='split')),
    ]
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda item: fetch(*item), jobs))
    records = [r for r, _ in results]
    bodies = {r['test']: b for r, b in results}

    page_params = params('SPY,QQQ', '2026-11-05T14:30:00Z', '2026-11-05T14:34:59Z', limit=2)
    first, body = fetch('pagination_page_1', page_params)
    records.append(first)
    pagination = {'tested': False}
    if body and body.get('next_page_token'):
        second, next_body = fetch('pagination_page_2', dict(page_params, page_token=body['next_page_token']))
        second['parameters'].pop('page_token', None)
        records.append(second)
        if next_body:
            a = {(s, r['t']) for s, rows in body['bars'].items() for r in rows}
            b = {(s, r['t']) for s, rows in next_body['bars'].items() for r in rows}
            pagination = {'tested': True, 'nonoverlapping_pages': not bool(a & b), 'page_1_count': len(a), 'page_2_count': len(b),
                          'note': 'Two-page cursor smoke test only; full multi-symbol exhaustion is not verified.'}

    adjustment = {'tested': False}
    raw = bodies.get('split_raw')
    adjusted = bodies.get('split_adjusted')
    if raw and adjusted:
        raw_rows = {r['t']: r for r in raw.get('bars', {}).get('AAPL', [])}
        adjusted_rows = {r['t']: r for r in adjusted.get('bars', {}).get('AAPL', [])}
        shared = sorted(raw_rows.keys() & adjusted_rows.keys())
        adjustment = {'tested': bool(shared), 'matched_timestamps': len(shared),
                      'raw_to_split_adjusted_close_ratios': [round(raw_rows[t]['c']/adjusted_rows[t]['c'], 6) for t in shared]}

    recent = next(r for r in records if r['test'] == 'recent_sip')
    expected = {'SPY','QQQ','IWM','DIA','AAPL','MSFT'}
    access_ok = recent.get('http_status') == 200 and expected <= set(recent.get('symbols', {})) and all(recent['symbols'][s]['count'] == 5 for s in expected) and not recent.get('validation_errors')
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'purpose': 'Bounded read-only historical equity market-data preflight',
              'status': 'historical_sip_sample_verified' if access_ok else 'needs_attention', 'requests': records,
              'pagination': pagination, 'split_adjustment': adjustment,
              'limitations': ['No trading/account-management endpoints called', 'No subscription tier inferred or changed',
                             'Small date samples do not prove complete multi-year coverage', 'Dividend, symbol history and borrow data not validated',
                             'Response files contain public-market bars and provider pagination cursors, never API credentials']}
    (OUT/'report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if access_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
