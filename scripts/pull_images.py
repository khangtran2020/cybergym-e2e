"""Pre-download all Docker images referenced by project and task configs."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import docker
import tomli

DEFAULT_BUILD_IMAGE = (
    "gcr.io/oss-fuzz-base/base-builder"
    "@sha256:8eda74a11e800aead5a041ee479a65b33dab3150d6e89e5694e2b6eb27be98fc"
)

client = docker.from_env()


def count_num_file_change_from_git_diff(git_diff: str, threshold: int = 1) -> bool:
    """
    Count the number of file changes from a git diff string.
    If the number of changes exceeds the threshold, return False.
    """
    num_changes = 0
    for line in git_diff.splitlines():
        if line.startswith("diff --git"):
            num_changes += 1
            if num_changes > threshold:
                return False
    return True


def collect_images(projects_dir, threshold: int = 1, debug: bool = False) -> set:
    images = set()
    projects_dir = Path(projects_dir)

    for project_toml in sorted(projects_dir.glob("*/project.toml")):
        project_config = tomli.loads(project_toml.read_text())
        project_image = project_config.get("build_image")

        task_dirs = []
        for dir in project_toml.parent.iterdir():
            # only get dir that git diff is less than a threshold
            if dir.is_dir() and (dir / "config.toml").exists():
                git_diff_file = dir / "patch.diff"
                if git_diff_file.exists():
                    with open(git_diff_file, "r") as f:
                        git_diff = f.read()
                    if count_num_file_change_from_git_diff(git_diff, threshold):
                        task_dirs.append(dir)
                        print(f"  Found task dir: {dir} (git diff within threshold)")
            if debug:
                if len(task_dirs) > 50:
                    break  # Limit to 30 task dirs for debugging

        if project_image:
            images.add(project_image)

        for task_dir in task_dirs:
            merged = dict(project_config)
            merged.update(tomli.loads((task_dir / "config.toml").read_text()))
            images.add(merged.get("build_image", DEFAULT_BUILD_IMAGE))

    return images


def pull_image(image):
    print(f"Pulling {image}...")
    try:
        if "@sha256:" in image:
            client.images.pull(image)
        else:
            repo, tag = image.rsplit(":", 1)
            client.images.pull(repo, tag=tag)
        print(f"  OK: {image}")
    except docker.errors.APIError as e:
        print(f"  FAILED: {image}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Pre-download all Docker images needed by cybergym tasks."
    )
    parser.add_argument(
        "--projects-dir",
        "-d",
        default="./projects",
        help="Path to the projects directory (default: ./projects)",
    )
    parser.add_argument(
        "--max-workers",
        "-w",
        type=int,
        default=4,
        help="Max concurrent pulls (default: 4)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only list images, don't pull",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Debug mode: limit the number of task dirs processed",
    )
    parser.add_argument(
        "--threshold",
        type=int,
        default=1,
        help="Threshold for number of file changes in git diff (default: 1)",
    )
    args = parser.parse_args()

    images = collect_images(
        args.projects_dir, threshold=args.threshold, debug=args.debug
    )
    print(f"Found {len(images)} unique images.")

    if args.dry_run:
        for img in sorted(images):
            print(f"  {img}")
        return

    if args.max_workers <= 1:
        for img in sorted(images):
            pull_image(img)
    else:
        with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
            futures = {executor.submit(pull_image, img): img for img in sorted(images)}
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"  ERROR: {futures[future]}: {e}")


if __name__ == "__main__":
    main()
