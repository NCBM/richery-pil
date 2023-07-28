from collections import deque
from copy import deepcopy
from dataclasses import dataclass, field
from functools import reduce
from typing import NamedTuple, Optional, Sequence, Tuple, Type, Union
from PIL.Image import Image
from PIL.ImageDraw import Draw, ImageDraw
from PIL.ImageFont import ImageFont, FreeTypeFont, TransposedFont
from richery.ansitool import SGRState

from richery.colordef import RGBA, ColorTable, SupportsRGBA
from richery.textwork import combine, split

GenericFont = Union[ImageFont, FreeTypeFont, TransposedFont]


class Rect(NamedTuple):
    """Describe rectangle with x, y, w, h"""
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0

    @property
    def xy(self) -> Tuple[int, int]:
        """Data (x, y)"""
        return self.x, self.y

    @property
    def wh(self) -> Tuple[int, int]:
        """Data (w, h)"""
        return self.w, self.h

    @property
    def size(self) -> int:
        return self.w * self.h

    @property
    def lt(self) -> Tuple[int, int]:
        """Left-Top Point (x, y)"""
        return self.x, self.y

    @property
    def rt(self) -> Tuple[int, int]:
        """Right-Top Point (x + w, y)"""
        return self.x + self.w, self.y

    @property
    def lb(self) -> Tuple[int, int]:
        """Left-Bottom Point (x, y + h)"""
        return self.x, self.y + self.h

    @property
    def rb(self) -> Tuple[int, int]:
        """Right-Bottom Point (x + w, y + h)"""
        return self.x + self.w, self.y + self.h

    @property
    def ltrb(self) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """Left-Top Point and Right-Bottom Point (lt, rb)"""
        return self.lt, self.rb

    def subrect(self, w: int, h: int, /) -> Tuple[int, int, int, int]:
        """SubRect (left, top, right, bottom)"""
        return self.x, self.y, w - self.w - self.x, h - self.h - self.y

    @classmethod
    def _remap(cls, base: "Rect", target: "Rect") -> "Rect":
        x0, y0, w0, h0 = base
        x1, y1 = target.xy
        return cls(x1 + x0, y1 + y0, w0, h0)

    def remap(self, *rect: "Rect") -> "Rect":
        """Remap this rectangle to another rectangle"""
        return reduce(self._remap, (self, *rect))
    
    def __contains__(self, point: Tuple[int, int]) -> bool:
        _x, _y = point
        return (
            self.x <= _x <= self.x + self.w
            and self.y <= _y <= self.y + self.h
        )

    @classmethod
    def _cross(cls, self: "Rect", r: "Rect"):
        _x = max(self.x, r.x)
        _y = max(self.y, r.y)
        _w = max(
            0,
            self.w + r.w - max(self.x + self.w, r.x + r.w) + min(self.x, r.x)
        )
        _h = max(
            0,
            self.h + r.h - max(self.y + self.h, r.y + r.h) + min(self.y, r.y)
        )
        return cls(_x, _y, _w, _h)

    def __mul__(self, r: "Rect") -> "Rect":
        return self._cross(self, r)

    @classmethod
    def from_ltrb(cls, lt: Tuple[int, int], rb: Tuple[int, int]) -> "Rect":
        _x, _y, _xw, _yh = *lt, *rb
        if (_x > _xw) ^ (_y > _yh):
            raise ArithmeticError("not a valid ltrb pair")
        return cls(min(_x, _xw), min(_y, _yh), abs(_xw - _x), abs(_yh - _y))


@dataclass(frozen=True, slots=True)
class FontFamily:
    """
    - 100 - Thin
    - 200 - ExtraLight (UltraLight)
    - 300 - Light
    - 400 - Regular (Normal, Book, Roman)
    - 500 - Medium
    - 600 - SemiBold (DemiBold)
    - 700 - Bold
    - 800 - ExtraBold (UltraBold)
    - 900 - Black (Heavy)
    """
    Regular: GenericFont
    Thin: Optional[GenericFont] = None
    ExtraLight: Optional[GenericFont] = None
    Light: Optional[GenericFont] = None
    Medium: Optional[GenericFont] = None
    SemiBold: Optional[GenericFont] = None
    Bold: Optional[GenericFont] = None
    ExtraBold: Optional[GenericFont] = None
    Black: Optional[GenericFont] = None

    def _tuple(self) -> Tuple[GenericFont | None, ...]:
        return (
            self.Thin, self.ExtraLight, self.Light, self.Regular,
            self.Medium, self.SemiBold, self.Bold, self.ExtraBold, self.Black
        )

    def _select(self, _i: int) -> GenericFont:
        return (((self.Regular, ) + self._tuple())[_i]) or self.Regular

    def find_relative_font(
        self, delta: int = 0, font: Optional[GenericFont] = None
    ) -> GenericFont:
        ext = tuple(x for x in self._tuple() if x is not None)
        _font = self.Regular if font is None else font
        found = ext.index(_font) + delta
        return ext[max(0, min(len(ext), found))]

    def __getitem__(self, _i: int) -> GenericFont:
        if 0 <= _i < 10:
            return self._select(_i)
        if 100 <= _i <= 900:
            return self._select(round(_i / 100))
        raise IndexError("font index only supports [0..9] and [100..900]")
    
    def __add__(self, other: int) -> GenericFont:
        return self.find_relative_font(other)


