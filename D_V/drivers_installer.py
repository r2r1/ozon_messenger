import os
import sys
import json
import zipfile
import tarfile
from pathlib import Path
import requests

# === Версии из вашего списка ===
VERSIONS = [
    "142.0.7444.175",
    "141.0.7390.54",
    "139.0.7258.127",
    "138.0.7204.50",
    "128.0.6613.36"
]

# === Определение платформы ===
def get_platform():
    system = sys.platform
    if system.startswith("linux"):
        return "linux64"
    elif system == "darwin":
        import platform
        return "mac-arm64" if platform.machine() == "arm64" else "mac-x64"
    elif system in ("win32", "cygwin") or (os.name == "nt"):
        return "win64"  # предполагаем 64-битную Windows
    else:
        raise RuntimeError(f"Unsupported OS: {system}")

PLATFORM = get_platform()
BASE_URL = "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing"
OUTPUT_DIR = Path("drivers")
OUTPUT_DIR.mkdir(exist_ok=True)

def download_and_extract(version):
    folder = OUTPUT_DIR / version
    if folder.exists():
        print(f"✅ Пропуск: {version} уже установлен.")
        return

    url = f"{BASE_URL}/{version}/{PLATFORM}/chromedriver-{PLATFORM}.zip"
    archive_path = folder / "chromedriver.zip"

    print(f"📥 Загрузка {version} для {PLATFORM}...")
    try:
        resp = requests.get(url, stream=True)
        if resp.status_code == 404:
            print(f"❌ Версия {version} не найдена на сервере (возможно, слишком новая или удалена).")
            return
        resp.raise_for_status()

        folder.mkdir(parents=True, exist_ok=True)
        with open(archive_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        # Распаковка
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(folder)

        # Удаляем архив и оставляем только chromedriver
        archive_path.unlink()
        # В новых версиях chromedriver лежит в подпапке chromedriver-<platform>/
        inner_dir = folder / f"chromedriver-{PLATFORM}"
        if inner_dir.exists():
            driver_src = inner_dir / ("chromedriver.exe" if PLATFORM.startswith("win") else "chromedriver")
            driver_dst = folder / ("chromedriver.exe" if PLATFORM.startswith("win") else "chromedriver")
            if driver_src.exists():
                driver_src.rename(driver_dst)
            # Удаляем пустую папку
            inner_dir.rmdir()

        # Делаем исполняемым (Linux/macOS)
        driver_path = folder / ("chromedriver.exe" if PLATFORM.startswith("win") else "chromedriver")
        if driver_path.exists() and not PLATFORM.startswith("win"):
            os.chmod(driver_path, 0o755)

        print(f"✅ Установлен: {version}")
    except Exception as e:
        print(f"❌ Ошибка при установке {version}: {e}")

def main():
    print(f"Определена платформа: {PLATFORM}")
    print(f"Будет установлено {len(VERSIONS)} версий chromedriver.\n")

    for ver in VERSIONS:
        download_and_extract(ver)

    print("\n🎉 Все доступные драйверы установлены в папку 'drivers'.")

if __name__ == "__main__":
    main()