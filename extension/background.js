// background.js
let processing = false;
let currentTabId = null;

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.action === 'startMessaging') {
    startMessaging(msg.config, sender.tab?.id);
  } else if (msg.action === 'messageSent') {
    handleNextSeller(sender.tab.id);
  }
  sendResponse({});
});

async function startMessaging(config, tabId) {
  if (processing) return;
  processing = true;

  await chrome.storage.local.set({
    ozon_seller_messenger: { ...config, currentIndex: 0 }
  });

  // Извлекаем slug или ID — в зависимости от того, что введено
  const firstTarget = config.targets[0];
  const url = `https://ozon.ru/seller/${firstTarget}/`;

  if (config.openInNewTab) {
    const newTab = await chrome.tabs.create({ url });
    currentTabId = newTab.id;
  } else {
    if (tabId) {
      await chrome.tabs.update(tabId, { url });
      currentTabId = tabId;
    } else {
      const newTab = await chrome.tabs.create({ url });
      currentTabId = newTab.id;
    }
  }
}

async function handleNextSeller(tabId) {
  if (tabId !== currentTabId) return;

  const data = await chrome.storage.local.get(['ozon_seller_messenger']);
  const config = data.ozon_seller_messenger;

  if (!config) {
    processing = false;
    return;
  }

  const nextIndex = config.currentIndex + 1;
  if (nextIndex >= config.targets.length) {
    // Завершено
    chrome.tabs.sendMessage(tabId, { action: 'showStatus', status: 'done' }).catch(() => {});
    await chrome.storage.local.remove('ozon_seller_messenger');
    processing = false;
    return;
  }

  await chrome.storage.local.set({
    ozon_seller_messenger: { ...config, currentIndex: nextIndex }
  });

  const nextUrl = `https://ozon.ru/seller/${config.targets[nextIndex]}/`;
  if (config.openInNewTab) {
    const newTab = await chrome.tabs.create({ url: nextUrl });
    currentTabId = newTab.id;
  } else {
    await chrome.tabs.update(tabId, { url: nextUrl });
  }
}