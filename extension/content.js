// content.js
(function () {
  const STORAGE_KEY = 'ozon_seller_messenger';
  console.log('[DEBUG] content.js загружен на:', window.location.href);
  
  function getStorage() {
    return new Promise(resolve => {
      chrome.storage.local.get([STORAGE_KEY], data => {
        resolve(data[STORAGE_KEY] || null);
      });
    });
  }
  
  function setStorage(obj) {
    return new Promise(resolve => {
      chrome.storage.local.set({ [STORAGE_KEY]: obj }, resolve);
    });
  }
  
  function clearStorage() {
    chrome.storage.local.remove(STORAGE_KEY);
  }
  
  // 🔁 Генерация случайной задержки в диапазоне [min, max] миллисекунд
  function randomDelay(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }
  
  function sleep(ms) {
    return new Promise(r => setTimeout(r, ms));
  }
  
  function isElementVisible(el) {
    if (!el || !(el instanceof Element)) return false;
    const style = getComputedStyle(el);
    return (
      el.offsetParent !== null &&
      style.visibility !== 'hidden' &&
      style.opacity !== '0' &&
      el.offsetWidth > 0 &&
      el.offsetHeight > 0
    );
  }
  
  // 🔴 НОВАЯ ФУНКЦИЯ: Поиск кнопки "Всё равно отправить"
  function findSendAnywayButton() {
    const buttons = document.querySelectorAll('button.om_3_p, button[class*="b25_5_3"]');
    for (const btn of buttons) {
      if (!isElementVisible(btn)) continue;
      
      // Ищем по тексту внутри кнопки
      const buttonText = btn.textContent?.trim() || '';
      if (buttonText.includes('Всё равно отправить') || buttonText.includes('отправить')) {
        return btn;
      }
      
      // Или по структуре: ищем div с текстом
      const textDiv = btn.querySelector('.b25_5_3-a9, [class*="tsBodyControl"]');
      if (textDiv && textDiv.textContent?.includes('Всё равно отправить')) {
        return btn;
      }
    }
    return null;
  }
  
  // 🔴 НОВАЯ ФУНКЦИЯ: Ожидание появления кнопки "Всё равно отправить"
  function waitForSendAnywayButton(maxWaitMs = 5000) {
    const start = Date.now();
    return new Promise(resolve => {
      function check() {
        const btn = findSendAnywayButton();
        if (btn) {
          return resolve(btn);
        }
        if (Date.now() - start > maxWaitMs) {
          return resolve(null);
        }
        setTimeout(check, 300);
      }
      check();
    });
  }
  
  function findWriteButton() {
    const buttons = document.querySelectorAll('button, a, [role="button"]');
    for (const btn of buttons) {
      if (!isElementVisible(btn)) continue;
      const text = (btn.textContent || '').trim().toLowerCase();
      if (text.includes('написать') && !text.includes('отправ')) {
        return btn;
      }
    }
    return null;
  }
  
  function waitForChatInput(maxWaitMs = 15000) {
    const start = Date.now();
    return new Promise(resolve => {
      function check() {
        const textareas = document.querySelectorAll('textarea');
        for (const el of textareas) {
          if (isElementVisible(el)) {
            // Проверяем по контексту: рядом есть "Введите сообщение"?
            const sibling = el.nextElementSibling;
            if (sibling && sibling.textContent?.trim() === 'Введите сообщение') {
              return resolve(el);
            }
            // Или родительский контейнер похож на чат
            if (el.closest('[class*="om_"]') && el.offsetHeight >= 15) {
              return resolve(el);
            }
          }
        }
        if (Date.now() - start > maxWaitMs) return resolve(null);
        setTimeout(check, 400);
      }
      check();
    });
  }
  
  function setInputValue(el, value) {
    el.value = value;
    el.textContent = value;
    el.focus();
    el.dispatchEvent(new Event('input', { bubbles: true }));
  }
  
  function sendMessage(inputEl) {
    console.log('[Content] Значение перед отправкой:', inputEl.value);
    
    const chatContainer = inputEl.closest('.om_17_n8') || inputEl.closest('[class*="om_17_n"]') || inputEl.parentElement;
    if (!chatContainer) {
      console.error('[Content] ❌ Не найден контейнер чата');
      return false;
    }
    
    const sendButtons = Array.from(chatContainer.querySelectorAll('button.om_17_o'));
    if (sendButtons.length === 0) {
      console.error('[Content] ❌ Нет кнопок отправки');
      return false;
    }
    
    const sendBtn = sendButtons[sendButtons.length - 1];
    
    if (!isElementVisible(sendBtn)) {
      console.error('[Content] ❌ Кнопка отправки не видима');
      return false;
    }
    if (sendBtn.disabled) {
      console.error('[Content] ❌ Кнопка отправки disabled');
      return false;
    }
    
    console.log('[Content] ✅ Отправляем сообщение');
    sendBtn.click();
    return true;
  }
  

  function getCurrentSellerSlug() {
  const match = window.location.pathname.match(/^\/seller\/([^\/]+)/);
  return match ? match[1] : null;
}

async function getSentSlugs() {
  const data = await new Promise(resolve => {
    chrome.storage.local.get(['ozon_seller_messenger_sent'], resolve);
  });
  return data.ozon_seller_messenger_sent || [];
}

async function addSentSlug(slug) {
  const sentSlugs = await getSentSlugs();
  if (!sentSlugs.includes(slug)) {
    sentSlugs.push(slug);
    await new Promise(resolve => {
      chrome.storage.local.set({ ozon_seller_messenger_sent: sentSlugs }, resolve);
    });
  }
}


function isMessagingBlocked() {
  const phrases = [
    'Этому продавцу пока нельзя написать',
    'нельзя написать',
    'сообщения недоступны',
    'чат недоступен',
    'недоступен для связи'
  ];
  const text = (document.body?.innerText || '').toLowerCase();
  return phrases.some(p => text.includes(p.toLowerCase()));
}



async function run() {
  const config = await getStorage();
  if (!config || !Array.isArray(config.shopSlugs) || !config.shopSlugs.length) {
    console.log('[Content] Нет конфига — выход');
    return;
  }

  const idx = config.currentIndex != null ? config.currentIndex : 0;
  if (idx >= config.shopSlugs.length) {
    console.log('[Content] 🎉 Рассылка завершена');
    clearStorage();
    alert('✅ Рассылка завершена!');
    return;
  }

  // 🔑 Используем slug из конфига (как при переходе)
  const slugFromConfig = (config.shopSlugs[idx] || '').toString().trim();
  if (!slugFromConfig) {
    console.error('[Content] ❌ Пустой slug на позиции', idx);
    const nextIndex = idx + 1;
    if (nextIndex >= config.shopSlugs.length) {
      console.log('[Content] 🎉 Рассылка завершена');
      clearStorage();
      alert('✅ Рассылка завершена!');
      return;
    }
    await setStorage({
      shopSlugs: config.shopSlugs,
      currentIndex: nextIndex,
      messages: config.messages,
      openInNewTab: config.openInNewTab
    });
    const nextUrl = `https://ozon.ru/seller/${(config.shopSlugs[nextIndex] || '').toString().trim()}/`;
    if (config.openInNewTab) {
      window.open(nextUrl, '_blank');
      await sleep(1000);
      window.close();
    } else {
      window.location.href = nextUrl;
    }
    return;
  }

  // 🔐 Проверка: уже отправляли этому продавцу?
  const sentSlugsData = await new Promise(resolve => {
    chrome.storage.local.get(['ozon_seller_messenger_sent'], resolve);
  });
  const sentSlugs = sentSlugsData.ozon_seller_messenger_sent || [];

  if (sentSlugs.includes(slugFromConfig)) {
    console.log(`[Content] ℹ️ Продавец "${slugFromConfig}" уже обработан. Пропускаем.`);
    const nextIndex = idx + 1;
    if (nextIndex >= config.shopSlugs.length) {
      console.log('[Content] 🎉 Рассылка завершена');
      clearStorage();
      alert('✅ Рассылка завершена!');
      return;
    }
    await setStorage({
      shopSlugs: config.shopSlugs,
      currentIndex: nextIndex,
      messages: config.messages,
      openInNewTab: config.openInNewTab
    });
    const nextUrl = `https://ozon.ru/seller/${(config.shopSlugs[nextIndex] || '').toString().trim()}/`;
    console.log('[Content] ➡️ Переход к следующему (уже отправляли):', nextUrl);
    if (config.openInNewTab) {
      window.open(nextUrl, '_blank');
      await sleep(1000);
      window.close();
    } else {
      window.location.href = nextUrl;
    }
    return;
  }

  // --- ОСНОВНАЯ ЛОГИКА ОТПРАВКИ ---

  const messages = config.messages || [
    'Здравствуйте! Интересует сотрудничество.',
    'Мы ищем поставщиков для нашего маркетплейса.',
    'Готовы обсудить детали?'
  ];

  // 1. Ждём загрузки страницы
  await sleep(randomDelay(2000, 3500));

  // 🔒 Проверяем, недоступен ли чат
  if (isMessagingBlocked()) {
    console.log('[Content] ⚠️ Этому продавцу нельзя написать. Пропускаем.');
    const nextIndex = idx + 1;
    if (nextIndex >= config.shopSlugs.length) {
      console.log('[Content] 🎉 Рассылка завершена');
      clearStorage();
      alert('✅ Рассылка завершена!');
      return;
    }
    await setStorage({
      shopSlugs: config.shopSlugs,
      currentIndex: nextIndex,
      messages: config.messages,
      openInNewTab: config.openInNewTab
    });
    const nextUrl = `https://ozon.ru/seller/${(config.shopSlugs[nextIndex] || '').toString().trim()}/`;
    console.log('[Content] ➡️ Переход к следующему (чат недоступен):', nextUrl);
    if (config.openInNewTab) {
      window.open(nextUrl, '_blank');
      await sleep(1000);
      window.close();
    } else {
      window.location.href = nextUrl;
    }
    return;
  }

  // 2. Ищем и кликаем "Написать"
  const btn = findWriteButton();
  if (!btn) {
    console.error('[Content] ❌ Кнопка "Написать" не найдена');
}
  if (btn) {
    console.log('[Content] ✅ Нашли кнопку "Написать"');
    btn.click();
    console.log('[Content] ✅ Нажали кнопку "Написать"');
  }
  // 3. Ждём появления поля чата
  await sleep(randomDelay(2000, 3500));
  const inputEl = await waitForChatInput(15000);
  if (!inputEl) {
    console.error('[Content] ❌ Поле ввода чата не найдено — пропускаем продавца');
    const nextIndex = idx + 1;
    if (nextIndex >= config.shopSlugs.length) {
      console.log('[Content] 🎉 Рассылка завершена');
      clearStorage();
      alert('✅ Рассылка завершена!');
      return;
    }
    await setStorage({
      shopSlugs: config.shopSlugs,
      currentIndex: nextIndex,
      messages: config.messages,
      openInNewTab: config.openInNewTab
    });
    const nextUrl = `https://ozon.ru/seller/${(config.shopSlugs[nextIndex] || '').toString().trim()}/`;
    console.log('[Content] ➡️ Переход к следующему (поле чата не найдено):', nextUrl);
    if (config.openInNewTab) {
      window.open(nextUrl, '_blank');
      await sleep(1000);
      window.close();
    } else {
      window.location.href = nextUrl;
    }
    return;
  }
  console.log('[Content] ✅ Нашли поле ввода чата');

  // 4. Отправляем сообщения
  for (let i = 0; i < messages.length; i++) {
    const message = messages[i];
    setInputValue(inputEl, message);
    console.log(`[Content] ✅ Ввели сообщение ${i + 1}/${messages.length}:`, message);
    await sleep(randomDelay(1500, 2500));
    const sent = sendMessage(inputEl);
    if (!sent) {
      console.error(`[Content] ❌ Не удалось отправить сообщение ${i + 1}`);
      break;
    }
    console.log(`[Content] ✅ Отправлено сообщение ${i + 1}/${messages.length}`);
    if (i < messages.length - 1) {
      await sleep(randomDelay(3000, 5000));
    }
  }

  // 5. Ждём и нажимаем "Всё равно отправить"
  console.log('[Content] ⏳ Ждём появления кнопки "Всё равно отправить"...');
  await sleep(randomDelay(1500, 2500));
  const sendAnywayBtn = await waitForSendAnywayButton(5000);
  if (sendAnywayBtn) {
    console.log('[Content] ✅ Нашли кнопку "Всё равно отправить"');
    sendAnywayBtn.click();
    console.log('[Content] ✅ Нажали кнопку "Всё равно отправить"');
    await sleep(randomDelay(1500, 2500));
  } else {
    console.log('[Content] ℹ️ Кнопка "Всё равно отправить" не появилась');
  }

  // 6. Финальная пауза
  await sleep(randomDelay(3000, 4500));

  // ✅ Помечаем как обработанного
  const updatedSentSlugs = [...new Set([...sentSlugs, slugFromConfig])];
  await new Promise(resolve => {
    chrome.storage.local.set({ ozon_seller_messenger_sent: updatedSentSlugs }, resolve);
  });
  console.log(`[Content] ✅ Продавец "${slugFromConfig}" добавлен в список отправленных`);

  // 7. Переход к следующему
  const nextIndex = idx + 1;
  if (nextIndex >= config.shopSlugs.length) {
    console.log('[Content] 🎉 Рассылка завершена');
    clearStorage();
    alert('✅ Рассылка завершена!');
    return;
  }

  await setStorage({
    shopSlugs: config.shopSlugs,
    currentIndex: nextIndex,
    messages: config.messages,
    openInNewTab: config.openInNewTab
  });

  const nextSlug = (config.shopSlugs[nextIndex] || '').toString().trim();
  const nextUrl = `https://ozon.ru/seller/${nextSlug}/`;
  console.log('[Content] ➡️ Переход к следующему магазину:', nextUrl);

  if (config.openInNewTab) {
    window.open(nextUrl, '_blank');
    await sleep(1000);
    window.close();
  } else {
    window.location.href = nextUrl;
  }
}





  // Запуск
  getStorage().then(config => {
    if (config && config.shopSlugs && config.shopSlugs.length) {
      console.log('[Content] Конфиг обнаружен — запускаем');
      run();
    } else {
      console.log('[Content] Нет активной рассылки');
    }
  });
})();