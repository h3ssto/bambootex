import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from enum import StrEnum
from os import linesep
from typing import Any, Callable, Protocol

import pandas as pd


class Font(StrEnum):
    rm = r"\textrm"
    sf = r"\textsf"
    tt = r"\texttt"
    bf = r"\textbf"
    it = r"\textit"


class Size(StrEnum):
    tiny        = r"\tiny"
    scriptsize  = r"\scriptsize"
    footnotesize= r"\footnotesize"
    small       = r"\small"
    normalsize  = r"\normalsize"
    large       = r"\large"
    Large       = r"\Large"
    LARGE       = r"\LARGE"
    huge        = r"\huge"
    Huge        = r"\Huge"


class Highlighter(Protocol):
    def __call__(self, series: pd.Series) -> dict[Any, str]: ...


@dataclass
class SimpleHighlighter:
    color: str

    def __call__(self, series: pd.Series) -> dict[Any, str]:
        return {idx: self.color for idx in series.index}


@dataclass
class GradientHighlighter:
    color_min: str
    color_max: str

    def __call__(self, series: pd.Series) -> dict[Any, str]:
        mn, mx = series.min(), series.max()

        def pct(v):
            return 50 if mx == mn else int(round((v - mn) / (mx - mn) * 100))

        return {
            idx: f"{self.color_max}!{pct(v)}!{self.color_min}"
            for idx, v in series.items()
        }


_LATEX_ESCAPE = str.maketrans({
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
})


def _latex_escape(s: str) -> str:
    return s.translate(_LATEX_ESCAPE)


@dataclass
class NumberFormatter:
    decimal_places: int = 2
    unit: str | None = None
    nan: str | None = None

    def __call__(self, value: float) -> str:
        if self.nan is not None and pd.isna(value):
            return self.nan
        formatted = format(value, f".{self.decimal_places}f")
        return f"{formatted} {self.unit}" if self.unit else formatted


def _as_formatter(fmt: str | Callable) -> Callable:
    if callable(fmt):
        return fmt
    return lambda x: format(x, fmt)


@dataclass
class TextFormatter:
    font: str | list[str] | None = None
    size: str | None = None
    align: str | None = None
    prefix: str = ""
    suffix: str = ""

    def __call__(self, value: str) -> str:
        fonts = self.font if isinstance(self.font, list) else ([self.font] if self.font else [])
        content = f"{self.prefix}{value}{self.suffix}"
        for f in reversed(fonts):
            content = rf"{f}{{{content}}}"
        if self.size:
            content = rf"{self.size}{{{content}}}"
        return content


@dataclass
class Cell:
    text: str
    hspan: int = 1
    vspan: int = 1
    align: str = "c"
    font: str | None = None

    def to_latex(self) -> str:
        if not self.text:
            return ""
        content = rf"{self.font}{{{self.text}}}" if self.font else self.text
        if self.hspan == 1 and self.vspan == 1:
            return rf"\SetCell{{{self.align}}}{{{content}}}"
        if self.vspan == 1:
            return rf"\SetCell[c={self.hspan}]{{{self.align}}}{{{content}}}"
        return rf"\SetCell[c={self.hspan}, r={self.vspan}]{{{self.align}}}{{{content}}}"


