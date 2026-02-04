import os
import sys
import json
import zipfile
import tarfile
from pathlib import Path

import requests
from tqdm import tqdm

# === Определение ОС ===
def get_platform():
    system = sys.platform
    if system.startswith("linux"):
        return "linux64"
    elif system == "darwin":
        # Проверяем архитектуру (Intel vs Apple Silicon)
        import platform
        machine = platform.machine()
        if machine == "arm64":
            return "mac-arm64"
        else:
            return "mac-x64"
    elif system == "win32" or system == "cygwin":
        return "win32"
    elif system == "win64" or (system == "win32" and os.environ.get("PROCESSOR_ARCHITECTURE") == "AMD64"):
        return "win64"
    else:
        raise RuntimeError(f"Unsupported OS: {system}")

PLATFORM = get_platform()
CHROMEDRIVER_BASE_URL = "https://edgedl.me.gvt1.com/edgedl/chrome/chrome-for-testing"
VERSIONS_URL = "https://googlechromelabs.github.io/chrome-for-testing/known-good-versions-with-downloads.json"

OUTPUT_DIR = Path("chromedrivers")
OUTPUT_DIR.mkdir(exist_ok=True)

def download_file(url, dest):
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    total = int(resp.headers.get('content-length', 0))
    with open(dest, 'wb') as f, tqdm(
        desc=dest.name,
        total=total,
        unit='B',
        unit_scale=True,
        unit_divisor=1024,
    ) as bar:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            bar.update(len(chunk))

def extract_archive(archive_path, extract_to):
    if archive_path.suffixes[-1] == ".zip":
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
            # Переместим chromedriver из подпапки (если есть)
            for root, dirs, files in os.walk(extract_to):
                for file in files:
                    if file == "chromedriver" or file == "chromedriver.exe":
                        os.replace(os.path.join(root, file), extract_to / file)
                        # Удалим пустые подпапки (опционально)
                        for d in dirs:
                            try:
                                os.rmdir(os.path.join(root, d))
                            except OSError:
                                pass
    elif archive_path.suffix == ".tar.gz":
        with tarfile.open(archive_path, 'r:gz') as tar_ref:
            tar_ref.extractall(extract_to)
            for root, dirs, files in os.walk(extract_to):
                for file in files:
                    if file == "chromedriver":
                        os.replace(os.path.join(root, file), extract_to / file)

def main(num_versions=15):
    print(f"Определена платформа: {PLATFORM}")
    print("Получение списка версий...")

    resp = requests.get(VERSIONS_URL)
    resp.raise_for_status()
    data = resp.json()

    # Фильтруем только версии, содержащие нужную платформу
    versions_with_driver = []
    for item in data["versions"]:
        version = item["version"]
        downloads = item.get("downloads", {})
        if "chromedriver" in downloads:
            for dl in downloads["chromedriver"]:
                if dl["platform"] == PLATFORM:
                    versions_with_driver.append({
                        "version": version,
                        "url": dl["url"]
                    })
                    break  # одна версия — одна ссылка на нашу ОС

    # Берём последние N версий (они уже в порядке возрастания, но на всякий — отсортируем по номеру)
    from packaging.version import parse as parse_version
    versions_with_driver.sort(key=lambda x: parse_version(x["version"]), reverse=True)
    selected = versions_with_driver[:num_versions]

    print(f"Найдено подходящих версий: {len(versions_with_driver)}")
    print(f"Будет загружено последних {len(selected)} версий.")

    for item in selected:
        version = item["version"]
        url = item["url"]
        folder = OUTPUT_DIR / f"chromedriver_{version}"
        if folder.exists():
            print(f"✅ Пропуск: {version} уже скачан.")
            continue

        print(f"\n📥 Скачивание chromedriver {version} для {PLATFORM}...")
        folder.mkdir(parents=True, exist_ok=True)

        archive_name = url.split("/")[-1]
        archive_path = folder / archive_name

        try:
            download_file(url, archive_path)
            extract_archive(archive_path, folder)
            archive_path.unlink()  # удаляем архив после распаковки

            # Делаем исполняемым (для Linux/macOS)
            driver_path = folder / ("chromedriver.exe" if PLATFORM.startswith("win") else "chromedriver")
            if driver_path.exists():
                if not PLATFORM.startswith("win"):
                    os.chmod(driver_path, 0o755)
                print(f"✅ Успешно установлен: {version} → {driver_path}")
            else:
                print(f"❌ Не найден chromedriver в архиве для {version}")
        except Exception as e:
            print(f"❌ Ошибка при установке {version}: {e}")
            import traceback
            traceback.print_exc()

    print("\n🎉 Готово! Все драйверы сохранены в папке:", OUTPUT_DIR.absolute())

if __name__ == "__main__":
    main(num_versions=15)