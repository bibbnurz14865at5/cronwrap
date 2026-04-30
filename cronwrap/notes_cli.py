"""CLI for managing per-job notes."""
from __future__ import annotations

import argparse
import json
import sys

from cronwrap.job_notes import JobNotes, NoteEntry, NotesError

_DEFAULT_DIR = ".cronwrap/notes"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cronwrap-notes", description="Manage job notes")
    p.add_argument("--notes-dir", default=_DEFAULT_DIR, metavar="DIR")
    sub = p.add_subparsers(dest="command")

    add_p = sub.add_parser("add", help="Add a note to a job")
    add_p.add_argument("job_name")
    add_p.add_argument("text")
    add_p.add_argument("--author", default=None)

    list_p = sub.add_parser("list", help="List notes for a job")
    list_p.add_argument("job_name")

    clear_p = sub.add_parser("clear", help="Clear all notes for a job")
    clear_p.add_argument("job_name")

    rm_p = sub.add_parser("remove", help="Remove a note by index")
    rm_p.add_argument("job_name")
    rm_p.add_argument("index", type=int)

    return p


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 1

    store = JobNotes(args.notes_dir)

    if args.command == "add":
        entry = NoteEntry(job_name=args.job_name, text=args.text, author=args.author)
        store.add(entry)
        print(f"Note added to '{args.job_name}'.")
        return 0

    if args.command == "list":
        notes = store.list_notes(args.job_name)
        if not notes:
            print(f"No notes for '{args.job_name}'.")
        for i, n in enumerate(notes):
            author_str = f" [{n.author}]" if n.author else ""
            print(f"[{i}] {n.timestamp}{author_str}: {n.text}")
        return 0

    if args.command == "clear":
        count = store.clear(args.job_name)
        print(f"Cleared {count} note(s) for '{args.job_name}'.")
        return 0

    if args.command == "remove":
        try:
            removed = store.remove_by_index(args.job_name, args.index)
            print(f"Removed note [{args.index}]: {removed.text}")
            return 0
        except NotesError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
