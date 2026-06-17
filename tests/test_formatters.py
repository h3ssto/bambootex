import pytest
from bambootex import TextFormatter, NumberFormatter, Font, Size


class TestNumberFormatter:
    def test_decimal_places(self):
        fmt = NumberFormatter(decimal_places=3)
        assert fmt(1.23456) == "1.235"

    def test_unit(self):
        fmt = NumberFormatter(decimal_places=2, unit="s")
        assert fmt(1.5) == "1.50 s"

    def test_nan_substitution(self):
        import math
        fmt = NumberFormatter(nan="--")
        assert fmt(float("nan")) == "--"

    def test_nan_none_by_default(self):
        fmt = NumberFormatter()
        assert fmt(float("nan")) == "nan"

    def test_nan_with_pandas_na(self):
        import pandas as pd
        fmt = NumberFormatter(nan="--")
        assert fmt(pd.NA) == "--"


class TestTextFormatter:
    def test_font(self):
        fmt = TextFormatter(font=Font.sf)
        assert fmt("hello") == r"\textsf{hello}"

    def test_size(self):
        fmt = TextFormatter(size=Size.small)
        assert fmt("hello") == r"\small{hello}"

    def test_font_and_size(self):
        fmt = TextFormatter(font=Font.sf, size=Size.small)
        assert fmt("hello") == r"\small{\textsf{hello}}"

    def test_font_list(self):
        fmt = TextFormatter(font=[Font.bf, Font.sf])
        assert fmt("hello") == r"\textbf{\textsf{hello}}"

    def test_prefix_suffix(self):
        fmt = TextFormatter(prefix="(", suffix=")")
        assert fmt("hello") == "(hello)"

    def test_prefix_suffix_with_font(self):
        fmt = TextFormatter(font=Font.sf, prefix="(", suffix=")")
        assert fmt("hello") == r"\textsf{(hello)}"

    def test_no_args(self):
        fmt = TextFormatter()
        assert fmt("hello") == "hello"
