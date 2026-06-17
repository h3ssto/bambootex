from bambootex import Cell, Font


def test_simple_cell():
    assert Cell("foo").to_latex() == r"\SetCell{c}{foo}"


def test_empty_cell():
    assert Cell("").to_latex() == ""


def test_hspan():
    assert Cell("foo", hspan=3).to_latex() == r"\SetCell[c=3]{c}{foo}"


def test_vspan():
    assert Cell("foo", vspan=2).to_latex() == r"\SetCell[c=1, r=2]{c}{foo}"


def test_hspan_and_vspan():
    assert Cell("foo", hspan=3, vspan=2).to_latex() == r"\SetCell[c=3, r=2]{c}{foo}"


def test_align():
    assert Cell("foo", align="l").to_latex() == r"\SetCell{l}{foo}"


def test_font():
    assert Cell("foo", font=Font.tt).to_latex() == r"\SetCell{c}{\texttt{foo}}"
