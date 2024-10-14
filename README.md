# pdfextbook

Extract pages from PDF files on bookmark boundaries.

PDF bookmarks point to a single page, but all the pages starting from the one pointed to by the bookmark until the one pointed to by the next bookmark at the same hierarchical level (excluded) will be extracted.

Therefore this tool is useful to extract chapters or sections from books or articles.

It is more powerful than the "Extract Bookmarked Pages" tool of Adobe Acrobat (and it's also free).

You will need the following software present in your path:

- [pdftk](https://www.pdflabs.com/tools/pdftk-the-pdf-toolkit/) (needed to extract bookmark metadata and to extract pages)
- [fzf](https://github.com/junegunn/fzf) (needed to select which bookmark to extract)
