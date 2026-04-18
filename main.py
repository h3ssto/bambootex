import pandas as pd
from os import linesep


class Table:

    def __init__(self, df, columns, column_aligns = None, column_formatters = None, headers = None, vlines = None, packages = None):
        self.df = df.copy()
        
        for col in columns:

            if isinstance(col, str):
                if col not in df:
                    raise ValueError(f"Column name {col} not in data frame.")

        self.packages = packages if packages else []
        self.columns = columns
        self.column_aligns = column_aligns
        self.column_formatters = column_formatters
        self.vlines = vlines

        self.headers = headers


    def build(self):

        if self.column_formatters:
            for k, v in self.column_formatters.items():
                self.df[k] = self.df[k].apply(v)

        if self.column_aligns:
            if self.column_aligns == "auto":
                alignments = ["l" if self.df[col].dtype is str else "r" for col in self.columns]
            else:
                alignments = self.column_aligns

        else:
            alignments = ["l" for _ in self.columns]

        vlines = sorted(self.vlines)

        inc = 0

        for v in vlines:

            if v < 0:
                alignments.append("|")
            else:
                alignments.insert(v + inc, "|")
                inc += 1

        alignments = "".join(alignments)

        pre = fr"\documentclass{{standalone}}\usepackage{{makecell}}\usepackage{{tabularray}}\begin{{document}}\begin{{tblr}}{{colspec = {{{alignments}}}}}\hline"

        header_lines = []

        post = r"\end{tblr}\end{document}"

        print(pre)

        if self.headers:
            for header in self.headers:
                line = []
                for entry in header:
                    if isinstance(entry, str):
                        if entry:
                            line.append(fr"\thead{{{entry}}}")
                        else:
                            line.append("")
                    else:  # tuple

                        if len(entry) == 3:
                            hspan, align, entry = entry
                            line.append(fr'\SetCell[c={hspan}]{{{align}}}{{\thead{{{entry}}}}}')
                        else:
                            hspan, vspan, align, entry = entry

                            line.append(fr'\SetCell[c={hspan}, r={vspan}]{{{align}}}{{\thead{{{entry}}}}}')


                header_lines.append(f"&{linesep}".join(line) + r"\\")

        if header_lines:
            header_lines[-1] += r"\hline"
        print(post)

        content = []

        for _, row in self.df.iloc[1:].iterrows():
            line = []
            for col in self.columns:
                line.append(str(row[col]))

            line = "&".join(line) + r"\\"
            content.append(line)


        lines = [pre, *header_lines, *content, post]
        
        lines = [line + linesep for line in lines]

        with open("test.tex", "w+") as fp:
            fp.writelines(lines)



def main():

    df = pd.read_csv("https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv")

    print(df)

    tbl = Table(df, columns = ["species", "sepal_length", "sepal_width"], column_aligns = "auto", column_formatters = dict(species = lambda x: rf"\textsf{{{x}}}", sepal_length = lambda x: f"{x:.2f}"), headers = [[(1, 2, "c", "Species"), (2, "c", "Sepal")], ["", "Length", "Width"]], vlines = [0, 1, -1], packages = ["libertine"])
    

    tbl.build()

    print(df)


if __name__ == '__main__':
    main()