@dataclass
class TextDrawState:
    land: Rect
    avoid: Sequence[Rect]
    fonts: Sequence[Tuple[FontFamily, Optional[FontFamily]]]
    lineheight: int
    curpos: Tuple[float, float] = (0., 0.)
    spacing: int = 4
    sgr: SGRState = field(default_factory=SGRState)
    palette: Type[ColorTable] = ColorTable

    def copy(self) -> "TextDrawState":
        return deepcopy(self)

    @property
    def current_font(self) -> GenericFont:
        return (
            self.fonts[self.sgr.font][self.sgr.italic]
            or self.fonts[self.sgr.font][0]
        ) + self.sgr.power

    @property
    def current_color(self) -> RGBA:
        if self.sgr.fg_rgb is not None:
            return RGBA(*self.sgr.fg_rgb)
        return self.palette(self.sgr.fg).rgba


class RichCanvas:
    def __init__(self, canvas: Image) -> None:
        self._canvas: Image = canvas
        self._draw: ImageDraw = Draw(canvas)

    @property
    def canvas(self) -> Image:
        return self._canvas

    @property
    def draw(self) -> ImageDraw:
        return self._draw

    @canvas.setter
    def canvas(self, c: Image) -> None:
        self._canvas = c
        self._draw = Draw(c)

    def rectangle(
        self, r: Rect, fill: Optional[SupportsRGBA] = None,
        edge: Optional[SupportsRGBA] = None, width: float = 0.
    ) -> None:
        if fill is not None:
            fill = fill.rgba
        if edge is not None:
            edge = edge.rgba
        self.draw.rectangle(r, fill, edge, width)

    def _draw_text(
        self,
        state: TextDrawState,
        textq: deque[Tuple[str, int]],
        breadcrumb: int,
        nstyle: int
    ) -> None:
        n = max(1, len(textq) - 1 - nstyle)
        for wd, wi in textq:
            if wd[0] == "\x1b":
                params = [int(opc) for opc in wd[2:-1].split(";")]
                state.sgr.set_state(*params)
                continue
            if wi == 0:
                raise RuntimeError
            cx, cy = state.curpos
            self.draw.text(
                (cx + state.land.x, cy + state.land.y),
                wd, state.current_color,
                state.current_font, "la",
            )
            state.curpos = cx + wi + breadcrumb / n, cy
        textq.clear()

    def _text(
        self, st: TextDrawState, text: str,
        *,
        justify: bool = True
    ) -> None:
        sp = combine(*split(text))
        rq: deque[Tuple[str, int]] = deque()
        # render queue
        rw, rh = 0, 0
        # current line width and height
        ws, wsw = 0, 0
        # whitespaces and width for stripping white tail
        lwr: bool = True
        # leading whitespace register
        sty: int = 0
        # style count
        for wd in sp:
            if wd[0] == "\x1b":
                sty += 1
                rq.append((wd, 0))
                continue
            *_, w, h = self.draw.textbbox(
                (0, 0), wd, st.current_font, "la"
            )
            rh = max(h, rh, st.lineheight)
            if rw + w > st.land.w:
                crb = (st.land.w - rw + wsw) if justify else 0

                # strip whitespaces ending
                for _ in range(ws):
                    rq.pop()
                self._draw_text(st, rq, crb, sty)

                sty = 0
                # enter new line
                _, cy = st.curpos
                st.curpos = 0, cy + rh + st.spacing
                rw, rh = 0, 0
            if not rq and not wd.strip() and not lwr:
                # skip non-leading whitespaces
                continue
            rw += w
            rq.append((wd, w))
            if wd.strip():
                lwr = False
                ws, wsw = 0, 0
            else:
                ws += 1
                wsw += w
        self._draw_text(st, rq, 0, 0)
        _, cy = st.curpos
        st.curpos = 0, cy + max(rh, st.lineheight) + st.spacing

    def text(
        self, state: TextDrawState, text: str,
        *,
        justify: bool = True
    ) -> None:
        for lns in text.splitlines():
            self._text(state, lns, justify=justify)