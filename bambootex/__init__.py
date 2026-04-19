import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from os import linesep
from typing import Any, Callable, Protocol

import pandas as pd


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


def _as_formatter(fmt: str | Callable) -> Callable:
    if callable(fmt):
        return fmt
    return lambda x: format(x, fmt)


@dataclass
class TextFormatter:
    font: str | None = None
    size: str | None = None

    def __call__(self, value: str) -> str:
        prefix = (self.size or "") + (self.font or "")
        return rf"{prefix}{{{value}}}" if prefix else str(value)


@dataclass
class Cell:
    text: str
    hspan: int = 1
    vspan: int = 1
    align: str = "c"

    def to_latex(self) -> str:
        if not self.text:
            return ""
        if self.hspan == 1 and self.vspan == 1:
            return rf"\SetCell{{{self.align}}}{{{self.text}}}"
        if self.vspan == 1:
            return rf"\SetCell[c={self.hspan}]{{{self.align}}}{{{self.text}}}"
        return (
            rf"\SetCell[c={self.hspan}, r={self.vspan}]{{{self.align}}}{{{self.text}}}"
        )


class Table:

    def __init__(
        self,
        df: pd.DataFrame,
        columns: list[str],
        column_formatters: dict[str, str | Callable] | None = None,
        headers: list[list[Cell]] | None = None,
        packages: list[str] | None = None,
        number_format: str = ".2f",
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
        self._highlights: list[tuple[str, Highlighter, tuple[Callable, ...]]] = []

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
        self, column: str, highlighter: Highlighter, *fns: Callable
    ) -> "Table":
        self._highlights.append((column, highlighter, fns))
        return self

    def _build_preamble(self) -> str:
        pkgs = r"\usepackage{xcolor}\usepackage{tabularray}\usepackage{babel}\usepackage{siunitx}\UseTblrLibrary{siunitx}"
        for pkg in self.packages:
            pkgs += rf"\usepackage{{{pkg}}}"
        n = len(self.headers) if self.headers else 0
        return rf"\documentclass{{standalone}}{pkgs}\begin{{document}}\begin{{tblr}}{{colspec = {{l S[table-format=3.2] S[table-format=2.1]}}, row{{1-{n}}} = {{font = \bfseries, halign = c}}, hline{{1}} = {{1pt}}, hline{{{n + 1}}} = {{0.5pt}}, hline{{Z}} = {{1pt}}}}"

    def _build_headers(self) -> list[str]:
        if not self.headers:
            return []

        lines = []
        for header in self.headers:
            cells = [cell.to_latex() or "{}" for cell in header]
            lines.append(f"&{linesep}".join(cells) + r"\\")

        return lines

    def _compute_highlights(self, df: pd.DataFrame) -> dict[tuple[Any, str], str]:
        highlights: dict[tuple[Any, str], str] = {}
        for col, highlighter, fns in self._highlights:
            series = df[col]
            if fns:
                mask = pd.Series(True, index=series.index)
                for fn in fns:
                    result = fn(series)
                    mask &= result if isinstance(result, pd.Series) else series == result
                series = series[mask]
            for idx, color in highlighter(series).items():
                highlights[(idx, col)] = color
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
