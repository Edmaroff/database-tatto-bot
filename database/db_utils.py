from config_data.config import NUMBER_ALL_STYLES, MAX_NUMBER_STYLES
from logging_errors.logging_setup import logger


async def validate_style_ids(style_ids: list[int]) -> list[int]:
    """
    Проверяет список ID стилей на наличие стиля "Все стили",
    удаляет дубликаты и проверяет наличие чисел больше MAX_NUMBER_STYLES и меньше NUMBER_ALL_STYLES.

    Параметры:
    - style_ids (list[int]): Список ID стилей.

    Возвращает:
    - list[int]: [0], если список содержит стиль "Все стили", иначе вернёт список
     с устраненными дубликатами и числами, которые не превышают MAX_NUMBER_STYLES.
    """

    logger.info("*БД* Вызвана функция validate_style_ids")
    try:
        # Удаляем дубликаты из списка style_ids
        unique_style_ids = list(set(style_ids))

        # Проверяем наличие стиля "Все стили"
        if NUMBER_ALL_STYLES in unique_style_ids:
            return [NUMBER_ALL_STYLES]

        # Обрезаем список, если числа больше MAX_NUMBER_STYLES и меньше NUMBER_ALL_STYLES
        filtered_style_ids = [
            style_id
            for style_id in unique_style_ids
            if NUMBER_ALL_STYLES <= style_id <= MAX_NUMBER_STYLES
        ]
        return filtered_style_ids
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции validate_style_ids: {error}")
