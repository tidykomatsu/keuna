"""Extraction configuration - centralizes path handling"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_raw_data_root() -> Path:
    """
    Get raw data root directory.
    Priority:
      1. EUNACOM_RAW_DATA environment variable
      2. Default: project_root/data/raw
    """
    env_path = os.getenv("EUNACOM_RAW_DATA")
    print(env_path)
    if env_path:
        path = Path(env_path)
        assert path.exists(), f"EUNACOM_RAW_DATA path does not exist: {path}"
        return path

    # Default: relative to project
    project_root = Path(__file__).parent.parent.parent
    print(project_root)
    return project_root / "data" / "raw"


def get_processed_data_root() -> Path:
    """
    Get processed data output directory.
    Priority:
      1. EUNACOM_PROCESSED_DATA environment variable
      2. Default: project_root/data/processed
    """
    env_path = os.getenv("EUNACOM_PROCESSED_DATA")

    if env_path:
        path = Path(env_path)
        path.mkdir(parents=True, exist_ok=True)
        return path

    project_root = Path(__file__).parent.parent.parent
    processed = project_root / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    return processed
