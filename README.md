# spockdoc

> Works with python3.2, docopt 0.6.1, sh 1.09, pandoc 1.12.3.3
> **Note: This is alpha software**

spockdoc is a python utility to bridge the gap between StackEdit, pandoc and
"perfect" printable PDF documentation. It is built around my own workflow, and
probably not appropriate for all needs.

While StackEdit and pandoc do 99.9% of the job, there are some subtle issues
with my particular workflow:

- By default, pandoc uses hyperref for internal crossreferences. This works well
when using the PDF on a computer, but when printed it means there is no numbered
reference to the specific section / image or what else the reference might
point to. So I use pandoc to convert from markdown to LaTeX, substitute
\hyperref with \autoref, and use pdflatex to convert the LaTeX file to a PDF.
- When writing on StackEdit I need to use online images. But when I use pandoc
to convert from markdown to LaTex and pdflatex to convert from LaTeX to PDF,
the image is not downloaded. So while the StackEdit version needs a hyperlink,
the LaTeX version needs a link to a local file.

What spockdoc does:

- checks out a specified branch (optionally commit) in a local git repository
- reads a config file (default: /path/to/repo/doc/spockdoc.conf) to determine
pre- and postprocessing rules, pandoc arguments and names of markdown files to
include
- builds printable PDF documentation by:
    1. Preprocessing the included markdown files with preprocessing rules
    2. Using pandoc on the preprocessed files to generate a LaTeX file
    3. Postprocessing the LaTeX file with postprocessing rules
    4. Generating the PDF with pdflatex

See sample-spockdoc.conf for a sample config file
