from database.models import (
    Complaints,
    Styles,
    ContactRequests,
    Likes,
)
from logging_errors.logging_setup import logger

from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError


async def create_complaint(
    session_maker, client_id: int, master_id: int, complaint_text: str
) -> None:
    """
    Создает запись о жалобе в таблице Complaints.

    Параметры:
    - client_id (int): Telegram ID клиента, который подает жалобу.
    - master_id (int): Telegram ID мастера, на которого подается жалоба.
    - complaint_text (str): Текст жалобы.

    Возвращает:
    - None
    """

    logger.info("*БД* Вызвана функция create_complaint")
    try:
        async with session_maker() as session:
            async with session.begin():
                complaint = Complaints(
                    client_id=client_id,
                    master_id= int(master_id),
                    complaint_text=complaint_text,
                )

                session.add(complaint)
                # return 'Жалоба создана'

    # Повторная жалоба от клиента на одного мастера
    except IntegrityError:
        pass
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции create_complaint: {error}")


async def create_like(session_maker, client_id: int, master_id: int) -> bool:
    """
    Создает запись о лайке в таблице Likes.

    Параметры:
    - client_id (int): Telegram ID клиента, который лайкнул мастера.
    - master_id (int): Telegram ID мастера, которого лайкнули.

    Возвращает:
    - None
    """

    logger.info("*БД* Вызвана функция create_like")
    try:
        async with session_maker() as session:
            async with session.begin():
                like = Likes(client_id=client_id, master_id=master_id)
                session.add(like)
                return True

    # Повторный лайк от клиента на одного мастера
    except IntegrityError:
        return False
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции create_like: {error}")


async def create_contact_request(session_maker, client_id: int, master_id: int) -> None:
    """
    Создает запись о запросе контакта в таблице ContactRequests.

    Параметры:
    - client_id (int): Telegram ID клиента, который запросил контакты.
    - master_id (int): Telegram ID мастера, у которого запросили контакты.

    Возвращает:
    - None
    """

    logger.info("*БД* Вызвана функция create_contact_request")
    try:
        async with session_maker() as session:
            async with session.begin():
                contact_request = ContactRequests(
                    client_id=client_id, master_id=master_id
                )
                session.add(contact_request)

    # Повторный запрос контактов от клиента на одного мастера
    except IntegrityError:
        pass
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции create_contact_request: {error}"
        )


async def create_styles(session_maker, styles_dict: dict[int:str]) -> None:
    """
    Создает стили в таблице Styles.

    Параметры:
    - styles_dict (dict): Словарь, где ключами являются ID стиля (int),
     а значениями - имя стиля (str).

    Возвращает:
    - None.
    """
    logger.info("*БД* Вызвана функция create_styles")
    try:
        async with session_maker() as session:
            async with session.begin():
                for style_id, style_name in styles_dict.items():
                    style = Styles(style_id=style_id, style_name=style_name)
                    session.add(style)
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции create_styles: {error}")


async def get_style_dictionary(session_maker) -> dict[int:str]:
    """
    Получает словарь стилей татуировки из таблицы Styles.

    Возвращает:
    - Словарь стилей татуировки в формате {style_id: style_name}.
    """

    logger.info("*БД* Вызвана функция get_style_dictionary")
    try:
        async with session_maker() as session:
            styles = await session.execute(select(Styles))
            style_dict = {
                style.style_id: style.style_name
                for style in styles.scalars()
                if style.style_name != "Все стили"
            }
            return style_dict
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_style_dictionary: {error}"
        )


async def delete_like(session_maker, client_id: int, master_id: int) -> bool:
    """
    Удаляет запись о лайке из таблицы Likes.

    Параметры:
    - client_id (int): Telegram ID клиента, который лайкнул мастера.
    - master_id (int): Telegram ID мастера, которого лайкнули.

    Возвращает:
    - bool: True, если лайк успешно удален, False, если лайк не был найден.
    """

    logger.info("*БД* Вызвана функция delete_like")
    try:
        async with session_maker() as session:
            async with session.begin():
                delete_query = delete(Likes).where(
                    Likes.client_id == client_id, Likes.master_id == master_id
                )
                result = await session.execute(delete_query)
                # Проверяем, была ли хотя бы одна запись удалена
                if result.rowcount > 0:
                    return True
                else:
                    return False

    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции delete_like: {error}")
        return False
