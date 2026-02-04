import requests
import json
import time
import os

# === НАСТРОЙКИ ===
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTdjY2IzNmI3MWE0Njg0MWUzNGRhYTciLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2OTdjZDUxMWUzMGE5OWU4NmVlNTM5ZTMifQ.3N3hPO6EsoAk_utpQSMoxJtbiKLGyw3DmTF0jbJLcwk"
BASE_URL = "https://api.gologin.com"

def get_all_profiles_full():
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "User-Agent": "Gologin-Full-Export/1.0",
    }

    all_profiles = []  # Теперь храним полные объекты профилей
    page = 0
    limit = 30

    print("🔄 Загружаем ВСЕ профили постранично...")

    while True:
        try:
            url = f"{BASE_URL}/browser/v2?page={page}&limit={limit}"
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                profiles = data.get("profiles", [])

                if not profiles:
                    print(f"🔚 Нет данных на странице {page}. Завершаем.")
                    break

                # Добавляем ПОЛНЫЕ профили в список
                all_profiles.extend(profiles)

                print(f"✅ Страница {page}: добавлено {len(profiles)} профилей (всего: {len(all_profiles)})")

                if len(profiles) < limit:
                    break  # Последняя страница

                page += 1
                time.sleep(0.3)  # Уважаем API

            elif response.status_code == 401:
                print("❌ Ошибка авторизации: проверь API токен.")
                break
            else:
                print(f"❌ Ошибка {response.status_code}: {response.text}")
                break

        except requests.exceptions.RequestException as e:
            print(f"🌐 Ошибка запроса: {e}")
            break

    return all_profiles

# === Запуск ===
if __name__ == "__main__":
    profiles = get_all_profiles_full()

    print(f"\n📋 Всего получено профилей: {len(profiles)}")

    # Создаём папку, если её нет
    output_dir = "full_profiles"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "profiles.json")

    # Сохраняем ВСЕ данные
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Полные данные сохранены в: {output_path}")