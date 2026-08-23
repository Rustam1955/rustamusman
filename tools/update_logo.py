from PIL import Image
import os

BASE = os.path.dirname(os.path.dirname(__file__))
IMG_DIR = os.path.join(BASE, 'static', 'img')
INPUT = os.path.join(IMG_DIR, 'logo.png')

def make_transparent(input_path):
    im = Image.open(input_path).convert('RGBA')
    px = im.load()
    w,h = im.size
    # sample background color from corners
    corners = [px[0,0], px[w-1,0], px[0,h-1], px[w-1,h-1]]
    # pick the most common corner color
    bg = max(set(corners), key=corners.count)
    br, bgc, bb, ba = bg
    def close(c1, c2, thresh=40):
        return sum((a-b)**2 for a,b in zip(c1,c2)) <= thresh*thresh

    for y in range(h):
        for x in range(w):
            r,g,b,a = px[x,y]
            if close((r,g,b),(br,bgc,bb), thresh=45):
                px[x,y] = (r,g,b,0)

    return im

def save_variants(im, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    # full transparent (overwrite logo.png backup)
    full = os.path.join(output_dir, 'logo_transparent.png')
    im.save(full)

    # resized
    small = im.copy()
    small.thumbnail((512,512), Image.LANCZOS)
    small.save(os.path.join(output_dir, 'logo_512.png'))

    # crop upper part (book emblem) to remove text if present
    w,h = im.size
    crop_box = (0, 0, w, int(h*0.66))
    emblem = im.crop(crop_box)
    emblem.save(os.path.join(output_dir, 'logo_emblem.png'))


if __name__ == '__main__':
    if not os.path.exists(INPUT):
        print('Input not found:', INPUT)
        raise SystemExit(1)
    backup = os.path.join(IMG_DIR, 'logo_orig.png')
    if not os.path.exists(backup):
        print('Creating backup', backup)
        Image.open(INPUT).save(backup)

    im = make_transparent(INPUT)
    save_variants(im, IMG_DIR)
    # overwrite logo.png with transparent version
    out_main = os.path.join(IMG_DIR, 'logo.png')
    im.save(out_main)
    print('Updated logo.png and saved variants in', IMG_DIR)
