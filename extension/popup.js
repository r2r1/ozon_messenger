(function () {
  const SHOP_PAIRS = [
    { name: 'name1', id: 'id1' },
    { name: 'name2', id: 'id2' },
    { name: 'name3', id: 'id3' },
    { name: 'name4', id: 'id4' },
    { name: 'name5', id: 'id5' }
  ];
  const STORAGE_KEY = 'ozon_seller_messenger';

  // Превращает "Smart Shop" → "smart-shop"
  function slugify(text) {
    return text
      .toLowerCase()
      .trim()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  // Собирает slug'и из пар название + ID
  function getShopSlugs() {
    const slugs = [];
    for (const pair of SHOP_PAIRS) {
      const nameVal = document.getElementById(pair.name).value.trim();
      const idVal = document.getElementById(pair.id).value.trim();

      if (!nameVal && !idVal) continue;

      if (!idVal) {
        alert(`Укажите ID магазина для строки с названием: "${nameVal || 'без названия'}"`);
        return null;
      }

      if (!/^\d+$/.test(idVal)) {
        alert(`ID должен содержать только цифры. Некорректный ID: "${idVal}"`);
        return null;
      }

      const slug = nameVal ? `${slugify(nameVal)}-${idVal}` : idVal;
      slugs.push(slug);
    }
    return slugs;
  }

  // Отображает статус
  function setStatus(text, isError = false) {
    const el = document.getElementById('status');
    if (el) {
      el.textContent = text;
      el.className = `status ${isError ? 'error' : 'ok'}`;
      el.style.display = 'block';
    }
  }

  // 🔥 НОВАЯ ФУНКЦИЯ: Разбор bulk-ввода
  function parseBulkInput() {
    const bulkText = document.getElementById('bulkInput')?.value.trim();
    if (!bulkText) {
      setStatus('Поле ввода пустое', true);
      return;
    }

    const lines = bulkText.split('\n');
    const pairs = [];

    for (let line of lines) {
      line = line.trim();
      if (!line) continue;

      let parts;
      if (line.includes('\t')) {
        parts = line.split('\t');
      } else if (line.includes(',')) {
        parts = line.split(',');
      } else {
        parts = line.split(/\s{2,}/);
      }

      parts = parts.map(p => p.trim()).filter(p => p);

      if (parts.length === 0) continue;

      if (parts.length === 1) {
        const id = parts[0];
        if (/^\d+$/.test(id)) {
          pairs.push({ name: '', id });
        } else {
          setStatus(`Некорректный ID в строке: "${line}"`, true);
          return;
        }
      } else if (parts.length >= 2) {
        const name = parts[0];
        const id = parts[1];
        if (!/^\d+$/.test(id)) {
          setStatus(`ID должен быть числом в строке: "${line}"`, true);
          return;
        }
        pairs.push({ name, id });
      }
    }

    const limitedPairs = pairs.slice(0, 5);

    // Очищаем поля
    for (let i = 1; i <= 5; i++) {
      document.getElementById(`name${i}`).value = '';
      document.getElementById(`id${i}`).value = '';
    }

    // Заполняем
    limitedPairs.forEach((pair, index) => {
      if (index < 5) {
        document.getElementById(`name${index + 1}`).value = pair.name;
        document.getElementById(`id${index + 1}`).value = pair.id;
      }
    });

    setStatus(`✅ Успешно загружено ${limitedPairs.length} магазинов`, false);
  }

  // Обработчик кнопки "Разобрать"
  const parseBtn = document.getElementById('parseBtn');
  if (parseBtn) {
    parseBtn.addEventListener('click', parseBulkInput);
  }

  // Ctrl+Enter в bulk-поле
  const bulkInput = document.getElementById('bulkInput');
  if (bulkInput) {
    bulkInput.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.key === 'Enter') {
        e.preventDefault();
        parseBulkInput();
      }
    });
  }

  // Обработчик отправки формы
  document.getElementById('submitBtn').addEventListener('click', async function (e) {
    e.preventDefault();
    const slugs = getShopSlugs();
    if (!slugs) return;

    if (slugs.length === 0) {
      setStatus('Добавьте хотя бы один магазин.', true);
      return;
    }

    const message1 = document.getElementById('message1')?.value.trim() || 'Здравствуйте! Интересует сотрудничество.';
    const message2 = document.getElementById('message2')?.value.trim() || 'Мы ищем поставщиков для нашего маркетплейса.';
    const message3 = document.getElementById('message3')?.value.trim() || 'Готовы обсудить детали?';

    const messages = [message1, message2, message3];
    const openInNewTab = document.getElementById('newTab')?.checked ?? true;

    await chrome.storage.local.set({
      [STORAGE_KEY]: {
        shopSlugs: slugs,
        currentIndex: 0,
        messages: messages,
        openInNewTab: openInNewTab
      }
    });

    setStatus('Открываю первый магазин…', false);

    // 🔥 ИСПРАВЛЕНО: убраны лишние пробелы в URL!
    const url = `https://ozon.ru/seller/${slugs[0]}/`;

    if (openInNewTab) {
      chrome.tabs.create({ url });
    } else {
      chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0]) {
          chrome.tabs.update(tabs[0].id, { url });
        } else {
          chrome.tabs.create({ url });
        }
      });
    }
  });

  // Восстановление данных
  chrome.storage.local.get([STORAGE_KEY], function (data) {
    const saved = data[STORAGE_KEY];
    if (saved && Array.isArray(saved.shopSlugs)) {
      saved.shopSlugs.forEach((slug, i) => {
        if (i >= SHOP_PAIRS.length) return;

        let namePart = '';
        let idPart = slug;

        const lastDashIndex = slug.lastIndexOf('-');
        if (lastDashIndex > 0 && /^\d+$/.test(slug.slice(lastDashIndex + 1))) {
          idPart = slug.slice(lastDashIndex + 1);
          namePart = slug.slice(0, lastDashIndex)
            .split('-')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
        }

        document.getElementById(SHOP_PAIRS[i].name).value = namePart;
        document.getElementById(SHOP_PAIRS[i].id).value = idPart;
      });

      if (saved.messages && Array.isArray(saved.messages)) {
        if (saved.messages[0]) document.getElementById('message1').value = saved.messages[0];
        if (saved.messages[1]) document.getElementById('message2').value = saved.messages[1];
        if (saved.messages[2]) document.getElementById('message3').value = saved.messages[2];
      }

      if (document.getElementById('newTab')) {
        document.getElementById('newTab').checked = !!saved.openInNewTab;
      }
    }
  });
})();