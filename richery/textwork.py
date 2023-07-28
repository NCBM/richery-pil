import unicodedata
from dataclasses import dataclass
from typing import List

from richery.ansitool import findcsiend


def iseaw(c: str) -> bool:
    eaw = unicodedata.east_asian_width(c)
    return eaw in ('F', 'W', 'A')


def findword(s: str) -> int:
    return next(
        (i for i, c in enumerate(s) if iseaw(c) or c.isspace() or c == "\x1b"),
        len(s)
    )


@dataclass
class PunctuationRule:
    left_bind: str
    right_bind: str
    both_bind: str

    def islb(self, c: str) -> bool:
        return c in self.left_bind or c in self.both_bind

    def isrb(self, c: str) -> bool:
        return c in self.right_bind or c in self.both_bind


WesternPuncRule = PunctuationRule(
    ",.:;?!>)]}~%",
    "<([{$#@",
    "-_+=&^*/|\\"
)

CJKPuncRule = PunctuationRule(
    "。，、；：？！”）｠》」』】〕〗〙〛〞·-－～",
    "“（｟《「『【〔〖〘〚〝",
    "—…／｜"
)

P_RULES = [WesternPuncRule, CJKPuncRule]


def _islb(c: str):
    return any(r.islb(c) for r in P_RULES)


def _isrb(c: str):
    return any(r.isrb(c) for r in P_RULES)


def _ispunc(c: str):
    return any((c in (r.left_bind + r.right_bind + r.both_bind)) for r in P_RULES)


def split(t: str) -> List[str]:
    res = []
    base, length = 0, len(t)
    while base != length:
        w = findcsiend(t[base:]) if t[base] == "\x1b" else findword(t[base:])
        if w == 0:
            res.append(t[base])
            w = 1
        else:
            res.append(t[base:base + w])
        base += w
    return res


def combine(*t: str) -> List[str]:
    if not t:
        return []
    res = [t[0]]
    prb, rb = False, (len(t[0]) == 1 and _isrb(t[0]))
    psgr = t[0][0] == "\x1b"
    for wd in t[1:]:
        if wd[0] == "\x1b":
            res.append(wd)
            prb, rb = False, False
            psgr = True
            continue
        if rb and not psgr:
            res[-1] += wd
            prb, rb = True, False
        if len(wd) == 1 and _ispunc(wd):
            rb = _isrb(wd)
            if _islb(wd) and not psgr:
                res[-1] += wd
                prb = True
        if not prb:
            res.append(wd)
        prb = False
        psgr = False
    return res