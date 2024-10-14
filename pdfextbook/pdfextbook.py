#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2024-present Raffaele Mancuso
# SPDX-License-Identifier: MIT

# Extract PDF pages on bookmark boundaries

import subprocess
import tempfile
import os
import readline
import argparse
import re
from pathlib import Path
import numpy as np
import json


def rlinput(prompt, prefill=""):
    # Ask for user input with a pre-filled default value
    readline.set_startup_hook(
        lambda: readline.insert_text(prefill)
    )
    try:
        return input(
            prompt
        )  # or raw_input in Python 2
    finally:
        readline.set_startup_hook()


def ask_for_output(choice):
    # Ask user for output file
    # pos = len(choice) - choice[::-1].index("[")
    # proposal = choice[:pos-2]
    proposal = (
        re.search(r"(.*)\[.*?\]", choice)
        .group(1)
        .strip()
    )
    proposal = (
        proposal[:50]
        .replace(" ", "_")
        .replace("[", "")
        .replace("]", "")
        .replace(".", "_")
        .replace(":", "")
        .replace("-", "_")
    )
    proposal += ".pdf"
    outfp = rlinput("Output file: ", proposal)
    outfp = Path(outfp)
    outfp = outfp.resolve()
    return outfp


def extract_bookmark(args, infp, choice, outfp):
    lead = "\t"
    print(f"{lead}Saving to: `{outfp}`")
    # Actually extract the pages
    # Get page boundaries
    pages = choice.split(" ")[-1][1:-1].split("-")
    start_page, end_page = pages
    #
    # Use pdftk
    if args.extraction_engine == "pdftk":
        print(f"{lead}Using pdftk to extract pages")
        # You can reference page numbers in reverse order
        # by prefixing them with the letter r.
        # For example, page r1 is the last page of the document,
        # r2 is the next-to-last page of the document,
        # and rend is the first page of the document.
        # You can use this prefix in ranges, too,
        # for example r3-r1 is the last three pages of a PDF.
        if end_page == "":
            end_page = "r1"
        cmd = [
            "pdftk",
            str(infp),
            "cat",
            str(start_page) + "-" + str(end_page),
            "output",
            str(outfp),
        ]
        res = subprocess.run(cmd)
    #
    # Use qpdf
    elif args.extraction_engine == "qpdf":
        print(f"{lead}Using qpdf to extract pages")
        # From qpdf documentation:
        # A number preceded by r counts from the end, so r1 is the last page,
        # r2 is the second-to-last page, etc.
        if end_page == "":
            end_page = "r1"
        cmd = [
            "qpdf",
            "--empty",
            "--pages",
            str(infp),
            str(start_page) + "-" + str(end_page),
            "--",
            outfp,
        ]
        res = subprocess.run(cmd)
    #
    # Use pdfjam
    elif args.extraction_engine == "pdfjam":
        print(f"{lead}Using pdfjam to extract pages")
        # In pdfjam, the last page corresponds to the empty string
        if end_page == "":
            end_page = ""
        cmd = [
            "pdfjam",
            str(infp),
            str(start_page) + "-" + str(end_page),
            "-o",
            outfp,
        ]
        res = subprocess.run(cmd)
    #
    else:
        raise Exception("Unsupported extraction engine")
    #
    assert (res.returncode == 0)


