import logging
from pathlib import Path
from .config_loader import read_config, write_config

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        pass
    
    def get_user_settings(self, user_id: str):
        config = read_config()
        
        # Получаем настройки для конкретного пользователя
        selected_fields_key = f"USER_{user_id}_SELECTED_FIELDS"
        field_order_key = f"USER_{user_id}_FIELD_ORDER"
        default_count_key = f"USER_{user_id}_DEFAULT_COUNT"
        min_orders_key = f"USER_{user_id}_MIN_ORDERS"
        max_orders_key = f"USER_{user_id}_MAX_ORDERS"
        
        if selected_fields_key in config and field_order_key in config:
            selected_fields = config[selected_fields_key].split(',') if config[selected_fields_key] else []
            field_order = config[field_order_key].split(',') if config[field_order_key] else []
            default_count = int(config.get(default_count_key, 500))
            min_orders = int(config.get(min_orders_key, 0) or 0)
            max_orders = int(config.get(max_orders_key, 0) or 0)

            # Миграция: если у пользователя нет ни одного seller-поля, задаем дефолт для продавцов
            seller_fields = {
                'seller_id', 'seller_name', 'seller_link',
                'company_name', 'inn', 'orders_count',
                'reviews_count', 'average_rating', 'working_time'
            }
            if not any(f in seller_fields for f in selected_fields):
                default_fields = ['seller_name', 'company_name', 'seller_link', 'orders_count', 'average_rating', 'reviews_count', 'inn', 'working_time']
                self.save_user_settings(user_id, default_fields, default_fields, default_count, min_orders, max_orders)
                return {
                    'selected_fields': default_fields,
                    'field_order': default_fields,
                    'default_product_count': default_count,
                    'min_seller_orders': min_orders,
                    'max_seller_orders': max_orders,
                }

            return {
                'selected_fields': selected_fields,
                'field_order': field_order,
                'default_product_count': default_count,
                'min_seller_orders': min_orders,
                'max_seller_orders': max_orders,
            }
        else:
            # Настройки по умолчанию
            default_fields = ['seller_name', 'company_name', 'seller_link', 'orders_count', 'average_rating', 'reviews_count', 'inn', 'working_time']
            self.save_user_settings(user_id, default_fields, default_fields, 500, 0, 0)
            return {
                'selected_fields': default_fields,
                'field_order': default_fields,
                'default_product_count': 500,
                'min_seller_orders': 0,
                'max_seller_orders': 0,
            }
    
    def save_user_settings(
        self,
        user_id: str,
        selected_fields: list,
        field_order: list,
        default_count: int = 500,
        min_seller_orders: int = 0,
        max_seller_orders: int = 0,
    ):
        config = {
            f"USER_{user_id}_SELECTED_FIELDS": ','.join(selected_fields),
            f"USER_{user_id}_FIELD_ORDER": ','.join(field_order),
            f"USER_{user_id}_DEFAULT_COUNT": str(default_count),
            f"USER_{user_id}_MIN_ORDERS": str(int(min_seller_orders or 0)),
            f"USER_{user_id}_MAX_ORDERS": str(int(max_seller_orders or 0)),
        }
        
        return write_config(config)