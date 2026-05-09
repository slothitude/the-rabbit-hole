"""Freeze the live site and push static HTML to gh-pages branch."""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

def main():
    # Step 1: Run freeze
    print("=== Freezing live site ===")
    subprocess.run([sys.executable, "freeze.py"], check=True)

    # Step 2: Init a temp git repo in _site and push to gh-pages
    site = Path("_site")
    if not site.exists():
        print("ERROR: _site/ not found. Run freeze.py first.")
        sys.exit(1)

    print("\n=== Pushing to gh-pages ===")
    # Get the remote URL from the main repo
    remote = subprocess.check_output(
        ["git", "remote", "get-url", "origin"],
        cwd=Path(__file__).parent,
        text=True
    ).strip()

    subprocess.run(["git", "init"], cwd=site, check=True)
    subprocess.run(["git", "add", "-A"], cwd=site, check=True)
    subprocess.run(
        ["git", "commit", "-m", f"Static snapshot $(date +%Y-%m-%d-%H%M)"],
        cwd=site, check=True
    )
    subprocess.run(
        ["git", "branch", "-M", "gh-pages"],
        cwd=site, check=True
    )
    subprocess.run(
        ["git", "remote", "add", "origin", remote],
        cwd=site, check=True
    )
    subprocess.run(
        ["git", "push", "-f", "origin", "gh-pages"],
        cwd=site, check=True
    )

    print("\nDone! Site pushed to gh-pages branch.")

if __name__ == "__main__":
    main()
