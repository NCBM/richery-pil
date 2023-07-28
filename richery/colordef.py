from itertools import product, starmap
from typing import Optional, Protocol, Sequence, Tuple, NamedTuple


class SupportsRGBA(Protocol):
    @property
    def rgba(self) -> "RGBA":
        ...


class RGBA(NamedTuple):
    r: int = 0
    g: int = 0
    b: int = 0
    a: int = 255

    @property
    def rgba(self) -> "RGBA":
        return self
    
    @property
    def hex(self) -> str:
        return f"#{self.a:02x}{self.r:02x}{self.g:02x}{self.b:02x}"


class RGB(NamedTuple):
    r: int = 0
    g: int = 0
    b: int = 0

    @property
    def rgba(self) -> RGBA:
        return RGBA(self.r, self.g, self.b)


_P = product((0, 128), repeat=3)
_Q = product((0, 255), repeat=3)
_R = product((0, 0x5f, 0x87, 0xaf, 0xd7, 0xff), repeat=3)
(
    BLACK, D_BLUE, D_GREEN, D_CYAN, D_RED, D_MAGENTA, D_YELLOW, GRAY
) = starmap(RGB, _P)
(
    _, L_BLUE, L_GREEN, L_CYAN, L_RED, L_MAGENTA, L_YELLOW, WHITE
) = starmap(RGB, _Q)
BLUE, GREEN, CYAN, RED, MAGENTA, YELLOW = (
    L_BLUE, L_GREEN, L_CYAN, L_RED, L_MAGENTA, L_YELLOW
)
L_GRAY = RGB(170, 170, 170)
D_GRAY = RGB(85, 85, 85)
LIGHTGRAY = RGB(192, 192, 192)

COLOR16_DEFAULT: Tuple[SupportsRGBA, ...] = (
    BLACK, D_RED, D_GREEN, D_YELLOW, D_BLUE, D_MAGENTA, D_CYAN, LIGHTGRAY,
    GRAY, L_RED, L_GREEN, L_YELLOW, L_BLUE, L_MAGENTA, L_CYAN, WHITE
)
# Generic 16 color palette
# Including BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, LIGHTGRAY
#   and their lighter version

COLOR16_COLORFUL: Tuple[SupportsRGBA, ...] = (
    BLACK, RGB(157, 157, 157), WHITE, RGB(190, 38, 51),
    RGB(224, 111, 139), RGB(73, 60, 43), RGB(164, 100, 34), RGB(235, 137, 49),
    RGB(247, 226, 107), RGB(47, 72, 78), RGB(68, 137, 26), RGB(163, 206, 39),
    RGB(27, 38, 50), RGB(0, 87, 132), RGB(49, 162, 242), RGB(178, 220, 239)
)
# Another 16 color palette from http://androidarts.com/palette/16pal.htm
# Including VOID(BLACK) GRAY WHITE RED MEAT DARKBROWN BROWN ORANGE
#   YELLOW DARKGREEN GREEN SLIMEGREEN NIGHTBLUE SEABLUE SKYBLUE CLOUDBLUE

COLOR256_DEFAULT: Tuple[SupportsRGBA, ...] = (
    COLOR16_DEFAULT + tuple(starmap(RGB, _R))
    + tuple(RGB(x, x, x) for x in range(8, 0xef, 10))
)
# Standard 256 color palette


class ColorTable:
    _real: int
    _palette: Tuple[SupportsRGBA]
    _default: Sequence[SupportsRGBA] = COLOR256_DEFAULT

    def __init__(
        self, color: int, *, palette: Optional[Sequence[SupportsRGBA]] = None
    ) -> None:
        self._real = color
        self._palette = tuple(palette or self._default)

    @property
    def rgba(self) -> RGBA:
        return self._palette[self._real].rgba

    def __eq__(self, __o: "ColorTable") -> bool:
        return (self._real, self._palette) == (__o._real, __o._palette)

    def __hash__(self) -> int:
        return hash((self._real, self._palette))

    def __len__(self) -> int:
        return len(self._palette)