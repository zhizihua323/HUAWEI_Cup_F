"""Shared paths and serialization for the F-problem baseline study.

AI-assisted: OpenAI Codex, OpenAI, used 2026-09-24.
Exact model/version and release date are not verified; see solution/README.md.
"""
from pathlib import Path
import json
import os
import sys
import numpy as np

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT.parent
DATA = WORKSPACE / 'F题' / 'real_attachments'
OUTPUT = PROJECT / 'outputs'
REPORTS = PROJECT / 'reports'
SEED = 20260924

def configure_stdout():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

def output_dir(name):
    path = OUTPUT / name
    path.mkdir(parents=True, exist_ok=True)
    return path

def extended_path(path):
    path = str(Path(path).resolve())
    return '\\\\?\\' + path if os.name == 'nt' and not path.startswith('\\\\?\\') else path

def save_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    def convert(x):
        if isinstance(x, np.generic): return x.item()
        if isinstance(x, np.ndarray): return x.tolist()
        if isinstance(x, Path): return str(x)
        raise TypeError(type(x).__name__)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=convert, allow_nan=False), encoding='utf-8')

def write_report(name, text):
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text(text, encoding='utf-8')
