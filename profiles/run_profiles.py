import time
import json
import os
import re
import subprocess
from gologin import GoLogin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

# --- Настройки ---
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
PROFILES_FILE = os.path.join(_SCRIPT_DIR, "data", "profiles.json")
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTdjY2IzNmI3MWE0Njg0MWUzNGRhYTciLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2OTdjZDUxMWUzMGE5OWU4NmVlNTM5ZTMifQ.3N3hPO6EsoAk_utpQSMoxJtbiKLGyw3DmTF0jbJLcwk"
EXTENSION_ID = "opcccnnccfmnjaeehjpokgbhpiahceek"
DELAY_AFTER_ENABLE = 3
PROFILE_DELAY = 20
SERVER_LAUNCH_URL = "http://localhost:8080/launch.html"

_CHROMEDRIVER_EXE = "chromedriver.exe" if (os.name == "nt" or os.getenv("OS", "").lower().startswith("windows")) else "chromedriver"


def _get_local_driver_versions():
    """Возвращает список версий драйверов в D_V/drivers, от новых к старым."""
    if not os.path.isdir(os.path.join(_REPO_ROOT, "D_V", "drivers")):
        return []
    versions = []
    for name in os.listdir(os.path.join(_REPO_ROOT, "D_V", "drivers")):
        path = os.path.join(_REPO_ROOT, "D_V", "drivers", name)
        if not os.path.isdir(path):
            continue
        exe = os.path.join(path, _CHROMEDRIVER_EXE)
        if os.path.isfile(exe):
            versions.append(name)
    def version_key(v):
        return tuple(int(x) for x in re.split(r"\.", v.strip())[:4] if x.isdigit())
    versions.sort(key=version_key, reverse=True)
    return versions


def create_driver_for_debugger(debugger_address):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("debuggerAddress", debugger_address)
    versions = _get_local_driver_versions()
    if not versions:
        raise FileNotFoundError(
            f"В папке D_V/drivers нет драйверов. Добавьте подпапки с версиями и chromedriver.exe внутри."
        )
    last_error = None
    for ver in versions:
        path = os.path.join(_REPO_ROOT, "D_V", "drivers", ver, _CHROMEDRIVER_EXE)
        if not os.path.isfile(path):
            continue
        try:
            service = Service(path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            print(f"[.] Использован драйвер: {ver}")
            return driver
        except Exception as e:
            last_error = e
            continue
    if last_error:
        raise last_error
    raise RuntimeError("Не удалось подключиться ни одним драйвером.")


def read_profiles(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else data.get("profiles", [])
    except Exception as e:
        print(f"[X] Ошибка чтения файла: {e}")
        return []


if __name__ == "__main__":
    if API_TOKEN == "your_api_token_here":
        print("[!] Укажи API токен в коде!")
        exit(1)
    if EXTENSION_ID == "your_extension_id_here":
        print("[!] Укажи ID расширения!")
        exit(1)

    profiles = read_profiles(PROFILES_FILE)
    if not profiles:
        print("[X] Нет профилей для обработки.")
        exit(1)

    print(f"[*] Найдено профилей: {len(profiles)}\n")

    for idx, profile in enumerate(profiles, start=1):
        profile_id = profile.get("id")
        profile_name = profile.get("name", "Без имени")

        if not profile_id:
            print(f"{idx}. [!] Пропущен: нет ID")
            continue

        print(f"\n-> {idx}. Обработка профиля: {profile_name} (ID: {profile_id})")

        gl = GoLogin({
            "token": API_TOKEN,
            "profile_id": profile_id,
            "skip_proxy_check": True,
        })

        driver = None
        try:
            debugger_address = gl.start()
<<<<<<< HEAD
            print(f"[OK] Браузер запущен")
            time.sleep(2)
=======
            print(f"[OK] Браузер запущен" )
>>>>>>> 6912d430ca8cbfa3a7b10474bcdb2e355d8c11a8

            driver = create_driver_for_debugger(debugger_address)
            print(f"[OK] Selenium подключен")

            # Активируем расширение через JavaScript (по ID или по имени)
            enable_script = """
            const extensions = document.querySelector('extensions-manager')
                .shadowRoot.querySelector('#items-list')
                .querySelectorAll('extensions-item');

            for (let ext of extensions) {
                if (ext.getAttribute('id') === '%s') {
                    const toggle = ext.shadowRoot.querySelector('#enabled');
                    if (!toggle.checked) {
                        toggle.click();
                    }
                    return true;
                }
            }
            return false;
            """ % EXTENSION_ID

            enable_by_name_script = """
            const extensions = document.querySelector('extensions-manager')
                .shadowRoot.querySelector('#items-list')
                .querySelectorAll('extensions-item');
            for (let ext of extensions) {
                const nameEl = ext.shadowRoot.querySelector('#name');
                if (nameEl && nameEl.textContent.includes('Ozon Seller Messenger')) {
                    const toggle = ext.shadowRoot.querySelector('#enabled');
                    if (toggle && !toggle.checked) toggle.click();
                    return true;
                }
            }
            return false;
            """

            result = driver.execute_script(enable_script)
            if result is False:
                result = driver.execute_script(enable_by_name_script)
                if result:
                    print(f"[OK] Расширение «Ozon Seller Messenger» активировано (по имени)")
                else:
                    print(f"[!] Расширение не найдено. Убедитесь, что оно уже установлено в профиль GoLogin.")
            else:
                print(f"[OK] Расширение активировано: {EXTENSION_ID}")

            time.sleep(DELAY_AFTER_ENABLE)

            # Открываем лаунчер
            launch_url = f"{SERVER_LAUNCH_URL}?profile_id={profile_id}"
            driver.execute_script("window.open(arguments[0], '_blank');", launch_url)
            time.sleep(3)
            driver.switch_to.window(driver.window_handles[-1])
            print(f"[.] Открыт лаунчер с profile_id={profile_id}")

            print(f"[...] Браузер открыт {PROFILE_DELAY} сек - можно пользоваться расширением...")
            time.sleep(PROFILE_DELAY)

        except Exception as e:
            print(f"[X] Ошибка при работе с профилем {profile_name}: {e}")

        finally:
            if driver:
                driver.quit()
                print(f"[.] Selenium закрыт")
            try:
                gl.stop()
                print(f"[.] Профиль остановлен")
            except:
                pass

            if idx < len(profiles):
                print(f"[...] Ожидание {PROFILE_DELAY} сек перед следующим профилем...")
                time.sleep(PROFILE_DELAY)

    print("[OK] Все профили обработаны: расширения активированы (если были установлены)!")