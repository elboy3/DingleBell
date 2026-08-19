"""
Checks the actual state of your local setup against Phase 1's deploy
checklist (see STATUS.md) and prints a pass/fail report. This checks
what's really true on disk/in config - not what you remember doing.

    python -m apt_agent.check_setup
"""
import importlib
import os
import sys

import yaml

CHECK_MARK = "\u2705"
CROSS_MARK = "\u274c"
WARN_MARK = "\u26a0\ufe0f "

REQUIRED_PACKAGES = [
    "googleapiclient",
    "google.oauth2.credentials",
    "google_auth_oauthlib.flow",
    "bs4",
    "yaml",
    "dateutil",
]

PLACEHOLDER_VALUES = {"you@example.com", "cricket@example.com", "apartment-agent@example.com"}


def check(label: str, passed: bool, detail: str = "") -> bool:
    mark = CHECK_MARK if passed else CROSS_MARK
    line = f"{mark} {label}"
    if detail:
        line += f" - {detail}"
    print(line)
    return passed


def check_packages() -> bool:
    all_ok = True
    missing = []
    for pkg in REQUIRED_PACKAGES:
        try:
            importlib.import_module(pkg)
        except ImportError:
            missing.append(pkg)
            all_ok = False
    detail = "all present" if all_ok else f"missing: {', '.join(missing)} (run: pip install -r requirements.txt)"
    return check("Python dependencies installed", all_ok, detail)


def check_credentials_file() -> bool:
    exists = os.path.exists("credentials.json")
    detail = "" if exists else "run through Google Cloud OAuth setup, save file here (see README step 1)"
    return check("credentials.json present", exists, detail)


def check_token_file() -> bool:
    exists = os.path.exists("token.json")
    detail = "" if exists else "run: python -m apt_agent.gmail_auth"
    return check("token.json present (OAuth completed)", exists, detail)


def check_config() -> tuple[bool, bool]:
    """Returns (config_exists, config_looks_customized)."""
    if not os.path.exists("config.yaml"):
        check("config.yaml present", False, "should exist from the repo scaffold")
        return False, False

    with open("config.yaml") as f:
        cfg = yaml.safe_load(f)

    check("config.yaml present", True)

    recipients = cfg.get("notify", {}).get("recipients", [])
    from_address = cfg.get("notify", {}).get("from_address", "")

    still_placeholder = (
        any(r in PLACEHOLDER_VALUES for r in recipients)
        or from_address in PLACEHOLDER_VALUES
    )
    customized = check(
        "config.yaml notify section customized (not placeholder emails)",
        not still_placeholder,
        "edit notify.recipients / notify.from_address" if still_placeholder else "",
    )

    price_min = cfg.get("search", {}).get("price_min")
    price_max = cfg.get("search", {}).get("price_max")
    check(
        "config.yaml price range set",
        price_min is not None and price_max is not None,
        f"${price_min}-${price_max}" if price_min else "not set",
    )

    return True, customized


def check_listings_db() -> bool:
    exists = os.path.exists("listings.db")
    detail = "" if exists else "will be created on first run (normal if you haven't run it yet)"
    return check("listings.db exists (agent has run at least once)", exists, detail)


def check_git_remote() -> bool:
    if not os.path.exists(".git"):
        check("git repo initialized", False, "run: git init && git remote add origin <your-repo-url>")
        return False
    check("git repo initialized", True)

    import subprocess
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        has_remote = result.returncode == 0 and result.stdout.strip()
        detail = result.stdout.strip() if has_remote else "run: git remote add origin <your-repo-url>"
        return check("git remote configured", bool(has_remote), detail)
    except (subprocess.SubprocessError, FileNotFoundError):
        return check("git remote configured", False, "couldn't check - is git installed?")


def main():
    print("=" * 60)
    print("Phase 1 setup check - what's actually true right now")
    print("=" * 60)
    print()

    print("-- Local environment --")
    check_packages()
    check_credentials_file()
    check_token_file()
    print()

    print("-- Config --")
    config_exists, config_customized = check_config()
    print()

    print("-- Deployment readiness --")
    check_git_remote()
    check_listings_db()
    print()

    print("-" * 60)
    print("Note: this can't check GitHub Secrets, Actions workflow runs,")
    print("or your email alert subscriptions - verify those manually via")
    print("the GitHub Actions tab and each listing site's settings.")
    print("See STATUS.md for the full manual-vs-Claude checklist.")


if __name__ == "__main__":
    main()
