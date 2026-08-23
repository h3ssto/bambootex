import os
import shutil
import subprocess
import tempfile
from os import linesep
from typing import Any, Callable

import pandas as pd

from .cell import Cell
from .formatters import TextFormatter, NumberFormatter, _as_formatter, _latex_escape
from .highlighters import Highlighter


def _run_lengths(values: list) -> list[int]:
    if not values:
        return []
    runs = []
    count = 1
    for prev, curr in zip(values, values[1:]):
        if curr == prev:
            count += 1
        else:
            runs.append(count)
            count = 1
    runs.append(count)
    return runs


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
        merge_rows: list[str] | None = None,
    ):
        self.df = df.copy()

        for col in columns:
            if isinstance(col, str) and col not in df:
                raise ValueError(f"Column name {col!r} not in data frame.")

        for col in merge_rows or []:
            if col not in columns:
                raise ValueError(f"merge_rows column {col!r} not in columns.")

        self.columns = columns
        self.column_formatters = column_formatters
        self.headers = headers
        self.packages = packages or []
        self.number_format = number_format
        self.vlines = vlines or []
        self.hlines = hlines or []
        self.default_size = default_size
        self.merge_rows = merge_rows or []
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
        pkgs = r"\usepackage{xcolor}\usepackage{amssymb}\usepackage{tabularray}\SetTblrInner{leftsep = 4pt,rightsep = 2pt}\usepackage{babel}\usepackage{siunitx}\UseTblrLibrary{siunitx}\usepackage{lmodern}\renewcommand{\familydefault}{\sfdefault}"
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
        column_cells: dict[str, list[str]] = {}
        for col in self.columns:
            cells = []
            skip = 0
            for i, val in enumerate(df[col].tolist()):
                if skip > 0:
                    skip -= 1
                    cells.append("{}")
                    continue
                if isinstance(val, Cell):
                    cells.append(val.to_latex() or "{}")
                    skip = val.vspan - 1
                else:
                    idx = df.index[i]
                    if (idx, col) in highlights:
                        cells.append(rf"\SetCell{{bg={highlights[(idx, col)]}}} {val}")
                    else:
                        cells.append(str(val))
            column_cells[col] = cells

        return [
            "&".join(column_cells[col][i] for col in self.columns) + r"\\"
            for i in range(len(df))
        ]

    def _apply_merge_rows(
        self,
        df: pd.DataFrame,
        merge_runs: dict[str, list[int]],
        highlights: dict[tuple[Any, str], str],
    ) -> None:
        for col, runs in merge_runs.items():
            values = df[col].tolist()
            merged = []
            pos = 0
            for length in runs:
                head_idx = df.index[pos]
                bg = highlights.get((head_idx, col))
                merged.append(Cell(str(values[pos]), vspan=length, bg=bg))
                merged.extend(values[pos + 1 : pos + length])
                pos += length
            df[col] = merged

    def to_tex(self, output_path: str):
        df = self.df.copy()
        highlights = self._compute_highlights(df)
        merge_runs = {col: _run_lengths(df[col].tolist()) for col in self.merge_rows}

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

        if merge_runs:
            self._apply_merge_rows(df, merge_runs, highlights)

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
