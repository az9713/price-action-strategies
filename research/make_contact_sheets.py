from pathlib import Path
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parent
frames = sorted((root / 'review_frames').glob('sec_*.jpg'))
out = root / 'contact_sheets'
out.mkdir(exist_ok=True)
cols, rows, w, h = 5, 10, 384, 240
for start in range(0, len(frames), cols * rows):
    sheet = Image.new('RGB', (cols*w, rows*h), '#111111')
    draw = ImageDraw.Draw(sheet)
    for i, path in enumerate(frames[start:start+cols*rows]):
        second = int(path.stem.split('_')[1]) - 1
        x, y = (i % cols)*w, (i // cols)*h
        with Image.open(path) as im:
            im.thumbnail((w, 216))
            sheet.paste(im, (x, y+24))
        draw.text((x+5, y+4), f'{second//60:02}:{second%60:02} | sample {second}s', fill='white')
    sheet.save(out / f'sheet_{start:04d}.jpg', quality=90)
print(f'{len(frames)} frames in {len(list(out.glob("*.jpg")))} sheets')
