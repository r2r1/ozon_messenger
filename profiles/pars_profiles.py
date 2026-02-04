import requests
import json
import time

# === НАСТРОЙКИ ===
API_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI2OTdjY2IzNmI3MWE0Njg0MWUzNGRhYTciLCJ0eXBlIjoiZGV2Iiwiand0aWQiOiI2OTdjZDUxMWUzMGE5OWU4NmVlNTM5ZTMifQ.3N3hPO6EsoAk_utpQSMoxJtbiKLGyw3DmTF0jbJLcwk"
BASE_URL = "https://api.gologin.com"  # Убран лишний пробел!

def get_all_profiles_minimal():
    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "User-Agent": "Gologin-Minimal/1.0",
    }

    minimal_profiles = []  # Список для хранения профилей
    seen_ids = set()       # Множество для отслеживания уже добавленных ID
    page = 0
    limit = 30

    print("🔄 Загружаем профили постранично...")

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

                added_count = 0
                for profile in profiles:
                    pid = profile.get("id")
                    if not pid:
                        continue  # Пропускаем, если нет ID

                    if pid not in seen_ids:
                        seen_ids.add(pid)
                        minimal_profiles.append({
                            "id": pid,
                            "name": profile.get("name", "Без имени")
                        })
                        added_count += 1

                print(f"✅ Страница {page}: получено {len(profiles)} профилей, добавлено {added_count} новых")

                if len(profiles) < limit:
                    break  # Последняя страница

                page += 1
                time.sleep(0.3)

            elif response.status_code == 401:
                print("❌ Ошибка авторизации: проверь API токен.")
                break
            else:
                print(f"❌ Ошибка {response.status_code}: {response.text}")
                break

        except requests.exceptions.RequestException as e:
            print(f"🌐 Ошибка запроса: {e}")
            break

    return minimal_profiles

# === Запуск ===
if __name__ == "__main__":
    profiles = get_all_profiles_minimal()

    print(f"\n📋 Всего получено уникальных профилей: {len(profiles)}")
    print("🔹 Формат: {id, name}\n")

    # Выводим первые 10
    for p in profiles[:10]:
        print(f"• ID: {p['id']} | Name: {p['name']}")

    if len(profiles) > 10:
        print(f"... и ещё {len(profiles) - 10} профилей.")

    # Сохраняем в файл
    output_path = "profiles/data/profiles.json"
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Сохранено в '{output_path}'")