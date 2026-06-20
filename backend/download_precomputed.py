"""
Downloads pre-computed embeddings and profile cache from Google Drive.
Required before running generate_submission.py for the first time.
"""


import os
import sys
import zipfile
from pathlib import Path


# Google Drive file ID for precomputed_data.zip
GDRIVE_FILE_ID = "1p2HjVsxhfPI3YwqF25veBqQGa-HooywJ"
GDRIVE_URL = f"https://drive.google.com/uc?export=download&id={GDRIVE_FILE_ID}"

BACKEND_DIR = Path(__file__).parent
ZIP_PATH = BACKEND_DIR / "precomputed_data.zip"

CACHE_FILE = BACKEND_DIR / "cache" / "processed_profiles.pkl"
QDRANT_FILE = BACKEND_DIR / "qdrant_data" / "collection" / "candidates" / "storage.sqlite"


def already_downloaded():
    """Check if the pre-computed files already exist."""
    return CACHE_FILE.exists() and QDRANT_FILE.exists()


def download_with_gdown():
    """Download using gdown (handles Google Drive's virus scan warning for large files)."""
    try:
        import gdown   # type: ignore
    except ImportError:
        print("  Installing gdown for Google Drive download...")
        os.system(f"{sys.executable} -m pip install gdown")
        import gdown    # type: ignore

    print(f"  Downloading from Google Drive (file ID: {GDRIVE_FILE_ID})")
    print(f"  Target: {ZIP_PATH}")
    print(f"  This is a one-time download (~500MB).")
    print()

    gdown.download(
        f"https://drive.google.com/uc?id={GDRIVE_FILE_ID}",
        str(ZIP_PATH),
        quiet=False,
    )


def main():
    print("=" * 60)
    print("  PRE-COMPUTED DATA DOWNLOADER")
    print("=" * 60)

    if already_downloaded():
        print("\n  Pre-computed data already present. Nothing to do.")
        print(f"    Cache:  {CACHE_FILE}")
        print(f"    Qdrant: {QDRANT_FILE}")
        return

    print("\n  Pre-computed data not found. Downloading from Google Drive...")
    print()

    try:
        download_with_gdown()

        if not ZIP_PATH.exists():
            raise RuntimeError("Download failed — zip file not created")

        size_mb = ZIP_PATH.stat().st_size / (1024 * 1024)
        print(f"\n  Download complete: {size_mb:.1f} MB")

        print("\n  Extracting to backend folder...")
        with zipfile.ZipFile(ZIP_PATH, "r") as z:
            z.extractall(BACKEND_DIR)
        print("  Extraction complete.")

        ZIP_PATH.unlink()
        print("  Cleaned up zip file.")

        print("\n" + "=" * 60)
        print("  SUCCESS — Pre-computed data ready.")
        print("  You can now run: python generate_submission.py")
        print("=" * 60)

    except Exception as e:
        print(f"\n  ERROR: {e}")
        print(f"\n  Manual fallback:")
        print(f"  1. Download from: https://drive.google.com/file/d/{GDRIVE_FILE_ID}/view")
        print(f"  2. Extract precomputed_data.zip into: {BACKEND_DIR}")
        print(f"  3. Verify these files exist:")
        print(f"     - {CACHE_FILE}")
        print(f"     - {QDRANT_FILE}")
        sys.exit(1)


if __name__ == "__main__":
    main()