from enum import StrEnum


class Font(StrEnum):
    rm = r"\textrm"
    sf = r"\textsf"
    tt = r"\texttt"
    bf = r"\textbf"
    it = r"\textit"


class Size(StrEnum):
    tiny         = r"\tiny"
    scriptsize   = r"\scriptsize"
    footnotesize = r"\footnotesize"
    small        = r"\small"
    normalsize   = r"\normalsize"
    large        = r"\large"
    Large        = r"\Large"
    LARGE        = r"\LARGE"
    huge         = r"\huge"
    Huge         = r"\Huge"
