import os
from pathlib import Path

DATA_DIR = Path(os.getenv("QORE_DATA_DIR", Path(__file__).resolve().parents[2] / ".local-data")).resolve()
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 2_000_000))
MAX_TOTAL_BYTES = int(os.getenv("MAX_TOTAL_BYTES", 8_000_000))
MAX_FILES = int(os.getenv("MAX_FILES", 80))
MAX_ZIP_COMPRESSED_BYTES = int(os.getenv("MAX_ZIP_COMPRESSED_BYTES", 4_000_000))
