import pathlib
from PIL import Image, ImageFont
from richery import canvas

for res, fnt, idx in (
    ("txt_chs.txt", "FZSSK", 0),
    ("txt_hgl.txt", "KCC-KP-CheongPong-Medium-KP-2011KPS", 0),
    ("txt_lat.txt", "times", 0),
    ("txt_color.txt", "sarasa-regular", 27)
):
    content = pathlib.Path(res).read_text()

    im = Image.new(size=(1000, 1000), mode="RGBA", color=(255, 255, 255))
    rcv = canvas.RichCanvas(im)
    font = ImageFont.truetype(fnt, 24, idx)
    ff = canvas.FontFamily(Regular=font)  # type: ignore

    region = canvas.Rect.from_ltrb((100, 100), (900, 900))
    tds = canvas.TextDrawState(region, (), [(ff, None)], 26)
    rcv.text(tds, content, justify=True)
    im.show()
