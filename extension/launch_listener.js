/**
 * Content script для страницы launch.html.
 * Получает profile_id из URL, загружает продавцов из profiles_with_sellers.json
 * по этому id и запускает рассылку расширения (открывает первого продавца и пишет в storage).
 */
(function () {
  const PROFILES_SELLERS_URL = 'http://localhost:8080/profiles_with_sellers.json';
  const STORAGE_KEY = 'ozon_seller_messenger';
  const DEFAULT_MESSAGES = [
    'Здравствуйте! Продaю кaрточки для склейки — с их помощью можно добaвить 1 000, 2 000 и даже 10 000 отзывов к вашей текущей или новой карточке',
    'Цена — 75 рублей за один отзыв. То есть, покупая 1 000 отзывов, вы оплачиваете 75 000 рублей, а получаете актив, который приносит от миллиона чистыми в месяц',
    'Оплата отзывов после, заранее ничего платить не нужно! \n\
        Связаться со мной можно в \n\
        тг: dousmyd  \n\
        (проведем видео-конференцию при необходимости)'
  ];

  function setStatus(text, isError) {
    const el = document.getElementById('status');
    if (el) {
      el.textContent = text;
      el.style.color = isError ? '#c00' : '#070';
    }
  }

  function getProfileIdFromUrl() {
    const params = new URLSearchParams(window.location.search);
    return (params.get('profile_id') || '').trim();
  }

  async function loadSellersForProfile(profileId) {
    if (!profileId) return null;
    try {
      const response = await fetch(PROFILES_SELLERS_URL);
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const data = await response.json();
      const row = Array.isArray(data)
        ? data.find((r) => (r.id || '').toString().trim() === profileId)
        : null;
      if (!row || !Array.isArray(row.sellers)) return null;
      // Только первые 5 продавцов по профилю — после них рассылка останавливается
      return row.sellers
        .map((s) => String(s.seller_id || '').trim())
        .filter(Boolean)
        .slice(0, 5);
    } catch (err) {
      console.error('[Launch] Ошибка загрузки profiles_with_sellers.json:', err);
      return null;
    }
  }

  async function run() {
    const profileId = getProfileIdFromUrl();
    if (!profileId) {
      setStatus('В URL не указан profile_id (например: ?profile_id=xxx)', true);
      return;
    }

    setStatus('Загрузка продавцов по профилю ' + profileId + '…', false);
    const shopSlugs = await loadSellersForProfile(profileId);

    if (!shopSlugs || shopSlugs.length === 0) {
      setStatus('Для профиля "' + profileId + '" продавцы не найдены в profiles_with_sellers.json', true);
      return;
    }

    const config = {
      shopSlugs: shopSlugs,
      currentIndex: 0,
      messages: DEFAULT_MESSAGES,
      openInNewTab: true
    };

    setStatus('Передача данных в расширение: ' + shopSlugs.length + ' продавцов…', false);
    try {
      chrome.runtime.sendMessage(
        {
          action: 'startFromLaunch',
          config: {
            shopSlugs: config.shopSlugs,
            messages: config.messages,
            openInNewTab: config.openInNewTab
          }
        },
        (response) => {
          if (chrome.runtime.lastError) {
            setStatus('Ошибка: ' + chrome.runtime.lastError.message, true);
            return;
          }
          setStatus('Рассылка запущена. Вкладку можно закрыть.', false);
        }
      );
    } catch (e) {
      setStatus('Ошибка передачи в расширение: ' + e.message, true);
    }
  }

  run();
})();
