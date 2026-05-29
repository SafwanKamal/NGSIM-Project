from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ngsim_ego.load_data import candidate_data_files, load_config, resolve_project_path


def _download_file(url: str, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))
        downloaded = 0
        with output_path.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                handle.write(chunk)
                downloaded += len(chunk)
                if total:
                    percent = downloaded / total * 100
                    print(f"\rDownloading {output_path.name}: {percent:5.1f}%", end="")
        print()


def _extract_zip(zip_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(destination)


def _extract_nested_zips(root: Path) -> None:
    for zip_path in sorted(root.rglob("*.zip")):
        destination = zip_path.with_suffix("")
        marker = destination / ".extracted"
        if marker.exists():
            continue
        print(f"Extracting nested archive: {zip_path}")
        _extract_zip(zip_path, destination)
        marker.write_text("extracted\n", encoding="utf-8")


def _copy_trajectory_files(source_root: Path, raw_dir: Path) -> list[Path]:
    copied = []
    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        name = path.name.lower()
        if path.suffix.lower() not in {".txt", ".csv", ".dat"}:
            continue
        if "traject" not in name or "dictionary" in name:
            continue
        target = raw_dir / path.name
        if path.resolve() != target.resolve():
            shutil.copy2(path, target)
        copied.append(target)
    return copied


def main() -> None:
    config = load_config()
    dot_config = config.get("official_dot", {})
    metadata_url = dot_config.get("dataset_api", "https://data.transportation.gov/api/views/8ect-6jqj")
    attachment_name = dot_config.get("attachment_name", "US-101-LosAngeles-CA.zip")
    download_dir = resolve_project_path(dot_config.get("download_dir", "data/raw/us101_official"))
    raw_dir = resolve_project_path(config.get("raw_data_dir", "data/raw"))

    metadata = requests.get(metadata_url, timeout=60).json()
    attachments = metadata.get("metadata", {}).get("attachments", [])
    attachment = next((item for item in attachments if item.get("filename") == attachment_name), None)
    if not attachment:
        available = [item.get("filename") for item in attachments]
        raise RuntimeError(f"Could not find {attachment_name!r}. Available attachments: {available}")

    asset_id = attachment["assetId"]
    download_url = f"{metadata_url}/files/{asset_id}?download=true&filename={attachment_name}"
    zip_path = download_dir / attachment_name
    extract_dir = download_dir / "extracted"

    if not zip_path.exists():
        print(f"Downloading official DOT attachment: {download_url}")
        _download_file(download_url, zip_path)
    else:
        print(f"Using existing download: {zip_path}")

    print(f"Extracting: {zip_path}")
    _extract_zip(zip_path, extract_dir)
    if dot_config.get("extract_nested_zips", True):
        _extract_nested_zips(extract_dir)

    copied = _copy_trajectory_files(extract_dir, raw_dir)
    print("Trajectory-like files copied into data/raw/:")
    for path in copied:
        print(path)

    print("All trajectory-like files now visible to the loader:")
    for path in candidate_data_files(config.get("raw_data_dir", "data/raw")):
        print(path)


if __name__ == "__main__":
    main()
