import time
import json
import os
import subprocess
from gologin import GoLogin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- Настройки ---
# Перед запуском включите сервер: из папки server выполните python server.py
# (чтобы launch.html и profiles_with_sellers.json были доступны на localhost:8080)
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
PROFILES_FILE = os.path.join(_SCRIPT_DIR, "data", "profiles.json")  # Путь к списку профилей
EXTENSION_DIR = os.path.join(_REPO_ROOT, "extension")               # Папка расширения для «Загрузить распакованное»
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTdjY2IzNmI3MWE0Njg0MWUzNGRhYTciLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2OTdjZDUxMWUzMGE5OWU4NmVlNTM5ZTMifQ.3N3hPO6EsoAk_utpQSMoxJtbiKLGyw3DmTF0jbJLcwk"                      # Твой токен Gologin
EXTENSION_ID = "opcccnnccfmnjaeehjpokgbhpiahceek"                # ID расширения (появится после первой загрузки папки)
DELAY_BEFORE_ACTION = 5                                # Задержка перед действиями (сек)
DELAY_AFTER_ENABLE = 3                                 # Задержка после включения расширения (сек)
PROFILE_DELAY = 0                                     # Время на работу с одним профилем (браузер открыт), сек
# Страница-лаунчер: по profile_id расширение подтянет продавцов из server/profiles_with_sellers.json
SERVER_LAUNCH_URL = "http://localhost:8080/launch.html"
SERVER_PORT = 8080                                     # Должен совпадать с server/server.py
# Версия ChromeDriver должна совпадать с версией Chrome в GoLogin (см. ошибку session not created)
CHROMEDRIVER_VERSION = "141.0.7390.54"                 # Текущий Chrome в GoLogin: 141.0.7390.54