# Main

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="pdf_extbook",
        description="Extract PDF pages on bookmark boundaries",
    )
    level_group = parser.add_mutually_exclusive_group()
    level_group.add_argument(
        "-a",
        "--all-levels",
        help="Extract all bookmarks of a given level.",
        nargs=2,
        metavar=("level", "path")
    )
    level_group.add_argument(
        "-m",
        "--max-level",
        help="Max bookmark level the user can choose from (levels start from 1).",
        default=None,
        type=int
    )
    level_group.add_argument(
        "-e",
        "--exact-level",
        help="Exact bookmark level the user can choose from (levels start from 1).",
        default=None,
        type=int
    )
    parser.add_argument(
        "-E",
        "--extraction-engine",
        help="Engine used to extract pages from PDF. Can be pdftk (default), qpdf, pdfjam.",
        default="qpdf",
        type=str,
        choices={"pdftk", "qpdf", "pdfjam"}
    )
    parser.add_argument(
        "-p",
        "--end-page-mode",
        help=("How to find the end page of a bookmark "
              "(PDF bookmarks point to a single page). "
              "If `exact`, bookmark ends when another bookmark "
              "at the same hierarchical level is encountered "
              "(or at the last page), "
              "if `less`, bookmark ends when another bookmark "
              "at the same or at a higher hierarchical level is encountered "
              "(or at the last page if there aren't any)."),
        default="less",
        type=str,
        choices={"exact", "less"}
    )
    parser.add_argument(
        "file",
        help="The PDF file from which to extract bookmarks."
    )
    args = parser.parse_args()

    # Use pdftk to extract bookmarks from PDF
    print("Extracting bookmarks...")
    cmd = ["pdftk", args.file, "dump_data_utf8"]
    bl = subprocess.run(
        cmd, text=True, capture_output=True
    ).stdout.splitlines()
    bl = [x for x in bl if x.startswith("Bookmark")]
    bl2 = "\n".join(bl)

    # Process bookmarks
    tag_title = "BookmarkTitle: "
    tag_level = "BookmarkLevel: "
    tag_page = "BookmarkPageNumber: "

    pat = tag_title + "(.+?)\n" + tag_level + "(.+?)\n" + tag_page + "(.+?)$"

    titles = list()
    levels = list()
    pages = list()
    for m in re.finditer(pat, bl2, re.MULTILINE):
        title = m.group(1)
        level = int(m.group(2))
        page = int(m.group(3))
        titles.append(title)
        levels.append(level)
        pages.append(page)

    assert len(titles) == len(levels)
    assert len(titles) == len(pages)

    # List relevant bookmarks with their start and end page (which we need to find)
    it = enumerate(zip(titles, levels, pages))
    choices = list()
    for i, (title, level, start_page) in it:
        if (
            args.max_level
            and level > args.max_level
        ):
            continue
        if (
            args.exact_level
            and level != args.exact_level
        ):
            continue
        if (
            args.all_levels
            and level != int(args.all_levels[0])
        ):
            continue
        # Get end page
        levels2 = np.asarray(levels[i + 1:])
        pages2 = np.asarray(pages[i + 1:])
        if len(levels2) == 0:
            end_page = ""
        else:
            if args.end_page_mode == "exact":
                cond = np.asarray(levels2 == level).nonzero()
            if args.end_page_mode == "less":
                cond = np.asarray(levels2 <= level).nonzero()
            if len(cond[0]) == 0:
                end_page = ""
            else:
                next_pos = cond[0][0]
                end_page = pages2[next_pos]-1
                if end_page == -1:
                    end_page = ""
        # Append bookmark to list of possible choices
        choices.append(title +
                       " [" +
                       str(start_page) +
                       "-" +
                       str(end_page) +
                       "]"
                       )
    print(json.dumps(choices, indent=4, ensure_ascii=False))
    choices = "\n".join(choices)

    # Ask user which bookmark to extract with fzf
    if (args.all_levels is None):
        with tempfile.NamedTemporaryFile("w") as input_file:
            with tempfile.NamedTemporaryFile("r") as output_file:
                input_file.write(choices)
                input_file.flush()
                os.system(
                    "fzf --reverse "
                    f'< "{input_file.name}" '
                    f'> "{output_file.name}"'
                )
                # Read user choice from file
                choice = output_file.read().strip()
        outfp = ask_for_output(choice)
        extract_bookmark(args, args.file, choice, outfp)

    else:
        print("Extracting all levels")
        choices = choices.splitlines()
        for i, choice in enumerate(choices):
            print(choice)
            outfp = args.all_levels[1] + str(i) + ".pdf"
            extract_bookmark(args, args.file, choice, outfp)


if __name__ == "__main__":
    main()
