#!/usr/bin/env python3
"""Pattern-anchored patch harness for the Horizon OC 'unlock' overlay.

Applies .hocpatch files (find/replace blocks anchored on a unique source
snippet, not line numbers) so the unlock changes can be reapplied after the
upstream Horizon OC / Atmosphere source drifts.

A .hocpatch file looks like:

    FILE: Source/some/relative/path.cpp

    ## short description of this hunk
    <<<<<<< SEARCH
    exact original text (must appear exactly once in the file)
    =======
    replacement text
    >>>>>>> REPLACE

    ## next hunk in the same file
    <<<<<<< SEARCH
    ...
    =======
    ...
    >>>>>>> REPLACE

Each SEARCH block must match the target file exactly once. If it matches
zero times, the harness checks whether the REPLACE text is already present
(idempotent re-run / already applied upstream) and skips instead of failing.
If it matches more than once, or matches zero times and REPLACE isn't
present either, the hunk fails loudly instead of guessing.
"""
import argparse
import pathlib
import sys

SEARCH_MARK = "<<<<<<< SEARCH"
DIVIDER_MARK = "======="
REPLACE_MARK = ">>>>>>> REPLACE"


class PatchBlock:
    def __init__(self, description, search, replace, line_no):
        self.description = description
        self.search = search
        self.replace = replace
        self.line_no = line_no

    def label(self):
        return self.description if self.description else f"line {self.line_no}"


class PatchFile:
    def __init__(self, path, target_file, blocks):
        self.path = path
        self.target_file = target_file
        self.blocks = blocks


def parse_patch_file(path):
    text = path.read_text(encoding="utf-8", newline="")
    lines = text.split("\n")

    target_file = None
    blocks = []
    pending_description = None

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()

        if stripped.startswith("FILE:"):
            target_file = stripped[len("FILE:"):].strip()
            i += 1
            continue

        if stripped.startswith("##"):
            pending_description = stripped[2:].strip()
            i += 1
            continue

        if stripped == SEARCH_MARK:
            block_start_line = i + 1
            i += 1
            search_lines = []
            while i < len(lines) and lines[i].strip() != DIVIDER_MARK:
                search_lines.append(lines[i])
                i += 1
            if i >= len(lines):
                raise ValueError(f"{path}:{block_start_line}: unterminated SEARCH block (missing '=======')")
            i += 1  # skip divider

            replace_lines = []
            while i < len(lines) and lines[i].strip() != REPLACE_MARK:
                replace_lines.append(lines[i])
                i += 1
            if i >= len(lines):
                raise ValueError(f"{path}:{block_start_line}: unterminated REPLACE block (missing '>>>>>>> REPLACE')")
            i += 1  # skip end marker

            blocks.append(PatchBlock(
                description=pending_description,
                search="\n".join(search_lines),
                replace="\n".join(replace_lines),
                line_no=block_start_line,
            ))
            pending_description = None
            continue

        i += 1

    if target_file is None:
        raise ValueError(f"{path}: missing 'FILE:' header")
    if not blocks:
        raise ValueError(f"{path}: no SEARCH/REPLACE blocks found")

    return PatchFile(path=path, target_file=target_file, blocks=blocks)


def apply_patch_file(patch_file, repo_root, dry_run, verbose):
    target_path = repo_root / patch_file.target_file
    applied = skipped = failed = 0

    if not target_path.exists():
        for block in patch_file.blocks:
            print(f"FAIL  {patch_file.target_file} [{block.label()}]: target file does not exist")
        return 0, 0, len(patch_file.blocks)

    # Target files may be CRLF or LF (this repo has both). Normalize to '\n' for
    # matching -- patch SEARCH/REPLACE text is always authored with '\n' -- and
    # restore the file's original line ending convention on write.
    raw = target_path.read_bytes()
    newline = "\r\n" if b"\r\n" in raw else "\n"
    content = raw.decode("utf-8").replace("\r\n", "\n")

    for block in patch_file.blocks:
        count = content.count(block.search)
        if count == 1:
            content = content.replace(block.search, block.replace, 1)
            applied += 1
            if verbose:
                print(f"OK    {patch_file.target_file} [{block.label()}]")
        elif count > 1:
            failed += 1
            print(f"FAIL  {patch_file.target_file} [{block.label()}]: SEARCH text matches {count} times (must be unique)")
        else:
            if block.replace and content.count(block.replace) >= 1:
                skipped += 1
                if verbose:
                    print(f"SKIP  {patch_file.target_file} [{block.label()}]: already applied")
            else:
                failed += 1
                print(f"FAIL  {patch_file.target_file} [{block.label()}]: SEARCH text not found "
                      f"(upstream source likely changed here -- update the patch)")

    if applied and not dry_run:
        out = content if newline == "\n" else content.replace("\n", newline)
        target_path.write_bytes(out.encode("utf-8"))

    return applied, skipped, failed


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("patch_dir", nargs="?", default="patches/unlock",
                         help="Directory containing .hocpatch files (default: patches/unlock)")
    parser.add_argument("--check", action="store_true", help="Dry run: report without writing any files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Also print OK/SKIP lines, not just failures")
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parent
    patch_dir_arg = pathlib.Path(args.patch_dir)
    patch_dir = patch_dir_arg if patch_dir_arg.is_absolute() else repo_root / patch_dir_arg

    if not patch_dir.is_dir():
        print(f"error: patch directory not found: {patch_dir}", file=sys.stderr)
        return 2

    patch_paths = sorted(patch_dir.glob("*.hocpatch"))
    if not patch_paths:
        print(f"error: no .hocpatch files found in {patch_dir}", file=sys.stderr)
        return 2

    total_applied = total_skipped = total_failed = 0
    for p in patch_paths:
        try:
            pf = parse_patch_file(p)
        except ValueError as e:
            print(f"FAIL  {p.name}: {e}")
            total_failed += 1
            continue
        a, s, f = apply_patch_file(pf, repo_root, args.check, args.verbose)
        total_applied += a
        total_skipped += s
        total_failed += f

    mode = "checked" if args.check else "applied"
    print()
    print(f"{total_applied} {mode}, {total_skipped} already applied, {total_failed} failed "
          f"(across {len(patch_paths)} patch file(s))")

    return 1 if total_failed else 0


if __name__ == "__main__":
    sys.exit(main())