def read_profiles(filepath):
    """Читает список профилей из JSON"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else data.get("profiles", [])
    except Exception as e:
        print(f"[X] Ошибка чтения файла: {e}")
        return []


def set_clipboard_win(text):
    """Установить текст в буфер обмена (Windows). Путь без лишних переносов."""
    text = (text or "").strip()
    # В PowerShell экранируем одинарные кавычки удвоением
    escaped = text.replace("'", "''")
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", f"Set-Clipboard -Value '{escaped}'"],
            check=True, capture_output=True, timeout=5, cwd=_REPO_ROOT
        )
    except Exception as e:
        print(f"[!] Не удалось скопировать путь в буфер: {e}")


def enable_developer_mode_and_load_unpacked(driver, extension_path):
    """
    На chrome://extensions/:
    1) Включить режим разработчика, если выключен.
    2) Если наше расширение не найдено по EXTENSION_ID — нажать «Загрузить распакованное» и подставить путь.
    """
    # Включить режим разработчика (переключатель «Developer mode» / «Режим разработчика»)
    dev_mode_script = """
    const root = document.querySelector('extensions-manager');
    if (!root || !root.shadowRoot) return 'no-manager';
    const findInShadow = (el, fn) => {
        if (!el) return null;
        if (fn(el)) return el;
        const sh = el.shadowRoot || el.openOrClosedShadowRoot;
        if (sh) {
            for (const c of sh.querySelectorAll('*')) {
                const r = findInShadow(c, fn);
                if (r) return r;
            }
        }
        return null;
    };
    const toggle = findInShadow(root, el => {
        const t = (el.textContent || '').toLowerCase();
        const role = (el.getAttribute('role') || '');
        return (t.includes('developer') || t.includes('разработчик')) && (el.tagName === 'CR-TOGGLE' || role === 'switch' || el.type === 'checkbox');
    });
    if (toggle) {
        if (!toggle.checked) toggle.click();
        return 'dev-mode-on';
    }
    return 'toggle-not-found';
    """
    try:
        result = driver.execute_script(dev_mode_script)
        if result == "dev-mode-on":
            print("[OK] Режим разработчика включён")
        time.sleep(0.5)
    except Exception as e:
        print(f"[!] Режим разработчика: {e}")

    # Проверить, установлено ли уже расширение с нашим ID
    check_script = """
    const root = document.querySelector('extensions-manager');
    if (!root || !root.shadowRoot) return false;
    const list = root.shadowRoot.querySelector('#items-list') || root.shadowRoot.querySelector('extensions-item-list');
    if (!list) return false;
    const items = list.querySelectorAll('extensions-item');
    for (const item of items) {
        if (item.getAttribute('id') === '%s') return true;
    }
    return false;
    """ % EXTENSION_ID
    try:
        already_installed = driver.execute_script(check_script)
        if already_installed:
            return True
    except Exception:
        pass

    # Найти и нажать кнопку «Загрузить распакованное» / «Load unpacked»
    load_unpacked_script = """
    const root = document.querySelector('extensions-manager');
    if (!root || !root.shadowRoot) return 'no-manager';
    const findAll = (el, fn, acc) => {
        if (!el) return acc;
        if (fn(el)) acc.push(el);
        const sh = el.shadowRoot || el.openOrClosedShadowRoot;
        if (sh) {
            for (const c of sh.querySelectorAll('*')) {
                findAll(c, fn, acc);
            }
        }
        return acc;
    };
    const buttons = findAll(root, el => {
        if (el.tagName !== 'BUTTON' && el.tagName !== 'CR-BUTTON') return false;
        const t = (el.textContent || '').toLowerCase();
        return t.includes('load unpacked') || t.includes('загрузить распакованное') || t.includes('unpacked');
    }, []);
    if (buttons.length) {
        buttons[0].click();
        return 'clicked';
    }
    return 'button-not-found';
    """
    try:
        result = driver.execute_script(load_unpacked_script)
        if result != "clicked":
            print(f"[!] Кнопка «Загрузить распакованное» не найдена: {result}")
            return False
        print("[.] Открыто окно выбора папки расширения")
    except Exception as e:
        print(f"[!] Ошибка при нажатии «Загрузить распакованное»: {e}")
        return False

    time.sleep(1.2)

    # Подставить путь в диалог выбора папки (Windows): буфер обмена + Ctrl+V, Enter
    set_clipboard_win(extension_path)
    try:
        import pyautogui
        pyautogui.hotkey("ctrl", "v")
        time.sleep(0.4)
        pyautogui.press("enter")
        time.sleep(1.5)
        print(f"[OK] Расширение загружено из папки: {extension_path}")
        return True
    except ImportError:
        print("[!] Установите pyautogui (pip install pyautogui) для автоматической подстановки пути.")
        print(f"    Либо вручную выберите папку: {extension_path}")
        return False
    except Exception as e:
        print(f"[!] Ошибка при вводе пути в диалог: {e}")
        return False

if __name__ == "__main__":
    # Проверка токена
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

        # Инициализация GoLogin
        gl = GoLogin({
            "token": API_TOKEN,
            "profile_id": profile_id,
            "skip_proxy_check": True,
        })

        driver = None
        try:
            # Запуск браузера
            debugger_address = gl.start()
            print(f"[OK] Браузер запущен" )

            # Настройка Selenium (версия драйвера должна совпадать с Chrome в GoLogin)
            service = Service(ChromeDriverManager(CHROMEDRIVER_VERSION).install())
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_experimental_option("debuggerAddress", debugger_address)

            driver = webdriver.Chrome(service=service, options=chrome_options)
            print(f"[OK] Selenium подключен")

            # Открываем страницу расширений
            driver.get("chrome://extensions/")
            time.sleep(DELAY_BEFORE_ACTION)

            # При необходимости включаем режим разработчика и загружаем расширение из папки
            if not os.path.isdir(EXTENSION_DIR):
                print(f"[!] Папка расширения не найдена: {EXTENSION_DIR}")
            else:
                enable_developer_mode_and_load_unpacked(driver, os.path.abspath(EXTENSION_DIR))
                time.sleep(1)

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
                    print(f"[X] Расширение не найдено. Убедитесь, что папка {EXTENSION_DIR} загружена в профиль.")
            else:
                print(f"[OK] Расширение активировано: {EXTENSION_ID}")

            # Задержка после включения расширения
            time.sleep(DELAY_AFTER_ENABLE)

            # Открываем страницу-лаунчер с id профиля: расширение получит id и по нему
            # возьмёт продавцов из server/profiles_with_sellers.json и запустит рассылку
            launch_url = f"{SERVER_LAUNCH_URL}?profile_id={profile_id}"
            driver.execute_script("window.open(arguments[0], '_blank');", launch_url)
            time.sleep(3)  # даём вкладке загрузиться и расширению обработать profile_id
            driver.switch_to.window(driver.window_handles[-1])
            print(f"[.] Открыт лаунчер с profile_id={profile_id}")

            # Время на работу с профилем (расширение активно, браузер открыт)
            print(f"[...] Браузер открыт {PROFILE_DELAY} сек - можно пользоваться расширением...")
            time.sleep(PROFILE_DELAY)

        except Exception as e:
            print(f"[X] Ошибка при работе с профилем {profile_name}: {e}")

        finally:
            # Закрываем браузер
            if driver:
                driver.quit()
                print(f"[.] Selenium закрыт")
            try:
                gl.stop()
                print(f"[.] Профиль остановлен")
            except:
                pass

            # Задержка перед следующим профилем
            if idx < len(profiles):
                print(f"[...] Ожидание {PROFILE_DELAY} сек перед следующим профилем...")
                time.sleep(PROFILE_DELAY)

    print("[OK] Все профили обработаны: расширения включены!")
