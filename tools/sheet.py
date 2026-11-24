"""Contact sheet: python tools/sheet.py out.png cols img1 img2 ..."""
import sys, os
from PIL import Image, ImageDraw
out, cols = sys.argv[1], int(sys.argv[2])
files = sys.argv[3:]
W = 640
ims = []
for f in files:
    im = Image.open(f).convert('RGB')
    im = im.resize((W, int(im.height * W / im.width)))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 8 + 7 * len(os.path.basename(f)), 16], fill=(0, 0, 0))
    d.text((4, 2), os.path.basename(f), fill=(255, 255, 255))
    ims.append(im)
H = ims[0].height
rows = (len(ims) + cols - 1) // cols
S = Image.new('RGB', (cols * W + (cols - 1) * 6, rows * H + (rows - 1) * 6), (30, 30, 40))
for i, im in enumerate(ims):
    S.paste(im, ((i % cols) * (W + 6), (i // cols) * (H + 6)))
S.save(out)
