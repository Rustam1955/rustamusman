from PIL import Image, ImageFilter, ImageOps, ImageDraw, ImageFont
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
INPUT = os.path.join(BASE_DIR, 'static', 'img', 'book.jpeg')
OUT_DIR = os.path.join(BASE_DIR, 'static', 'img')

os.makedirs(OUT_DIR, exist_ok=True)

def fit_image(im, size):
    im.thumbnail(size, Image.LANCZOS)
    return im


def add_shadow(im, offset=(10,10), background=0x00000000, shadow_color=0x44000000, blur_radius=20):
    total = Image.new('RGBA', (im.width + abs(offset[0]) + blur_radius*2, im.height + abs(offset[1]) + blur_radius*2), background)
    shadow = Image.new('RGBA', im.size, shadow_color)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur_radius))
    total.paste(shadow, (blur_radius + max(offset[0],0), blur_radius + max(offset[1],0)), shadow)
    total.paste(im, (blur_radius + max(-offset[0],0), blur_radius + max(-offset[1],0)), im)
    return total


def make_square_logo():
    im = Image.open(INPUT).convert('RGBA')
    size = 1024
    bg = Image.new('RGBA', (size, size), (0,0,0,0))
    fit_image(im, (int(size*0.85), int(size*0.85)))
    # add shadow
    im_with_shadow = add_shadow(im, offset=(0,10), blur_radius=24)
    # center
    x = (size - im_with_shadow.width)//2
    y = (size - im_with_shadow.height)//2
    bg.paste(im_with_shadow, (x,y), im_with_shadow)
    out_path = os.path.join(OUT_DIR, 'logo_book.png')
    bg.save(out_path)
    print('Saved', out_path)
    return out_path


def make_circle_badge(square_path):
    im = Image.open(square_path).convert('RGBA')
    size = im.width
    mask = Image.new('L', (size,size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0,0,size,size), fill=255)
    circ = Image.new('RGBA', (size,size), (0,0,0,0))
    circ.paste(im, (0,0), mask)
    # draw ring
    draw2 = ImageDraw.Draw(circ)
    ring_width = int(size*0.04)
    draw2.ellipse((ring_width/2, ring_width/2, size-ring_width/2, size-ring_width/2), outline=(230,200,120,255), width=ring_width)
    out_path = os.path.join(OUT_DIR, 'logo_book_circle.png')
    circ.save(out_path)
    print('Saved', out_path)
    return out_path


def make_favicons(square_path):
    im = Image.open(square_path).convert('RGBA')
    sizes = [32, 64, 128, 180]
    for s in sizes:
        out = im.resize((s,s), Image.LANCZOS)
        out_path = os.path.join(OUT_DIR, f'favicon-{s}.png')
        out.save(out_path)
        print('Saved', out_path)
    # create .ico
    ico_path = os.path.join(OUT_DIR, 'favicon.ico')
    imico = im.resize((64,64), Image.LANCZOS)
    imico.save(ico_path, sizes=[(64,64),(32,32)])
    print('Saved', ico_path)


if __name__ == '__main__':
    if not os.path.exists(INPUT):
        print('Input image not found:', INPUT)
        raise SystemExit(1)
    square = make_square_logo()
    badge = make_circle_badge(square)
    make_favicons(square)
    print('All assets generated in', OUT_DIR)
