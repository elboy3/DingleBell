"""Thin wrapper around apt_agent.main.load_config() so the webapp reads the
same config.yaml (+ env var overrides) as the email pipeline and
browser_import.py - one config loader, three consumers."""
from apt_agent.main import load_config


def load_webapp_config(path: str = "config.yaml") -> dict:
    return load_config(path)
