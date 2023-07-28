from collections import namedtuple
from dataclasses import dataclass
import re
from typing import Optional, Tuple
import warnings


"""
\\x1b [ ... m

0	Reset
1	+Bold               +power
2	+Light              -power
3	+Italic/Oblique     +italic
4	+Underline          +uline
9	+Strike             +strike
10	fon0                font
11–19	fon1-9          font
23	-Italic/Oblique     -italic
24	-Underline          -uline
29	-Strike             -strike
30–37	+fg             fg
38	+fgx                fg
    38;5;n or 38;2;r;g;b
39	fg0                 fg
53	+Hatline            +hline
55	-Hatline            -hline
64	+Dot                +dot
65	-Dot                -dot
90–97	+xfg            fg
"""


@dataclass
class SGRState:
    power: int = 0
    # 0 for normal, >0 for bolder, <0 for lighter

    italic: bool = False
    # False for normal, True for italic

    uline: int = 0
    # 0 for no line, 1 for underline, 2 for dunderline

    hline: int = 0
    # 0 for no line, -1 for hatline, -2 for dhatline

    strike: bool = False

    font: int = 0
    # can be 0-9

    fg_default: int = 0
    fg: int = 0
    fg_rgb: Optional[Tuple[int, int, int]] = None

    dot: bool = False

    def set_state(self, *opcodes: int) -> None:
        op38, op38_256 = False, False
        op38_24 = 0
        op38_24_tmp = []
        for op in opcodes:
            if op38_256:
                self.fg = op
                op38, op38_256 = False, False
                self.fg_rgb = None
                continue
            elif op38_24:
                op38_24_tmp.append(op)
                op38_24 -= 1
                if op38_24 == 0:
                    self.fg_rgb = tuple(op38_24_tmp)
                    op38, op38_256 = False, False
                continue
            elif op38:
                if op == 5:
                    op38_256 = True
                    continue
                elif op == 2:
                    op38_24 = 3
                    continue
                op38, op38_256 = False, False
                self.fg_rgb = None
            if op == 0:
                self.power = self.uline = self.hline = self.font = 0
                self.italic = self.strike = self.dot = False
                self.fg = self.fg_default
                self.fg_rgb = None
            elif op == 1:
                self.power += 1
            elif op == 2:
                self.power -= 1
            elif op == 3:
                self.italic = True
            elif op == 4:
                self.uline += 1
            elif op == 9:
                self.strike = True
            elif 10 <= op <= 19:
                self.font = op - 10
            elif op == 23:
                self.italic = False
            elif op == 24:
                self.uline -= 1
            elif op == 29:
                self.strike = False
            elif 30 <= op <= 37:
                self.fg = op - 30
                self.fg_rgb = None
            elif op == 38:
                op38 = True
            elif op == 39:
                self.fg = self.fg_default
            elif op == 53:
                self.hline += 1
            elif op == 55:
                self.hline -= 1
            elif op == 64:
                self.dot = True
            elif op == 65:
                self.dot = False
            elif 90 <= op <= 97:
                self.fg = op - 82
                self.fg_rgb = None
            else:
                warnings.warn(f"code {op} not dealt")


CSIBlock = namedtuple("CSIBlock", ("cc", "par", "op", "t"))
CSI_REGEX = re.compile(
    r"(?P<cc>\033\[(?P<par>[\x30-\x3f]*)(?P<op>[\x40-\x7e]))(?P<t>[^\033]*)"
)


def csi_split(text: str) -> Tuple[CSIBlock, ...]:
    return tuple(CSIBlock(*found) for found in CSI_REGEX.findall(text))


def findcsiend(text: str) -> int:
    return next(
        (i + 3 for i, c in enumerate(text[2:]) if ord(c) in range(0x40, 0x7f)),
        len(text)
    )