#!/usr/bin/env python3
"""Turn transcribe output into caption pages for a composition.

Reads one or more word-timing JSON files (from `hyperframes transcribe`), offsets each
by the time its clip starts in the video, groups words into short pages and prints a
JavaScript array you paste into the composition's CAPTIONS constant.

Whisper sometimes changes case or punctuation ("your schedule," for "Your schedule").
Pass the original lines with --text, in clip order, to keep the timings but use your
words. A line is only swapped in when its word count matches the transcript.

Example:
  captions.py assets/vo/l1.json@0.2 assets/vo/l2.json@5.25 --max-words 5 \
    --text "First line as written." --text "Second line as written."
"""

from __future__ import annotations

import argparse
import json
import sys


def load_words(spec: str) -> list[tuple[str, float, float]]:
    path, _, offset = spec.partition("@")
    data = json.load(open(path))
    words = data if isinstance(data, list) else data.get("words", [])
    off = float(offset or 0)
    return [(w["text"].strip(), round(w["start"] + off, 2), round(w["end"] + off, 2)) for w in words]


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("clips", nargs="+", help="file.json@start_seconds")
    p.add_argument("--max-words", type=int, default=5)
    p.add_argument("--text", action="append", default=[], help="original script line, once per clip in order")
    args = p.parse_args()

    pages = []
    for n, spec in enumerate(args.clips):
        words = load_words(spec)
        if n < len(args.text):
            script = args.text[n].split()
            if len(script) == len(words):
                words = [(script[i], s, e) for i, (_, s, e) in enumerate(words)]
            else:
                print(f"// note: clip {n + 1} has {len(words)} words but --text has {len(script)}; kept the transcript",
                      file=sys.stderr)
        page: list[tuple[str, float, float]] = []
        for w in words:
            page.append(w)
            ends_sentence = w[0][-1:] in ".?!,"
            if len(page) >= args.max_words or ends_sentence:
                pages.append(page)
                page = []
        if page:
            pages.append(page)

    print("const CAPTIONS = [")
    for page in pages:
        words = ", ".join(f'["{t}", {s}]' for t, s, _ in page)
        print(f"  {{ end: {page[-1][2]}, words: [{words}] }},")
    print("];")


if __name__ == "__main__":
    main()
