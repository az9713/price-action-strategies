"""Extract exact source-video frames; never open credentials or contact a provider."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import json
import hashlib

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'source' / 'video.mkv'
OUT = ROOT / 'screenshots'
OUT.mkdir(exist_ok=True)
SCREENS = [
    ('concept_map', 73), ('ten_setups', 208), ('subjective_levels', 258),
    ('methodology', 304), ('funnel', 425), ('win_rate_profit', 450),
    ('timeframe_costs', 482), ('random_levels', 516), ('touch_count', 540),
    ('level_rule_effects', 591), ('structure_follow_through', 614),
    ('trend_families', 620), ('common_trend_rules', 627),
    ('confirmation', 641), ('stop_models', 665), ('context_filters', 683),
    ('cross_market_check', 700), ('holdout_market', 719),
    ('holdout_timeframes', 734), ('selected_equity_curves', 765),
    ('family_robustness', 790), ('example_trade', 875),
    ('prompt_page_02', 964.25), ('prompt_page_03', 971.25),
    ('prompt_page_04', 972.25), ('prompt_page_05', 973.25),
    ('prompt_page_06', 975.25), ('prompt_page_07', 977.25),
    ('prompt_page_08', 979.25), ('prompt_page_09', 981.25),
    ('prompt_page_10', 982.25), ('prompt_page_11', 983.25),
    ('prompt_page_12', 985.25), ('prompt_page_13', 987.25),
    ('prompt_page_14', 988.25), ('prompt_page_15', 989.25),
    ('prompt_page_16', 991.25),
]

def capture(item):
    name, seconds = item
    target = OUT / f'{name}.png'
    result = subprocess.run([
        'ffmpeg', '-hide_banner', '-loglevel', 'error', '-nostdin',
        '-ss', str(seconds), '-threads', '2', '-i', str(SOURCE),
        '-frames:v', '1', '-update', '1', '-y', str(target)
    ], capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f'{name}: {result.stderr[-1000:]}')
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    return {'id': name, 'source_seconds_requested': seconds,
            'source_frame_index_approx': round(seconds * 30),
            'path': target.relative_to(ROOT).as_posix(),
            'sha256': digest,
            'source_url': f'https://www.youtube.com/watch?v=z97PnFIPoFg&t={int(seconds)}s'}

if __name__ == '__main__':
    entries = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(capture, item) for item in SCREENS]
        for future in as_completed(futures):
            entry = future.result()
            entries.append(entry)
            print(f'Captured {entry["id"]} at {entry["source_seconds_requested"]}s', flush=True)
    entries.sort(key=lambda e: e['source_seconds_requested'])
    (ROOT/'screenshot-manifest.json').write_text(json.dumps({
        'source': 'source/video.mkv', 'method': 'FFmpeg accurate input seek; one unaltered decoded frame per screenshot',
        'resolution': [3840,2160], 'screenshots': entries,
        'timestamp_note': 'Requested times; nearest representable source frame, approximately within one frame. Not exact transition boundaries.'
    },indent=2),encoding='utf-8')
    print(f'Complete: {len(entries)} screenshots', flush=True)
