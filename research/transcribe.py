from faster_whisper import WhisperModel
from pathlib import Path
import json

root = Path(__file__).resolve().parent
model = WhisperModel('small.en', device='cpu', compute_type='int8', cpu_threads=8)
segments, info = model.transcribe(str(root/'source'/'audio.wav'), beam_size=5, language='en', vad_filter=True)
items = []
with (root/'source'/'transcript.txt').open('w', encoding='utf-8') as f:
    for s in segments:
        item = {'start': s.start, 'end': s.end, 'text': s.text}
        items.append(item)
        f.write(f'[{s.start:07.2f}-{s.end:07.2f}] {s.text}\n')
        f.flush()
(root/'source'/'transcript.json').write_text(json.dumps(items, indent=2), encoding='utf-8')
print(f'Transcribed {len(items)} segments; language={info.language}')
