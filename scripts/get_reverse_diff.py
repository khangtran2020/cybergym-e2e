"""Create reverse.diff for patches that modify exactly one existing file."""

import argparse
import io
from pathlib import Path
import re

HUNK_HEADER = re.compile(rb"@@ -(\d+(?:,\d+)?) \+(\d+(?:,\d+)?) @@(.*)")
INDEX_HEADER = re.compile(rb"index ([0-9a-f]+)\.\.([0-9a-f]+)(.*)")


def reverse_diff(patch: bytes) -> bytes:
    """Reverse a single-file Git text diff, raising ValueError if ineligible.

    Work on bytes to preserve source encodings and line endings. Commit messages,
    diff statistics and email signatures are omitted from the generated patch.
    """
    lines = io.BytesIO(patch).readlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(b"diff --git ")]
    if len(starts) != 1:
        raise ValueError("patch must modify exactly one file")
    lines = lines[starts[0] :]
    first_hunk = next(
        (i for i, line in enumerate(lines) if line.startswith(b"@@ ")), len(lines)
    )
    headers = lines[:first_hunk]
    if any(
        line.startswith((b"new file mode ", b"deleted file mode ")) for line in headers
    ):
        raise ValueError("file additions and deletions are excluded")
    if any(line.startswith((b"rename ", b"copy ")) for line in headers):
        raise ValueError("file renames and copies are excluded")
    if any(
        line.startswith((b"GIT binary patch", b"Binary files ")) for line in headers
    ):
        raise ValueError("binary patches are unsupported")

    old_headers = [
        line[4:].rstrip(b"\n") for line in headers if line.startswith(b"--- ")
    ]
    new_headers = [
        line[4:].rstrip(b"\n") for line in headers if line.startswith(b"+++ ")
    ]
    if len(old_headers) != 1 or len(new_headers) != 1:
        raise ValueError("expected one pair of file headers")
    old_path = old_headers[0].split(b"\t", 1)[0]
    new_path = new_headers[0].split(b"\t", 1)[0]
    if b"/dev/null" in (old_path, new_path):
        raise ValueError("file additions and deletions are excluded")
    # Git quotes paths containing special characters, including the a/b prefix.
    old_name = re.sub(rb'^("?)a/', rb"\1", old_path)
    new_name = re.sub(rb'^("?)b/', rb"\1", new_path)
    if old_name != new_name:
        raise ValueError("patch must modify an existing file at the same path")
    if first_hunk == len(lines):
        raise ValueError("patch has no text hunks")

    result = []
    for line in headers:
        if line.startswith(b"index "):
            line = INDEX_HEADER.sub(rb"index \2..\1\3", line)
        elif line.startswith(b"old mode "):
            line = b"new mode " + line[len(b"old mode ") :]
        elif line.startswith(b"new mode "):
            line = b"old mode " + line[len(b"new mode ") :]
        result.append(line)

    i = first_hunk
    while i < len(lines) and lines[i].startswith(b"@@ "):
        match = HUNK_HEADER.fullmatch(lines[i].rstrip(b"\n"))
        if match is None:
            raise ValueError("invalid hunk header")
        old_range, new_range, context = match.groups()
        old_left = int(old_range.split(b",")[1]) if b"," in old_range else 1
        new_left = int(new_range.split(b",")[1]) if b"," in new_range else 1
        result.append(
            b"@@ -" + new_range + b" +" + old_range + b" @@" + context + b"\n"
        )
        i += 1
        while old_left or new_left:
            if i >= len(lines):
                raise ValueError("truncated hunk")
            line = lines[i]
            if line.startswith(b" ") or line == b"\n":
                old_left -= 1
                new_left -= 1
                # Git also accepts empty context lines without a space prefix.
                result.append(b" \n" if line == b"\n" else line)
            elif line.startswith(b"-"):
                old_left -= 1
                result.append(b"+" + line[1:])
            elif line.startswith(b"+"):
                new_left -= 1
                result.append(b"-" + line[1:])
            elif line.startswith(b"\\ No newline at end of file"):
                result.append(line)
            else:
                raise ValueError("invalid hunk body")
            if old_left < 0 or new_left < 0:
                raise ValueError("hunk line counts do not match its header")
            i += 1
        if i < len(lines) and lines[i].startswith(b"\\ No newline at end of file"):
            result.append(lines[i])
            i += 1

    # Accept the optional format-patch signature, but never silently drop hunks.
    if any(line.strip() for line in lines[i:]) and lines[i] != b"-- \n":
        raise ValueError("unexpected content after the final hunk")
    return b"".join(result)


def generate_reverse_diffs(
    projects_dir: Path, dry_run: bool = False
) -> tuple[int, int]:
    """Visit project/task directories using the layout in pull_images.py."""
    generated = skipped = 0
    for project_toml in sorted(projects_dir.glob("*/project.toml")):
        for task_dir in sorted(project_toml.parent.iterdir()):
            if not task_dir.is_dir() or not (task_dir / "config.toml").is_file():
                continue
            patch_path = task_dir / "patch.diff"
            if not patch_path.is_file():
                continue
            try:
                reversed_patch = reverse_diff(patch_path.read_bytes())
            except ValueError as exc:
                skipped += 1
                print(f"SKIP {patch_path}: {exc}")
                continue
            reverse_path = task_dir / "reverse.diff"
            if not dry_run:
                reverse_path.write_bytes(reversed_patch)
            generated += 1
            print(f"{'Would write' if dry_run else 'Wrote'} {reverse_path}")
    return generated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects-dir",
        "-d",
        type=Path,
        default=Path("./projects"),
        help="Path to the projects directory (default: ./projects)",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List results without writing files"
    )
    args = parser.parse_args()
    if not args.projects_dir.is_dir():
        parser.error(f"projects directory does not exist: {args.projects_dir}")
    generated, skipped = generate_reverse_diffs(args.projects_dir, args.dry_run)
    print(
        f"{'Would generate' if args.dry_run else 'Generated'} {generated} reverse diffs; skipped {skipped} patches."
    )


if __name__ == "__main__":
    main()
