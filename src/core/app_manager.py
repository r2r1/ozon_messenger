import logging
import re
import threading
import asyncio
import time
from typing import Dict, Any, List, Optional
from ..config.settings import Settings
from ..parsers.link_parser import OzonLinkParser
from ..parsers.product_parser import OzonProductParser
from ..parsers.seller_parser import OzonSellerParser
from ..utils.excel_exporter import ExcelExporter
from ..telegram.bot_manager import TelegramBotManager
from ..utils.resource_manager import resource_manager

logger = logging.getLogger(__name__)

class AppManager:
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.is_running = False  # Глобальный флаг для совместимости
        self.active_parsing_users = set()  # Множество активных пользователей
        self.parsing_lock = threading.RLock()
        self.stop_event = threading.Event()
        self.last_results = {}  # Глобальные результаты для совместимости
        self.user_results = {}  # Результаты по пользователям: {user_id: results}
        self.telegram_bot: Optional[TelegramBotManager] = None
    
    def start_parsing(
        self,
        category_url: str,
        selected_fields: list = None,
        user_id: str = None,
        min_seller_orders: int = 0,
        max_seller_orders: int = 0,
    ) -> bool:
        with self.parsing_lock:
            # Проверяем, не парсит ли уже этот пользователь
            if user_id and user_id in self.active_parsing_users:
                logger.warning(f"Пользователь {user_id} уже запустил парсинг")
                return False
            
            # Добавляем пользователя в активные
            if user_id:
                self.active_parsing_users.add(user_id)
            
            # Устанавливаем глобальный флаг для первого пользователя
            if not self.is_running:
                self.stop_event.clear()
                self.is_running = True
        
        try:
            # Запускаем парсинг в отдельном потоке
            parsing_thread = threading.Thread(
                target=self._parsing_task_wrapper,
                args=(category_url, selected_fields, user_id, int(min_seller_orders or 0), int(max_seller_orders or 0)),
                daemon=True
            )
            parsing_thread.start()
            return True
        except Exception as e:
            logger.error(f"Ошибка запуска парсинга для пользователя {user_id}: {e}")
            # Убираем пользователя из активных при ошибке
            with self.parsing_lock:
                if user_id and user_id in self.active_parsing_users:
                    self.active_parsing_users.remove(user_id)
                # Если это был последний пользователь, сбрасываем глобальный флаг
                if not self.active_parsing_users:
                    self.is_running = False
            return False
    
    def _parsing_task_wrapper(
        self,
        category_url: str,
        selected_fields: list = None,
        user_id: str = None,
        min_seller_orders: int = 0,
        max_seller_orders: int = 0,
    ):
        """Wrapper для парсинга с правильной очисткой ресурсов"""
        try:
            self._parsing_task(category_url, selected_fields, user_id, int(min_seller_orders or 0), int(max_seller_orders or 0))
        except Exception as e:
            logger.error(f"Ошибка в парсинге для пользователя {user_id}: {e}")
        finally:
            # Убираем пользователя из активных
            with self.parsing_lock:
                if user_id and user_id in self.active_parsing_users:
                    self.active_parsing_users.remove(user_id)
                    logger.info(f"Пользователь {user_id} завершил парсинг")
                
                # Если это был последний пользователь, сбрасываем глобальный флаг
                if not self.active_parsing_users:
                    self.is_running = False
                    logger.info("Все пользователи завершили парсинг")
    
    def stop_parsing(self, user_id: str = None):
        """Останавливает парсинг для конкретного пользователя или всех"""
        with self.parsing_lock:
            if user_id:
                # Останавливаем парсинг для конкретного пользователя
                if user_id in self.active_parsing_users:
                    self.active_parsing_users.remove(user_id)
                    logger.info(f"Остановлен парсинг для пользователя {user_id}")
            else:
                # Останавливаем все парсинги
                self.active_parsing_users.clear()
                logger.info("Остановлен парсинг для всех пользователей")
            
            # Если нет активных пользователей, сбрасываем глобальный флаг
            if not self.active_parsing_users:
                self.stop_event.set()
                self.is_running = False
    
    def _parsing_task(
        self,
        category_url: str,
        selected_fields: list = None,
        user_id: str = None,
        min_seller_orders: int = 0,
        max_seller_orders: int = 0,
    ):
        # Поля, которые требуют парсинга селлера
        SELLER_FIELDS = {
            'seller_id', 'seller_name', 'seller_link',
            'inn', 'company_name', 'orders_count', 'reviews_count', 'average_rating', 'working_time'
        }
        
        # Проверяем, нужен ли парсинг селлеров
        needs_seller_parsing = False
        if selected_fields:
            needs_seller_parsing = any(field in SELLER_FIELDS for field in selected_fields)
        else:
            # Если поля не указаны, по умолчанию парсим селлеров
            needs_seller_parsing = True
        
        start_time = time.time()
        
        try:
            # Начинаем сессию парсинга для пользователя
            if user_id:
                resource_manager.start_parsing_session(user_id, 'full_parsing', 0)
            
            link_parser = OzonLinkParser(category_url, self.settings.MAX_PRODUCTS, user_id)
            
            success, product_links = link_parser.start_parsing()
            
            if self.stop_event.is_set():
                return
            
            if not success or not product_links:
                logger.error("Не удалось собрать ссылки товаров")
                return
            
            if self.stop_event.is_set():
                return
            
            product_parser = OzonProductParser(self.settings.MAX_WORKERS, user_id)
            product_results = product_parser.parse_products(product_links)
            
            # Принудительно закрываем все воркеры продуктов перед началом парсинга продавцов
            product_parser.cleanup()
            
            if self.stop_event.is_set():
                return
            
            seller_results = []
            # Метаданные селлера (имя/ссылка) можно достать из карточек товаров
            seller_meta: Dict[str, Dict[str, str]] = {}
            
            if needs_seller_parsing:
                seller_ids = []
                total_products = len(product_results)
                successful_products = len([p for p in product_results if p.success])
                products_with_seller_id = 0
                
                for product in product_results:
                    if product.success:
                        if product.seller_id:
                            seller_ids.append(product.seller_id)
                            products_with_seller_id += 1

                            if product.seller_id not in seller_meta:
                                seller_meta[product.seller_id] = {
                                    'seller_name': product.company_name or '',
                                    'seller_link': product.seller_link or (f"https://ozon.ru/seller/{product.seller_id}" if product.seller_id else '')
                                }
                            else:
                                # добиваем пустые значения, если появились позже
                                if not seller_meta[product.seller_id].get('seller_name') and product.company_name:
                                    seller_meta[product.seller_id]['seller_name'] = product.company_name
                                if not seller_meta[product.seller_id].get('seller_link') and product.seller_link:
                                    seller_meta[product.seller_id]['seller_link'] = product.seller_link
                        else:
                            logger.warning(f"Товар {product.article} ({product.name[:50]}) не имеет seller_id")
                
                unique_seller_ids = list(set(seller_ids))
                logger.info(f"Статистика seller_id: всего товаров={total_products}, успешных={successful_products}, с seller_id={products_with_seller_id}, уникальных селлеров={len(unique_seller_ids)}")
                
                if unique_seller_ids:
                    logger.info(f"Начинаем парсинг {len(unique_seller_ids)} продавцов (поля: {selected_fields})")
                    seller_parser = OzonSellerParser(self.settings.MAX_WORKERS, user_id)
                    seller_results = seller_parser.parse_sellers(unique_seller_ids)
                    logger.info(f"✓ Парсинг селлеров завершен. Получено: {len(seller_results)}, успешных: {len([s for s in seller_results if s.success])}")
                    # Закрываем воркеры продавцов после завершения
                    seller_parser.cleanup()
                else:
                    logger.info("Нет ID селлеров для парсинга")
            else:
                logger.info(f"Парсинг селлеров пропущен: в selected_fields ({selected_fields}) нет полей селлера")
            
            if self.stop_event.is_set():
                return

            # Фильтрация продавцов по диапазону заказов (max=0 => без верхней границы)
            if (min_seller_orders and min_seller_orders > 0) or (max_seller_orders and max_seller_orders > 0):
                before_count = len(seller_results)
                filtered = []
                for s in seller_results:
                    if not getattr(s, 'success', False):
                        continue
                    orders_int = self._parse_orders_count_to_int(getattr(s, 'orders_count', ''))
                    if min_seller_orders and min_seller_orders > 0 and orders_int < min_seller_orders:
                        continue
                    if max_seller_orders and max_seller_orders > 0 and orders_int > max_seller_orders:
                        continue
                    filtered.append(s)
                seller_results = filtered
                logger.info(f"Фильтр по заказам: min={min_seller_orders}, max={max_seller_orders}, было={before_count}, стало={len(seller_results)}")
            
            seller_data = {}
            for seller in seller_results:
                if seller.success:
                    seller_data[seller.seller_id] = seller
            
            end_time = time.time()
            total_time = end_time - start_time
            successful_products = len([p for p in product_results if p.success])
            failed_products = len([p for p in product_results if not p.success])
            avg_time_per_product = total_time / len(product_results) if product_results else 0
            
            # Сохраняем результаты для конкретного пользователя
            user_results = {
                'links': product_links,
                'products': product_results,
                'sellers': seller_results,
                'category_url': category_url,
                'total_products': len(product_results),
                'successful_products': successful_products,
                'failed_products': failed_products,
                'total_sellers': len(seller_results),
                'successful_sellers': len([s for s in seller_results if s.success]),
                'output_folder': getattr(link_parser, 'output_folder', 'unknown'),
                'seller_data': seller_data,
                'selected_fields': selected_fields,
                'min_seller_orders': int(min_seller_orders or 0),
                'max_seller_orders': int(max_seller_orders or 0),
                'seller_meta': seller_meta,
                'parsing_stats': {
                    'total_time': total_time,
                    'successful_products': successful_products,
                    'failed_products': failed_products,
                    'average_time_per_product': avg_time_per_product
                }
            }
            
            # Сохраняем результаты для пользователя
            if user_id:
                self.user_results[user_id] = user_results
            
            # Обновляем глобальные результаты для совместимости
            self.last_results = user_results
            
            self._save_results_to_file(user_id)
            self._export_to_excel(user_id)
            self._send_report_to_telegram(user_id)
            
        finally:
            # Завершаем сессию парсинга для пользователя
            if user_id:
                resource_manager.finish_parsing_session(user_id)
    

    def _save_results_to_file(self, user_id: str = None):
        """Сохраняет в JSON только те же данные, что и в Excel (продавцы), для автоматизации."""
        try:
            import json
            from datetime import datetime

            results = self.user_results.get(user_id, self.last_results) if user_id else self.last_results
            folder_name = results.get('output_folder', 'unknown')
            output_dir = self.settings.OUTPUT_DIR / folder_name
            filepath = output_dir / f"category_{folder_name}.json"
            output_dir.mkdir(parents=True, exist_ok=True)

            seller_meta = results.get('seller_meta', {}) or {}
            sellers_list = []

            for seller in results.get('sellers', []):
                if not getattr(seller, 'success', False):
                    continue
                sid = getattr(seller, 'seller_id', '')
                meta = seller_meta.get(sid, {}) if sid else {}
                company_name = (getattr(seller, 'company_name', '') or '').replace('\\"', '"').replace('\"', '"').replace('"', '"')
                seller_link = meta.get('seller_link') or (f"https://ozon.ru/seller/{sid}" if sid else "")
                sellers_list.append({
                    'seller_id': sid,
                    'seller_name': (meta.get('seller_name') or '').replace('\\"', '"').replace('\"', '"').replace('"', '"'),
                    'company_name': company_name,
                    'inn': getattr(seller, 'inn', '') or '',
                    'orders_count': getattr(seller, 'orders_count', '') or '',
                    'reviews_count': getattr(seller, 'reviews_count', '') or '',
                    'average_rating': getattr(seller, 'average_rating', '') or '',
                    'working_time': getattr(seller, 'working_time', '') or '',
                    'seller_link': seller_link,
                })

            save_data = {
                'timestamp': datetime.now().strftime("%d.%m.%Y_%H-%M-%S"),
                'category_url': results.get('category_url', ''),
                'total_sellers': len(sellers_list),
                'sellers': sellers_list,
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения результатов: {e}")
    
    def _export_to_excel(self, user_id: str = None):
        try:
            # Получаем результаты для конкретного пользователя
            results = self.user_results.get(user_id, self.last_results) if user_id else self.last_results
            
            folder_name = results.get('output_folder', 'unknown')
            output_dir = self.settings.OUTPUT_DIR / folder_name
            
            exporter = ExcelExporter(output_dir, f"category_{folder_name}")
            selected_fields = results.get('selected_fields', [])
            
            # Экспортируем только продавцов
            export_data = {'sellers': []}
            seller_meta = results.get('seller_meta', {}) or {}

            for seller in results.get('sellers', []):
                if not getattr(seller, 'success', False):
                    continue

                sid = getattr(seller, 'seller_id', '')
                meta = seller_meta.get(sid, {}) if sid else {}

                company_name = (getattr(seller, 'company_name', '') or '').replace('\\"', '"').replace('\"', '"').replace('"', '"')
                seller_link = meta.get('seller_link') or (f"https://ozon.ru/seller/{sid}" if sid else "")

                export_data['sellers'].append({
                    'seller_id': sid,
                    'seller_name': (meta.get('seller_name') or '').replace('\\"', '"').replace('\"', '"').replace('"', '"'),
                    'company_name': company_name,
                    'inn': getattr(seller, 'inn', '') or '',
                    'orders_count': getattr(seller, 'orders_count', '') or '',
                    'reviews_count': getattr(seller, 'reviews_count', '') or '',
                    'average_rating': getattr(seller, 'average_rating', '') or '',
                    'working_time': getattr(seller, 'working_time', '') or '',
                    'seller_link': seller_link,
                })
            
            if exporter.export_results(export_data, selected_fields):
                json_path = output_dir / f"category_{folder_name}.json"
                self._send_files_to_telegram(
                    str(exporter.filepath),
                    user_id,
                    json_path=str(json_path) if json_path.exists() else None,
                )
            
        except Exception as e:
            logger.error(f"Ошибка экспорта в Excel: {e}")

    def _parse_orders_count_to_int(self, value) -> int:
        """Преобразует строковое значение заказов в int.
        Поддержка: 897 K, 1,6 M, 40,2 K (запятая — десятичная), 5 972, 1 315 (пробел — тысячи).
        """
        try:
            if value is None:
                return 0
            s = str(value).strip()
            if not s:
                return 0
            # Нормализуем неразрывные и тонкие пробелы
            s = s.replace('\u00a0', ' ').replace('\u202f', ' ').replace('\u2009', ' ')
            s_lower = s.lower()

            multiplier = 1
            # Убираем суффикс K/M (или тыс/млн), остаётся только числовая часть
            if s_lower.endswith('m') or ' m' in s_lower or 'млн' in s_lower:
                multiplier = 1_000_000
                num_part = re.sub(r'\s*m\s*$|\s*млн\s*$', '', s_lower, flags=re.I).strip()
            elif s_lower.endswith('k') or ' k' in s_lower or 'тыс' in s_lower:
                multiplier = 1_000
                num_part = re.sub(r'\s*k\s*$|\s*тыс\s*$', '', s_lower, flags=re.I).strip()
            else:
                num_part = s_lower

            # Пробел — разделитель тысяч (5 972 → 5972), запятая — десятичная (1,6 → 1.6)
            num_part = num_part.replace(' ', '').replace(',', '.')
            if not num_part:
                return 0
            return int(float(num_part) * multiplier)
        except Exception:
            return 0
    
    def start_telegram_bot(self, bot_token: str, user_ids) -> bool:
        try:
            if self.telegram_bot:
                self.telegram_bot.stop()
            
            # Поддерживаем как строку, так и массив для обратной совместимости
            if isinstance(user_ids, str):
                user_ids = [user_ids]
            elif not isinstance(user_ids, list):
                user_ids = list(user_ids)
            
            self.telegram_bot = TelegramBotManager(bot_token, user_ids, self)
            return self.telegram_bot.start()
        except Exception as e:
            logger.error(f"Ошибка запуска Telegram бота: {e}")
            return False
    
    def stop_telegram_bot(self):
        if self.telegram_bot:
            self.telegram_bot.stop()
            self.telegram_bot = None
    
    def restart_parsing(
        self,
        category_url: str,
        selected_fields: list = None,
        user_id: str = None,
        min_seller_orders: int = 0,
        max_seller_orders: int = 0,
    ) -> bool:
        self.stop_parsing(user_id)
        time.sleep(1)
        return self.start_parsing(category_url, selected_fields, user_id, min_seller_orders, max_seller_orders)
    
    def get_status(self):
        with self.parsing_lock:
            status = {
                'is_running': self.is_running,
                'active_users_count': len(self.active_parsing_users),
                'active_users': list(self.active_parsing_users),
                'telegram_bot_active': self.telegram_bot and hasattr(self.telegram_bot, 'is_running') and self.telegram_bot.is_running,
                'last_results': self.last_results,
                'settings': {
                    'max_products': self.settings.MAX_PRODUCTS,
                    'max_workers': self.settings.MAX_WORKERS
                }
            }
        
        # Добавляем информацию о ресурсах
        resource_status = resource_manager.get_status()
        status.update(resource_status)
        
        return status
    
    def get_user_results(self, user_id: str):
        """Получает результаты парсинга для конкретного пользователя"""
        with self.parsing_lock:
            return self.user_results.get(user_id, None)
    
    def _send_report_to_telegram(self, user_id: str = None):
        self._send_via_temp_bot(report_only=True, target_user_id=user_id)
    
    def _send_files_to_telegram(self, excel_path: str, user_id: str = None, json_path: str = None):
        self._send_via_temp_bot(excel_path=excel_path, json_path=json_path, target_user_id=user_id)

    def _send_via_temp_bot(self, excel_path: str = None, json_path: str = None, report_only: bool = False, target_user_id: str = None):
        try:
            from ..utils.config_loader import load_telegram_config
            
            bot_token, config_user_ids = load_telegram_config()
            
            if not bot_token:
                logger.error("Нет TELEGRAM_BOT_TOKEN в config.txt")
                return
            
            # Определяем целевого пользователя
            if target_user_id:
                # Отправляем конкретному пользователю
                target_users = [target_user_id]
            else:
                # Отправляем всем пользователям из конфига (для обратной совместимости)
                if not config_user_ids:
                    logger.error("Нет TELEGRAM_CHAT_ID в config.txt")
                    return
                target_users = config_user_ids.split(',') if isinstance(config_user_ids, str) else [config_user_ids]
            
            from aiogram import Bot
            from aiogram.types import FSInputFile
            
            async def send_files():
                temp_bot = Bot(token=bot_token)
                
                try:
                    for target_user in target_users:
                        target_user = target_user.strip()
                        
                        if report_only:
                            # Получаем результаты для конкретного пользователя
                            results = self.user_results.get(target_user_id, self.last_results) if target_user_id else self.last_results
                            
                            stats = results.get('parsing_stats', {})
                            total_time = stats.get('total_time', 0)
                            successful = stats.get('successful_products', 0)
                            failed = stats.get('failed_products', 0)
                            avg_time = stats.get('average_time_per_product', 0)
                            
                            hours = int(total_time // 3600)
                            minutes = int((total_time % 3600) // 60)
                            seconds = int(total_time % 60)
                            
                            if hours > 0:
                                time_str = f"{hours}ч {minutes}м {seconds}с"
                            elif minutes > 0:
                                time_str = f"{minutes}м {seconds}с"
                            else:
                                time_str = f"{seconds}с"
                            
                            success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
                            
                            report = (
                                "📈 <b>Отчет о парсинге</b>\n\n"
                                f"⏱️ <b>Общее время:</b> {time_str}\n"
                                f"⚡ <b>Среднее время на товар:</b> {avg_time:.1f}с\n\n"
                                f"📦 <b>Всего товаров:</b> {successful + failed}\n"
                                f"✅ <b>Успешно:</b> {successful}\n"
                                f"❌ <b>Неудачно:</b> {failed}\n"
                                f"📊 <b>Успешность:</b> {success_rate:.1f}%"
                            )
                            
                            await temp_bot.send_message(chat_id=target_user, text=report, parse_mode="HTML")
                        
                        if excel_path:
                            caption = (
                                "🎉 <b>Парсинг успешно завершен!</b>\n\n"
                                "📊 <b>Ваш Excel файл готов!</b>\n"
                                "💎 Данные отформатированы и готовы к использованию\n\n"
                                "📥 Скачайте файл ниже ⬇️"
                            )
                            document = FSInputFile(excel_path)
                            await temp_bot.send_document(
                                chat_id=target_user,
                                document=document,
                                caption=caption,
                                parse_mode="HTML"
                            )
                        if json_path:
                            import os
                            if os.path.isfile(json_path):
                                caption_json = "📄 <b>JSON</b> — полные данные парсинга"
                                doc_json = FSInputFile(json_path)
                                await temp_bot.send_document(
                                    chat_id=target_user,
                                    document=doc_json,
                                    caption=caption_json,
                                    parse_mode="HTML"
                                )
                    
                    if excel_path or json_path:
                        await asyncio.sleep(10)
                        self._delete_output_folder()
                        
                finally:
                    await temp_bot.session.close()
            
            asyncio.run(send_files())
            
        except Exception as e:
            logger.error(f"Ошибка отправки через временный бот: {e}")
    
    def _delete_output_folder(self):
        try:
            import shutil
            import os
            import stat
            
            folder_name = self.last_results.get('output_folder', '')
            if folder_name:
                output_dir = self.settings.OUTPUT_DIR / folder_name
                if output_dir.exists():
                    def handle_remove_readonly(func, path, exc):
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    
                    shutil.rmtree(output_dir, onerror=handle_remove_readonly)
        except Exception as e:
            logger.error(f"Ошибка удаления папки: {e}")
    
    def shutdown(self):
        # non-blocking wrapper
        threading.Thread(target=self._do_shutdown, daemon=True).start()

    def _do_shutdown(self):
        self.stop_parsing()
        self.stop_telegram_bot()