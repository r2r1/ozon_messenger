
import time
import json
import os
from gologin import GoLogin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# --- Настройки ---
PROFILES_FILE = "profiles/data/profiles.json"          # Путь к списку профилей
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTdjY2IzNmI3MWE0Njg0MWUzNGRhYTciLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2OTdjZDUxMWUzMGE5OWU4NmVlNTM5ZTMifQ.3N3hPO6EsoAk_utpQSMoxJtbiKLGyw3DmTF0jbJLcwk"                      # Твой токен Gologin
EXTENSION_ID = "kbfaaeambikahofikckfpgfplggifdlh"                # ID расширения, например: "padekgcemlokbadohgkifijomclgjgif"
DELAY_BEFORE_ACTION = 5                                # Задержка перед действиями (сек)
DELAY_AFTER_ENABLE = 3                                 # Задержка после включения расширения (сек)
PROFILE_DELAY = 15                                     # Время на работу с одним профилем (браузер открыт)
PAGE_FOR_EXTENSION = "https://www.ozon.ru/"            # Страница, на которой работает расширение

def read_profiles(filepath):
    """Читает список профилей из JSON"""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else data.get("profiles", [])
    except Exception as e:
        print(f"❌ Ошибка чтения файла: {e}")
        return []

if __name__ == "__main__":
    # Проверка токена
    if API_TOKEN == "your_api_token_here":
        print("❗ Укажи API токен в коде!")
        exit(1)
    if EXTENSION_ID == "your_extension_id_here":
        print("❗ Укажи ID расширения!")
        exit(1)

    profiles = read_profiles(PROFILES_FILE)
    if not profiles:
        print("❌ Нет профилей для обработки.")
        exit(1)

    print(f"📁 Найдено профилей: {len(profiles)}\n")

    for idx, profile in enumerate(profiles, start=1):
        profile_id = profile.get("id")
        profile_name = profile.get("name", "Без имени")

        if not profile_id:
            print(f"{idx}. ⚠️ Пропущен: нет ID")
            continue

        print(f"\n➡️ {idx}. Обработка профиля: {profile_name} (ID: {profile_id})")

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
            print(f"✅ Браузер запущен")

            # Настройка Selenium
            service = Service(ChromeDriverManager().install())
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_experimental_option("debuggerAddress", debugger_address)

            driver = webdriver.Chrome(service=service, options=chrome_options)
            print(f"🔗 Selenium подключён")

            # Открываем страницу расширений
            driver.get("chrome://extensions/")
            time.sleep(DELAY_BEFORE_ACTION)

            # Активируем расширение через JavaScript
            enable_script = """
            const extensions = document.querySelector('extensions-manager')
                .shadowRoot.querySelector('#items-list')
                .querySelectorAll('extensions-item');

            for (let ext of extensions) {
                if (ext.getAttribute('id') === '%s') {
                    const toggle = ext.shadowRoot.querySelector('#enabled');
                    if (!toggle.checked) {
                        toggle.click();  // Включаем
                        console.log('✅ Расширение включено:', '%s');
                    } else {
                        console.log('🟢 Расширение уже активно:', '%s');
                    }
                    return true;
                }
            }
            console.log('🔴 Расширение не найдено:', '%s');
            return false;
            """ % (EXTENSION_ID, EXTENSION_ID, EXTENSION_ID, EXTENSION_ID)

            result = driver.execute_script(enable_script)
            if result is False:
                print(f"❌ Расширение с ID={EXTENSION_ID} не найдено в профиле")
            else:
                print(f"✨ Расширение активировано: {EXTENSION_ID}")

            # Задержка после включения расширения
            time.sleep(DELAY_AFTER_ENABLE)

            # Открываем вкладку, на которой работает расширение (Ozon)
            driver.execute_script("window.open(arguments[0], '_blank');", PAGE_FOR_EXTENSION)
            time.sleep(2)  # даём вкладке загрузиться
            # Переключаемся на новую вкладку
            driver.switch_to.window(driver.window_handles[-1])
            print(f"🌐 Открыта страница: {PAGE_FOR_EXTENSION}")

            # Время на работу с профилем (расширение активно, браузер открыт)
            print(f"⏳ Браузер открыт {PROFILE_DELAY} сек — можно пользоваться расширением...")
            time.sleep(PROFILE_DELAY)

        except Exception as e:
            print(f"❌ Ошибка при работе с профилем {profile_name}: {e}")

        finally:
            # Закрываем браузер
            if driver:
                driver.quit()
                print(f"🛑 Selenium закрыт")
            try:
                gl.stop()
                print(f"⏹️ Профиль остановлен")
            except:
                pass

            # Задержка перед следующим профилем
            if idx < len(profiles):
                print(f"⏳ Ожидание {PROFILE_DELAY} сек перед следующим профилем...")
                time.sleep(PROFILE_DELAY)

    print("🎉 Все профили обработаны: расширения включены!")