class Table:

    def __init__(
        self,
        df: pd.DataFrame,
        columns: list[str],
        column_formatters: dict[str, str | Callable] | None = None,
        headers: list[list[Cell]] | None = None,
        packages: list[str] | None = None,
        number_format: str | NumberFormatter = ".2f",
        vlines: list[int] | None = None,
        hlines: list[int] | None = None,
        default_size: str | None = None,
    ):
        self.df = df.copy()

        for col in columns:
            if isinstance(col, str) and col not in df:
                raise ValueError(f"Column name {col!r} not in data frame.")

        self.columns = columns
        self.column_formatters = column_formatters
        self.headers = headers
        self.packages = packages or []
        self.number_format = number_format
        self.vlines = vlines or []
        self.hlines = hlines or []
        self.default_size = default_size
        self._highlights: list[tuple[str | list[str], Highlighter, tuple[Callable, ...]]] = []

    def sort_by(
        self, key: str | list[str] | Callable, reverse: bool = False
    ) -> "Table":
        if callable(key):
            keys = self.df.apply(key, axis=1)
            self.df = self.df.iloc[keys.argsort()[::-1] if reverse else keys.argsort()]
        else:
            self.df = self.df.sort_values(key, ascending=not reverse)
        return self

    def highlight(
        self, column: str | list[str], highlighter: Highlighter, *fns: Callable
    ) -> "Table":
        self._highlights.append((column, highlighter, fns))
        return self

    def _colspec(self) -> str:
        specs = []
        for col in self.columns:
            formatter = self.column_formatters.get(col) if self.column_formatters else None
            if isinstance(formatter, TextFormatter) and formatter.align:
                specs.append(formatter.align)
            elif pd.api.types.is_float_dtype(self.df[col]) or pd.api.types.is_integer_dtype(self.df[col]):
                specs.append("r")
            else:
                specs.append("l")
        return " ".join(specs)

    def _build_preamble(self) -> str:
        pkgs = r"\usepackage{xcolor}\usepackage{amssymb}\usepackage{tabularray}\usepackage{babel}\usepackage{siunitx}\UseTblrLibrary{siunitx}\usepackage{lmodern}\renewcommand{\familydefault}{\sfdefault}"
        for pkg in self.packages:
            pkgs += rf"\usepackage{{{pkg}}}"
        size_cmd = rf"\AtBeginDocument{{{self.default_size}}}" if self.default_size else ""
        n = len(self.headers) if self.headers else 0
        vline_opts = "".join(rf", vline{{{i + 1}}} = {{solid}}" for i in self.vlines)
        hline_opts = "".join(rf", hline{{{i + 1}}} = {{solid}}" for i in self.hlines)
        return rf"\documentclass{{standalone}}{pkgs}\renewcommand*\ttdefault{{lmtt}}\begin{{document}}{size_cmd}\begin{{tblr}}{{colspec = {{{self._colspec()}}}, row{{1-{n}}} = {{font = \bfseries, halign = c}}, hline{{1}} = {{1pt}}, hline{{{n + 1}}} = {{0.5pt}}, hline{{Z}} = {{1pt}}{vline_opts}{hline_opts}}}"

    def _build_headers(self) -> list[str]:
        if not self.headers:
            return []

        lines = []
        for header in self.headers:
            cells = []
            for cell in header:
                cells.append(cell.to_latex() or "{}")
                cells.extend("{}" for _ in range(cell.hspan - 1))
            lines.append(f"&{linesep}".join(cells) + r"\\")

        return lines

    def _compute_highlights(self, df: pd.DataFrame) -> dict[tuple[Any, str], str]:
        highlights: dict[tuple[Any, str], str] = {}
        for col_or_cols, highlighter, fns in self._highlights:
            if isinstance(col_or_cols, list):
                predicate = fns[0] if fns else lambda *_: True
                for idx, row in df[col_or_cols].iterrows():
                    matching = pd.Series(
                        {col: row[col] for col in col_or_cols if predicate(row[col], row)}
                    )
                    for col, color in highlighter(matching).items():
                        highlights[(idx, col)] = color
            else:
                series = df[col_or_cols]
                if fns:
                    mask = pd.Series(True, index=series.index)
                    for fn in fns:
                        result = fn(series)
                        mask &= result if isinstance(result, pd.Series) else series == result
                    series = series[mask]
                for idx, color in highlighter(series).items():
                    highlights[(idx, col_or_cols)] = color
        return highlights

    def _build_content(
        self, df: pd.DataFrame, highlights: dict[tuple[int, str], str]
    ) -> list[str]:
        rows = []
        for idx, row in df.iterrows():
            cells = [
                (
                    rf"\SetCell{{bg={highlights[(idx, col)]}}} {row[col]}"
                    if (idx, col) in highlights
                    else str(row[col])
                )
                for col in self.columns
            ]
            rows.append("&".join(cells) + r"\\")
        return rows

    def to_tex(self, output_path: str):
        df = self.df.copy()
        highlights = self._compute_highlights(df)

        for col in self.columns:
            if pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col]):
                df[col] = df[col].apply(lambda v: _latex_escape(str(v)))

        formatters = {
            col: _as_formatter(self.number_format)
            for col in self.columns
            if pd.api.types.is_float_dtype(df[col])
        }

        if self.column_formatters:
            formatters.update(
                {col: _as_formatter(fmt) for col, fmt in self.column_formatters.items()}
            )

        for col, fmt in formatters.items():
            df[col] = df[col].apply(fmt)

        pre = self._build_preamble()
        post = r"\end{tblr}\end{document}"

        lines = [
            pre,
            *self._build_headers(),
            *self._build_content(df, highlights),
            post,
        ]

        with open(output_path, "w+") as fp:
            fp.writelines(line + linesep for line in lines)

    def to_pdf(self, output_path: str):
        with tempfile.TemporaryDirectory() as tmpdir:
            tex_path = os.path.join(tmpdir, "table.tex")
            self.to_tex(tex_path)
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_path],
                cwd=tmpdir,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"pdflatex failed:\n{result.stdout}")
            shutil.copy(os.path.join(tmpdir, "table.pdf"), output_path)
