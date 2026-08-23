import tempfile
import pandas as pd
import pytest
from bambootex import Table, Cell, TextFormatter, NumberFormatter, SimpleHighlighter, Font


def make_table(df, columns, **kwargs):
    t = Table(df, columns, **kwargs)
    with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as f:
        path = f.name
    t.to_tex(path)
    return open(path).read()


class TestColspec:
    def test_string_col_is_left(self):
        df = pd.DataFrame({"name": ["a"]})
        content = make_table(df, ["name"])
        assert "colspec = {l}" in content

    def test_float_col_is_right(self):
        df = pd.DataFrame({"val": [1.0]})
        content = make_table(df, ["val"])
        assert "colspec = {r}" in content

    def test_text_formatter_align_overrides(self):
        df = pd.DataFrame({"name": ["a"]})
        content = make_table(df, ["name"], column_formatters={
            "name": TextFormatter(align="c")
        })
        assert "colspec = {c}" in content

    def test_mixed_cols(self):
        df = pd.DataFrame({"name": ["a"], "val": [1.0]})
        content = make_table(df, ["name", "val"])
        assert "colspec = {l r}" in content


class TestHeaders:
    def test_hspan_generates_placeholders(self):
        df = pd.DataFrame({"a": [1.0], "b": [2.0], "c": [3.0]})
        content = make_table(df, ["a", "b", "c"], headers=[
            [Cell("Group", hspan=3)],
        ])
        # hspan=3 produces \SetCell[c=3] + 2 empty {} placeholders joined by &\n
        assert content.count("{}") == 2

    def test_empty_cell_becomes_placeholder(self):
        df = pd.DataFrame({"a": [1.0], "b": [2.0]})
        content = make_table(df, ["a", "b"], headers=[
            [Cell("A", vspan=2), Cell("B")],
            [Cell(""), Cell("b")],
        ])
        assert "{}" in content


class TestVlines:
    def test_vline_after_col_1(self):
        df = pd.DataFrame({"a": ["x"], "b": [1.0]})
        content = make_table(df, ["a", "b"], vlines=[1])
        assert "vline{2} = {solid}" in content

    def test_multiple_vlines(self):
        df = pd.DataFrame({"a": ["x"], "b": [1.0], "c": [2.0]})
        content = make_table(df, ["a", "b", "c"], vlines=[1, 2])
        assert "vline{2} = {solid}" in content
        assert "vline{3} = {solid}" in content


class TestHlines:
    def test_hline_after_row_2(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0]})
        content = make_table(df, ["a"], hlines=[2])
        assert "hline{3} = {solid}" in content


class TestHighlight:
    def test_single_col_highlight(self):
        df = pd.DataFrame({"val": [1.0, 2.0, 3.0]})
        t = Table(df, ["val"])
        t.highlight("val", SimpleHighlighter("red"), lambda s: s == s.max())
        with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as f:
            path = f.name
        t.to_tex(path)
        content = open(path).read()
        assert r"\SetCell{bg=red}" in content

    def test_multi_col_highlight_min(self):
        df = pd.DataFrame({"a": [1.0, 3.0], "b": [2.0, 1.0]})
        t = Table(df, ["a", "b"])
        t.highlight(["a", "b"], SimpleHighlighter("green"), lambda v, row: v == row.min())
        with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as f:
            path = f.name
        t.to_tex(path)
        content = open(path).read()
        # row 0: a=1.0 is min; row 1: b=1.0 is min — both should be highlighted
        assert content.count(r"\SetCell{bg=green}") == 2


class TestMergeRows:
    def test_merges_consecutive_equal_values(self):
        df = pd.DataFrame({
            "group": ["a", "a", "b"],
            "val": [1.0, 2.0, 3.0],
        })
        content = make_table(df, ["group", "val"], merge_rows=["group"])
        assert r"\SetCell[c=1, r=2]{c}{a}" in content
        assert "{}" in content
        assert r"\SetCell[c=1, r=2]{c}{b}" not in content

    def test_no_merge_for_singleton_run(self):
        df = pd.DataFrame({"group": ["a", "b"], "val": [1.0, 2.0]})
        content = make_table(df, ["group", "val"], merge_rows=["group"])
        assert "r=" not in content

    def test_rejects_unknown_merge_rows_column(self):
        df = pd.DataFrame({"group": ["a"], "val": [1.0]})
        with pytest.raises(ValueError):
            Table(df, ["val"], merge_rows=["group"])

    def test_merge_combines_with_highlight(self):
        df = pd.DataFrame({
            "group": ["a", "a"],
            "val": [1.0, 2.0],
        })
        t = Table(df, ["group", "val"], merge_rows=["group"])
        t.highlight("group", SimpleHighlighter("yellow"), lambda s: s == "a")
        with tempfile.NamedTemporaryFile(suffix=".tex", delete=False) as f:
            path = f.name
        t.to_tex(path)
        content = open(path).read()
        assert "bg=yellow" in content
        assert "r=2" in content
