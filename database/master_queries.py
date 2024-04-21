import datetime
from importlib import import_module

from config_data.config import (
    NUMBER_ALL_STYLES,
    TATTOO_TYPE_MONOCHROME,
    TATTOO_TYPE_COLOR,
)
from database.db_utils import validate_style_ids
from database.models import (
    Master,
    Complaints,
    MasterStyles,
    Styles,
    MasterPhotos,
    ContactRequests,
    Likes,
    ClientStyles,
    Client,
)
from logging_errors.logging_setup import logger

from sqlalchemy import select, exists, delete, update, func, literal_column, desc, and_
from sqlalchemy.sql.functions import count
from sqlalchemy.orm import selectinload, join, outerjoin
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.exc import IntegrityError


async def create_master(
    session_maker,
    master_id: int,
    username: str,
    master_url: str,
    name: str,
    city: str,
    about_master: str,
    tattoo_type: str,
    phone_number: str,
    is_fake: bool = False,
    is_blocked: bool = False,
) -> bool:
    """
    Создает новую запись о мастере в таблице Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - username (str): Логин мастера в Telegram.
    - master_url (str): Ссылка на мастера в Telegram.
    - name (str): Имя мастера.
    - city (str): Город мастера.
    - about_master (str): Информация о мастере.
    - tattoo_type (str): Тип татуировки, в котором работает мастер.


    Возвращает:
    - True, если мастер создан.
    - False, если мастер уже есть в таблице 'Client'.
    - False, если мастер уже есть в таблице 'Master'.
    """

    logger.info("*БД* Вызвана функция create_master")
    try:
        # Импорт с importlib для избежания цикличного импорта
        client_queries = import_module(".client_queries", package="database")

        if await client_queries.check_client_in_db(session_maker, master_id):
            raise ValueError(f"Telegram ID пользователя {master_id}")

        if not username:
            username = None

        async with session_maker() as session:
            async with session.begin():
                master = Master(
                    master_id=master_id,
                    username=username,
                    master_url=master_url,
                    name=name,
                    city=city,
                    about_master=about_master,
                    tattoo_type=tattoo_type,
                    phone_number=phone_number,
                    is_fake=is_fake,
                    is_blocked=is_blocked,
                )
                session.add(master)
                return True
    except (IntegrityError, ValueError) as master_exists:
        logger.warning(
            f"*БД* Мастер уже есть в БД, функция create_master: {master_exists}"
        )
        return False
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции create_master: {error}")


async def check_master_in_db(session_maker, master_id: int) -> bool:
    """
    Проверяет есть ли пользователь в таблице Master.

    Параметры:
    - master_id (int): Telegram ID пользователя.

    Возвращает:
    - True, если пользователь есть в Master, иначе False.
    """

    logger.info("*БД* Вызвана функция check_master_in_db")
    try:
        async with session_maker() as session:
            query = select(exists().where(Master.master_id == master_id))
            user_exists = await session.scalar(query)
            return user_exists
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции check_master_in_db: {error}")


async def create_master_styles(
    session_maker, master_id: int, style_ids: list[int]
) -> None:
    """
    Создает записи о стилях тату, в которых работает мастер, перед созданием
     удаляет записи об уже выбранных стилях в таблице MasterStyles.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - style_ids (list[int]): Список ID стилей из таблицы Styles.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция create_master_styles")
    try:
        # Удаление уже выбранных стилей мастера
        await delete_master_styles(session_maker, master_id)

        # Проверка style_ids
        style_ids = await validate_style_ids(style_ids)

        async with session_maker() as session:
            async with session.begin():
                for style_id in style_ids:
                    query = select(Styles).where(Styles.style_id == style_id)
                    style = await session.execute(query)
                    style = style.scalar_one_or_none()

                    if style:
                        master_style = MasterStyles(
                            master_id=master_id, style_id=style_id
                        )
                        session.add(master_style)
                    else:
                        logger.warning(
                            f"Стиля со style_id={style_id} не существует в Styles"
                        )
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции create_master_styles: {error}"
        )


async def create_master_photos(session_maker, master_id: int, photo_paths: list[str]):
    """
    Создает записи фото мастера в таблице MasterPhotos, перед созданием
     удаляет записи об уже выбранных фото в таблице MasterPhotos.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - photo_paths (list[str]): Список путей до фото на сервере.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция create_master_photos")
    try:
        # Удаление существующих фотографий мастера
        await delete_master_photos(session_maker, master_id)

        async with session_maker() as session:
            async with session.begin():
                for photo_path in photo_paths:
                    master_photo = MasterPhotos(
                        master_id=master_id, photo_path=photo_path
                    )
                    session.add(master_photo)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции create_master_photos: {error}"
        )


async def get_master_field_value(
    session_maker, master_id: int, field_name: str
) -> bool:
    """
    Получает значение поля field_name для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - field_name (str): Имя поля, значение которого нужно получить.

    Возвращает:
    - Значение поля field_name.
    """

    logger.info("*БД* Вызвана функция get_master_field_value")
    try:
        async with session_maker() as session:
            query = select(getattr(Master, field_name)).where(
                Master.master_id == master_id
            )
            result = await session.execute(query)
            field_value = result.scalar()
            if field_value is not None:
                return field_value
            else:
                logger.warning(f"Мастер с master_id={master_id} не найден.")
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_field_value: {error}"
        )


async def get_master_is_blocked(session_maker, master_id: int) -> bool:
    """
    Получает значение поля is_blocked для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - Значение поля is_blocked (заблокирован ли мастер).
    """

    logger.info("*БД* Вызвана функция get_master_is_blocked")
    try:
        field_name = "is_blocked"
        field_value = await get_master_field_value(session_maker, master_id, field_name)
        return field_value
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_is_blocked: {error}"
        )


async def get_master_is_notifications_allowed(session_maker, master_id: int) -> bool:
    """
    Получает значение поля is_notifications_allowed для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - Значение поля is_notifications_allowed (заблокирован ли мастер на уведомления).
    """

    logger.info("*БД* Вызвана функция get_master_is_notifications_allowed")
    try:
        field_name = "is_notifications_allowed"
        field_value = await get_master_field_value(session_maker, master_id, field_name)
        return field_value
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_is_notifications_allowed: {error}"
        )


async def get_master_is_fake(session_maker, master_id: int) -> bool:
    """
    Получает значение поля is_fake для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - Значение поля is_fake (фейковый ли мастер).
    """

    logger.info("*БД* Вызвана функция get_master_is_fake")
    try:
        field_name = "is_fake"
        field_value = await get_master_field_value(session_maker, master_id, field_name)
        return field_value
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции get_master_is_fake: {error}")


async def get_master_cities_new_registered(session_maker) -> list[str]:
    """
    Получает список городов мастеров, которые зарегистрировались не позднее одной неделе назад.
    (Функция используется для рассылки сообщений о новых мастерах)

    Возвращает:
    - list[str] - список уникальных городов. Если не было мастеров,
     которые зарегистрировались не позднее 1 недели назад, вернёт []
    """

    logger.info("*БД* Вызвана функция get_master_cities_new_registered")
    try:
        async with session_maker() as session:
            # Вычисляем дату, которая была неделю назад от текущего момента
            one_week_ago = datetime.datetime.now() - datetime.timedelta(weeks=1)

            query = select(Master.city).where(
                and_(Master.is_blocked.is_(False), Master.date_of_reg >= one_week_ago)
            )
            result = await session.execute(query)
            cities = [row[0] for row in result.unique()]
            return cities
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_cities_new_registered: {error}"
        )


async def get_master_complaints_count(session_maker, master_id: int) -> int:
    """
    Получает количество жалоб на Мастера в таблице Complaints.

    Параметры:
    - master_id (int): Telegram ID Мастера.

    Возвращает:
    - int - количество жалоб на  Мастера.
    """

    logger.info("*БД* Вызвана функция get_master_complaints_count")
    try:
        async with session_maker() as session:
            query = select(func.count(Complaints.complaint_id)).where(
                Complaints.master_id == master_id
            )
            result = await session.execute(query)
            complaints_count = result.scalar()
            return complaints_count
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_complaints_count: {error}"
        )


async def get_master_likes_count(session_maker, master_id: int) -> int:
    """
    Получает количество лайков у Мастера в таблице Likes.

    Параметры:
    - master_id (int): Telegram ID Мастера.

    Возвращает:
    - int - количество лайков у Мастера.
    """

    logger.info("*БД* Вызвана функция get_master_likes_count")
    try:
        async with session_maker() as session:
            query = select(func.count(Likes.like_id)).where(
                Likes.master_id == master_id
            )
            result = await session.execute(query)
            likes_count = result.scalar()
            return likes_count
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_likes_count: {error}"
        )


async def get_master_contact_requests_count(session_maker, master_id: int) -> int:
    """
    Получает количество запросов на контакты Мастера в таблице ContactRequests.

    Параметры:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - int - количество запросов на контакты Мастера.
    """

    logger.info("*БД* Вызвана функция get_master_contact_requests_count")
    try:
        async with session_maker() as session:
            query = select(func.count(ContactRequests.request_id)).where(
                ContactRequests.master_id == master_id
            )
            result = await session.execute(query)
            contact_requests_count = result.scalar()
            return contact_requests_count
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_contact_requests_count: {error}"
        )


async def get_master_main_info(session_maker, master_id: int) -> dict:
    """
    Получает основную информацию
    (имя, город, тип тату, номер телефона, информация о себе) о мастере.

    Параметры:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - dict - Словарь вида:
    {"name": str, "city": str, "tattoo_type": str, "phone_number": str, "about_master": str},
     если мастер не найден, вернёт {}.
    """
    logger.info("*БД* Вызвана функция get_master_main_info")
    try:
        async with session_maker() as session:
            master = await session.get(Master, master_id)
            if master:
                return {
                    "name": master.name,
                    "city": master.city,
                    "tattoo_type": master.tattoo_type,
                    "phone_number": master.phone_number,
                    "about_master": master.about_master,
                }
            return {}
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_main_info: {error}"
        )


async def get_master_contact_info(session_maker, master_id: int) -> dict:
    """
    Получает контакты мастера (номер телефона и ссылка на мастера) о мастере.

    Параметры:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - dict - Словарь вида:
    {"phone_number": str, "master_url": str},
     если мастер не найден, вернёт {}.
    """
    logger.info("*БД* Вызвана функция get_master_contact_info")
    try:
        async with session_maker() as session:
            master = await session.get(Master, master_id)
            if master:
                return {
                    "phone_number": master.phone_number,
                    "master_url": master.master_url,
                }
            return {}
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_contact_info: {error}"
        )


async def get_master_selected_styles(session_maker, master_id: int) -> dict:
    """
    Получает словарь стилей, которые выбрал мастер.

    Параметры:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - dict - словарь вида {номер стиля (int): название стиля (str)},
     если мастер не найден, вернёт {}.
    """

    logger.info("*БД* Вызвана функция get_master_selected_styles")
    try:
        async with session_maker() as session:
            style_list = await session.execute(
                select(MasterStyles.style_id, Styles.style_name)
                .select_from(MasterStyles)
                .join(Styles)
                .where(MasterStyles.master_id == master_id)
            )

            result = {}
            if style_list:
                result_list = style_list.all()
                for style in result_list:
                    result[style[0]] = style[1]

            return result
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_selected_styles: {error}"
        )


async def get_master_photos(session_maker, master_id: int) -> list:
    """
    Получает список путей всех фотографий мастера.

    Параметры:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - list - список путей на фото мастера вида [str,str,str, ...], если
     мастер/фото не найдены, вернёт [].
    """

    logger.info("*БД* Вызвана функция get_master_photos")
    try:
        async with session_maker() as session:
            foto_to_string = func.string_agg(
                MasterPhotos.photo_path,
                aggregate_order_by(literal_column("';'"), MasterPhotos.master_id),
            )
            foto_str = await session.scalar(
                select(foto_to_string)
                .select_from(MasterPhotos)
                .where(MasterPhotos.master_id == master_id)
                .group_by(MasterPhotos.master_id)
            )
            if foto_str:
                result = foto_str.split(";")
            else:
                result = []
            return result
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции get_master_photos: {error}")


async def get_master_stats(session_maker, master_id: int) -> tuple:
    """
    Получает количество лайков, жалоб и запросов на контакты Мастера
    из таблиц Likes, Complaints, ContactRequests.

    Параметры:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - tuple - количество лайков, жалоб и запросов на контакты Мастера.
    """

    logger.info("*БД* Вызвана функция get_master_stats")
    try:
        requests = []
        async with session_maker() as session:
            for request in [Likes, Complaints, ContactRequests]:
                master_request = (
                    select(count(request.master_id))
                    .select_from(request)
                    .where(request.master_id == master_id)
                )
                requests.append(master_request)
            client_list = await session.scalars(
                requests[0].union_all(requests[1], requests[2])
            )
            result = client_list.all()
            return tuple(result)  # (Likes, Complaints, ContactRequests)

    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции get_master_stats: {error}")


async def get_master_list_stats(session_maker, list_master_id: list[int]) -> dict:
    """
    Получает количество лайков, жалоб и запросов на контакты Мастера
    из таблиц Likes, Complaints, ContactRequests в виде словаря. (для рассылки статистики мастеров)

    Параметры:
    - list_master_id (list[int]): Список Telegram ID мастеров.

    Возвращает:
    - dict - словарь вида
     {master_id (int): [likes (int), complaints (int), contact_requests (int)]},
     если мастер не найден, то в словаре не будет ключа с master_id этого мастера.
    """

    logger.info("*БД* Вызвана функция get_master_list_stats")
    try:
        async with session_maker() as session:
            query = (
                select(Master)
                .filter(Master.master_id.in_(list_master_id))
                .options(
                    selectinload(Master.likes),
                    selectinload(Master.complaints),
                    selectinload(Master.contact_requests),
                )
            )

            result = await session.execute(query)
            masters = result.scalars().all()

            master_info = {}
            for master in masters:
                likes = len(master.likes)
                complaints = len(master.complaints)
                contact_requests = len(master.contact_requests)
                master_info[master.master_id] = [likes, complaints, contact_requests]
        return master_info

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_list_stats: {error}"
        )


async def get_master_profiles(session_maker, list_master_id: list[int]) -> list:
    """
    Получает список анкет мастеров для отображения клиенту.

    Параметры:
    - list_master_id (list): Список Telegram ID мастеров.


    Возвращает:
    - Список анкет мастеров в виде словаря, вида:
        - "master_id" (int): Telegram ID мастера.
        - "name" (str): Имя мастера.
        - "city" (str): Город, где находится мастер.
        - "about_master" (str): Описание мастера.
        - "photo_path" (list[str]): Список путей к фотографиям мастера.
        - "likes" (int): Количество лайков у мастера.
      Если ни один master_id в list_master_id не существует, вернёт [].
    """
    logger.info("*БД* Вызвана функция get_master_profiles")
    try:
        async with session_maker() as session:
            query = (
                select(Master)
                .options(selectinload(Master.photos), selectinload(Master.likes))
                .where(
                    and_(
                        Master.is_blocked.is_(False),
                        Master.master_id.in_(list_master_id),
                    )
                )
            )

            result = await session.execute(query)
            masters = result.scalars().all()

            master_profiles = []
            for master in masters:
                name = master.name
                city = master.city
                about_master = master.about_master
                photos = [photo.photo_path for photo in master.photos]
                likes = len(master.likes)
                info = {
                    "master_id": master.master_id,
                    "about_master": about_master,
                    "name": name,
                    "city": city,
                    "photo_path": photos,
                    "likes": likes,
                }
                master_profiles.append(info)

        return master_profiles
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_profiles: {error}"
        )


async def update_master_field_value(
    session_maker, master_id: int, field_name: str, new_value: bool | str
) -> None:
    """
    Обновляет значение поля field_name для указанного мастера  в таблице Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - field_name (str): Имя поля, значение которого нужно изменить.
    - new_value: Новое значение поля.

    Возвращает:
    - None
    """

    logger.info("*БД* Вызвана функция update_master_field_value")
    try:
        async with session_maker() as session:
            async with session.begin():
                query = (
                    update(Master)
                    .where(Master.master_id == master_id)
                    .values({field_name: new_value})
                )
                await session.execute(query)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_master_field_value: {error}"
        )


async def update_master_username(
    session_maker, master_id: int, new_value: bool
) -> None:
    """
    Обновляет значение поля username для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - new_value (bool): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_master_username")
    try:
        field_name = "username"
        await update_master_field_value(session_maker, master_id, field_name, new_value)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_master_username: {error}"
        )


async def update_master_url(session_maker, master_id: int, new_value: bool) -> None:
    """
    Обновляет значение поля master_url для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - new_value (bool): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_master_url")
    try:
        field_name = "master_url"
        await update_master_field_value(session_maker, master_id, field_name, new_value)
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции update_master_url: {error}")


async def update_master_is_notifications_allowed(
    session_maker, master_id: int, new_value: bool
) -> None:
    """
    Обновляет значение поля is_notifications_allowed для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - new_value (bool): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_master_is_notifications_allowed")
    try:
        field_name = "is_notifications_allowed"
        await update_master_field_value(session_maker, master_id, field_name, new_value)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_master_is_notifications_allowed: {error}"
        )


async def update_master_is_fake(session_maker, master_id: int, new_value: bool) -> None:
    """
    Обновляет значение поля is_fake для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - new_value (bool): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_master_is_fake")
    try:
        field_name = "is_fake"
        await update_master_field_value(session_maker, master_id, field_name, new_value)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_master_is_fake: {error}"
        )


async def update_master_name(session_maker, master_id: int, new_value: str) -> None:
    """
    Обновляет значение поля name для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - new_value (str): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_master_name")
    try:
        field_name = "name"
        await update_master_field_value(session_maker, master_id, field_name, new_value)
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции update_master_name: {error}")


async def update_master_city(session_maker, master_id: int, new_value: str) -> None:
    """
    Обновляет значение поля city для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - new_value (str): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_master_city")
    try:
        field_name = "city"
        await update_master_field_value(session_maker, master_id, field_name, new_value)
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции update_master_city: {error}")


async def update_master_tattoo_type(
    session_maker, master_id: int, new_value: str
) -> None:
    """
    Обновляет значение поля tattoo_type для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - new_value (str): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_master_tattoo_type")
    try:
        field_name = "tattoo_type"
        await update_master_field_value(session_maker, master_id, field_name, new_value)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_master_tattoo_type: {error}"
        )


async def update_master_about_master(
    session_maker, master_id: int, new_value: str
) -> None:
    """
    Обновляет значение поля about_master для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - new_value (str): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_master_about_master")
    try:
        field_name = "about_master"
        await update_master_field_value(session_maker, master_id, field_name, new_value)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_master_about_master: {error}"
        )


async def update_master_phone_number(
    session_maker, master_id: int, new_value: str
) -> None:
    """
    Обновляет значение поля phone_number для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - new_value (str): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_master_phone_number")
    try:
        field_name = "phone_number"
        await update_master_field_value(session_maker, master_id, field_name, new_value)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_master_phone_number: {error}"
        )


async def delete_master_photos(session_maker, master_id: int) -> None:
    """
    Удаляет все записи из таблицы MasterPhotos для указанного master_id.

    Аргументы:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - None
    """
    logger.info("*БД* Вызвана функция delete_master_photos")
    try:
        async with session_maker() as session:
            async with session.begin():
                delete_query = delete(MasterPhotos).where(
                    MasterPhotos.master_id == master_id
                )
                await session.execute(delete_query)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции delete_master_photos: {error}"
        )


async def delete_master(session_maker, master_id: int) -> None:
    """
    Удаляет мастера из таблицы Master и всех связанных таблиц.

    Параметры:
    - master_id (int): ID мастера в Telegram.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция delete_master")
    try:
        async with session_maker() as session:
            async with session.begin():
                query = select(Master).where(Master.master_id == master_id)
                result = await session.execute(query)
                master = result.scalar_one_or_none()
                if master is not None:
                    await session.delete(master)
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции delete_master: {error}")


async def delete_master_styles(session_maker, master_id: int) -> None:
    """
    Удаляет все записи из таблицы MasterStyles для указанного master_id.

    Аргументы:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - None
    """
    logger.info("*БД* Вызвана функция delete_master_styles")
    try:
        async with session_maker() as session:
            async with session.begin():
                delete_query = delete(MasterStyles).where(
                    MasterStyles.master_id == master_id
                )
                await session.execute(delete_query)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции delete_master_styles: {error}"
        )


# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# ---------------- ФУНКЦИИ ПОИСКА АНКЕТ МАСТЕРОВ ДЛЯ КЛИЕНТА ----------------
async def get_client_info_and_styles(session_maker, client_id: int) -> tuple:
    """
    Получает информацию (Telegram ID клиента, имя, город, тип тату, номера выбранных стилей тату)
     о клиенте (для поиска анкет мастеров).

    Параметры:
    - client_id (str): Telegram ID клиента.

    Возвращает:
    - tuple - Кортеж (Telegram ID клиента (int), имя (str), город (str),
     тип тату (str), номера выбранных стилей тату [list]), если клиент не найден, вернёт []

    """
    logger.info("*БД* Вызвана функция get_client_info_and_styles")
    try:
        result = []
        async with session_maker() as session:
            request = (
                select(
                    Client.client_id,
                    Client.name,
                    Client.city,
                    Client.tattoo_type,
                    func.array_agg(ClientStyles.style_id),
                )
                .select_from(join(Client, ClientStyles))
                .where(Client.client_id == client_id)
                .group_by(
                    Client.client_id, Client.name, Client.city, Client.tattoo_type
                )
            )
            client_request = await session.execute(request)
            client = client_request.fetchone()
            if bool(client):
                result = client

        return result

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_info_and_styles: {error}"
        )


async def get_master_list_photos(session_maker, list_master_id: list) -> dict:
    """
    Получает словарь с master_id и списком путей всех фотографий мастера
     (для поиска анкет мастеров).

    Параметры:
    - list_master_id (list[int]): Список Telegram ID мастеров.

    Возвращает:
    - dict - словарь вида {Telegram ID мастера (int): списком путей фотографий (list[str])},
     если мастер не найден, вернёт {Telegram ID мастера (int): []}.
    """

    logger.info("*БД* Вызвана функция get_master_list_photos")
    try:
        result = {}
        async with session_maker() as session:
            add_foto_to_string = func.string_agg(
                MasterPhotos.photo_path,
                aggregate_order_by(literal_column("';'"), MasterPhotos.master_id),
            )
            foto_str = await session.execute(
                select(MasterPhotos.master_id, add_foto_to_string)
                .select_from(MasterPhotos)
                .where(MasterPhotos.master_id.in_(list_master_id))
                .group_by(MasterPhotos.master_id)
            )

        foto_master_dict = dict(foto_str.all())
        for master_id in list_master_id:
            # Если у мастера нет фото возвращает пустой список
            photo_path = []
            if master_id in foto_master_dict:
                photo_path = foto_master_dict[master_id].split(";")
            result[master_id] = photo_path

        return result
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_list_photos: {error}"
        )


async def get_master_list_selected_styles(session_maker, list_master_id: list) -> dict:
    """
    Получает словарь с master_id и списком стилей, которые выбрал мастер
     (для поиска анкет мастеров).

    Параметры:
    - list_master_id (list[int]): Список Telegram ID мастеров.

    Возвращает:
    - dict - словарь вида {Telegram ID мастера (int): список названий стилей (list[str])},
     если мастер не найден, вернёт {Telegram ID мастера (int): []}.
    """

    logger.info("*БД* Вызвана функция get_master_list_selected_styles")
    try:
        result = {}
        async with session_maker() as session:
            # Получение списка стилей работ мастера
            styles_to_string = func.string_agg(
                Styles.style_name,
                aggregate_order_by(literal_column("';'"), MasterStyles.master_id),
            )
            styles_str = await session.execute(
                select(MasterStyles.master_id, styles_to_string)
                .select_from(MasterStyles)
                .join(Styles)
                .where(MasterStyles.master_id.in_(list_master_id))
                .group_by(MasterStyles.master_id)
            )

        styles_master_dict = dict(styles_str.all())
        for master_id in list_master_id:
            # Если у мастера нет фото возвращает пустой список
            style = []
            if master_id in styles_master_dict:
                style = styles_master_dict[master_id].split(";")
            result[master_id] = style

        return result
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_list_selected_styles: {error}"
        )


async def get_master_ranking_by_like_all(
    session_maker, client_id: int, len_index: int, len_return=1
) -> list[dict]:
    """
    Документация в функции get_master_ranking_by_like_with_except, filtered='all'
    """

    logger.info("*БД* Вызвана функция get_master_ranking_by_like_all")
    try:
        result = []  # Окончательный список словарей с подходящими мастерами
        list_tuples_masters = (
            []
        )  # список кортежей Матеров вида (master_id, name, city, количество лайков)
        list_master_id = []  # список с master_id Мастеров
        async with session_maker() as session:
            # master_id, name, city, tattoo_type, list_styles = client
            client = await get_client_info_and_styles(session_maker, client_id)

            #  Вернет пустой список если клиента нет в базе
            if not client:
                return result

            city: str = client[2]
            tattoo_type: str = client[3]
            list_styles: str = client[4]

            # Проверка типа тату
            if tattoo_type == TATTOO_TYPE_MONOCHROME:
                filter_type = [Master.tattoo_type != TATTOO_TYPE_COLOR]
            elif tattoo_type == TATTOO_TYPE_COLOR:
                filter_type = [Master.tattoo_type != TATTOO_TYPE_MONOCHROME]
            else:
                filter_type = []

            # Если у клиента выбраны ВСЕ СТИЛИ
            if [NUMBER_ALL_STYLES] == list_styles:
                # Выбирает всех универсалов подходящих клиенту
                universal_masters_for_client = (
                    select(MasterStyles.master_id)
                    .distinct(MasterStyles.master_id)
                    .select_from(join(Master, MasterStyles))
                    .where(
                        *filter_type, Master.is_blocked.is_(False), Master.city == city
                    )
                )

                # Все мастера подходящие клиенту
                all_master_client = universal_masters_for_client
            else:
                # Выбирает всех мастеров подходящих клиенту кроме универсальных
                masters_for_client = (
                    select(MasterStyles.master_id)
                    .distinct(MasterStyles.master_id)
                    .select_from(
                        join(MasterStyles, Master).join(
                            ClientStyles, ClientStyles.style_id == MasterStyles.style_id
                        )
                    )
                    .where(
                        and_(
                            *filter_type,
                            ClientStyles.client_id == client_id,
                            Master.city == city,
                        ),
                    )
                )
                # Выбирает всех универсалов подходящих клиенту
                universal_masters_for_client = (
                    select(MasterStyles.master_id)
                    .select_from(join(Master, MasterStyles))
                    .where(
                        and_(
                            *filter_type,
                            MasterStyles.style_id == NUMBER_ALL_STYLES,
                            Master.city == city,
                        ),
                    )
                )
                # Все мастера подходящие клиенту
                all_master_client = masters_for_client.union_all(
                    universal_masters_for_client
                )

            # Запрос для получения кортежа мастеров
            request = (
                select(
                    Master.master_id,
                    Master.name,
                    Master.city,
                    Master.about_master,
                    count(Likes.master_id).label("count_likes"),
                )
                .select_from(outerjoin(Master, Likes))
                .where(
                    and_(
                        Master.city == city,
                        Master.is_blocked.is_(False),
                        Master.master_id.in_(all_master_client),
                    )
                )
                .group_by(Master.master_id, Master.name, Master.city)
                .order_by(desc("count_likes"))
            )

            generator_list_masters = await session.execute(request)
            # Получение нужной части мастеров
            number_iter = len_index // len_return + bool(len_index % len_return)
            for _ in range(number_iter):
                value = generator_list_masters.fetchmany(len_return)
                list_tuples_masters = value
            for tuple_master in list_tuples_masters:
                list_master_id.append(tuple_master[0])

            # Получение списка ссылок на фото работ мастера
            photo_path = await get_master_list_photos(session_maker, list_master_id)

            # Получение списка стилей работ мастера
            styles = await get_master_list_selected_styles(
                session_maker, list_master_id
            )

            # Создание словаря Мастера
            for master in list_tuples_masters:
                master_id = master[0]

                master_dict = {
                    "master_id": master_id,
                    "name": master[1],
                    "city": master[2],
                    "about_master": master[3],
                    "styles": styles[master_id],
                    "photo_path": photo_path[master_id],
                    "likes": master[4],
                }
                result.append(master_dict)

        return result

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_ranking_by_like_all: {error}"
        )


async def get_master_ranking_by_like_city(
    session_maker, client_id: int, len_index: int, len_return=1
) -> list[dict]:
    """
    Документация в функции get_master_ranking_by_like_with_except, filtered='city'
    """

    logger.info("*БД* Вызвана функция get_master_ranking_by_like_city")
    try:
        result = []  # Окончательный список словарей с подходящими мастерами
        list_tuples_masters = (
            []
        )  # список кортежей Матеров вида (master_id, name, city, количество лайков)
        list_master_id = []  # список с master_id Мастеров
        async with session_maker() as session:
            # master_id, name, city, tattoo_type, list_styles = client
            client = await get_client_info_and_styles(session_maker, client_id)

            #  Вернет пустой список если клиента нет в базе
            if not client:
                return result

            city: str = client[2]
            tattoo_type: str = client[3]
            list_styles: str = client[4]

            # Проверка типа тату
            if tattoo_type == TATTOO_TYPE_MONOCHROME:
                filter_type = [Master.tattoo_type != TATTOO_TYPE_COLOR]
            elif tattoo_type == TATTOO_TYPE_COLOR:
                filter_type = [Master.tattoo_type != TATTOO_TYPE_MONOCHROME]
            else:
                filter_type = []

            # Если у клиента выбраны ВСЕ СТИЛИ
            if [NUMBER_ALL_STYLES] == list_styles:
                # Выбирает всех универсалов подходящих клиенту
                universal_masters_for_client = (
                    select(MasterStyles.master_id)
                    .distinct(MasterStyles.master_id)
                    .select_from(join(Master, MasterStyles))
                    .where(
                        *filter_type, Master.is_blocked.is_(False), Master.city == city
                    )
                )
                # Все мастера подходящие клиенту
                all_master_client = universal_masters_for_client
            else:
                # Выбирает всех мастеров подходящих клиенту кроме универсальных
                masters_for_client = (
                    select(MasterStyles.master_id)
                    .distinct(MasterStyles.master_id)
                    .select_from(
                        join(MasterStyles, Master).join(
                            ClientStyles, ClientStyles.style_id == MasterStyles.style_id
                        )
                    )
                    .where(
                        *filter_type,
                        ClientStyles.client_id == client_id,
                        Master.city == city,
                    )
                )
                # Выбирает всех универсалов подходящих клиенту
                universal_masters_for_client = (
                    select(MasterStyles.master_id)
                    .select_from(join(Master, MasterStyles))
                    .where(
                        and_(
                            *filter_type,
                            MasterStyles.style_id == NUMBER_ALL_STYLES,
                            Master.city == city,
                        ),
                    )
                )
                # Все мастера подходящие клиенту
                all_master_client = masters_for_client.union_all(
                    universal_masters_for_client
                )

            # Запрос для получения кортежа мастеров
            request = (
                select(
                    Master.master_id,
                    Master.name,
                    Master.city,
                    Master.about_master,
                    count(Likes.master_id).label("count_likes"),
                )
                .select_from(outerjoin(Master, Likes))
                .where(
                    and_(
                        Master.city == city,
                        Master.is_blocked.is_(False),
                        Master.master_id.not_in(all_master_client),
                    )
                )
                .group_by(Master.master_id, Master.name, Master.city)
                .order_by(desc("count_likes"))
            )

            generator_list_masters = await session.execute(request)
            # Получение нужной части мастеров
            number_iter = len_index // len_return + bool(len_index % len_return)
            for _ in range(number_iter):
                value = generator_list_masters.fetchmany(len_return)
                list_tuples_masters = value
            for tuple_master in list_tuples_masters:
                list_master_id.append(tuple_master[0])

            # Получение списка ссылок на фото работ мастера
            photo_path = await get_master_list_photos(session_maker, list_master_id)

            # Получение списка стилей работ мастера
            styles = await get_master_list_selected_styles(
                session_maker, list_master_id
            )

            # Создание словаря Мастера
            for master in list_tuples_masters:
                master_id = master[0]

                master_dict = {
                    "master_id": master_id,
                    "name": master[1],
                    "city": master[2],
                    "about_master": master[3],
                    "styles": styles[master_id],
                    "photo_path": photo_path[master_id],
                    "likes": master[4],
                }
                result.append(master_dict)

        return result

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_ranking_by_like_city: {error}"
        )


async def get_master_ranking_by_like_none(
    session_maker, client_id: int, len_index: int, len_return=1
) -> list[dict]:
    """
    Документация в функции get_master_ranking_by_like_with_except, filtered='none'
    """

    logger.info("*БД* Вызвана функция get_master_ranking_by_like_none")
    try:
        result = []  # Окончательный список словарей с подходящими мастерами
        list_tuples_masters = (
            []
        )  # список кортежей Матеров вида (master_id, name, city, количество лайков)
        list_master_id = []  # список с master_id Мастеров
        async with session_maker() as session:
            # master_id, name, city, tattoo_type, list_styles = client
            client = await get_client_info_and_styles(session_maker, client_id)

            #  Вернет пустой список если клиента нет в базе
            if not client:
                return result

            city: str = client[2]
            tattoo_type: str = client[3]
            list_styles: str = client[4]

            # Проверка типа тату
            if tattoo_type == TATTOO_TYPE_MONOCHROME:
                filter_type = [Master.tattoo_type != TATTOO_TYPE_COLOR]
            elif tattoo_type == TATTOO_TYPE_COLOR:
                filter_type = [Master.tattoo_type != TATTOO_TYPE_MONOCHROME]
            else:
                filter_type = []

            # Если у клиента выбраны ВСЕ СТИЛИ
            if [NUMBER_ALL_STYLES] == list_styles:
                # Выбирает всех универсалов подходящих клиенту
                universal_masters_for_client = (
                    select(MasterStyles.master_id)
                    .distinct(MasterStyles.master_id)
                    .select_from(join(Master, MasterStyles))
                    .where(
                        *filter_type, Master.is_blocked.is_(False), Master.city != city
                    )
                )

                # Все мастера подходящие клиенту
                all_master_client = universal_masters_for_client
            else:
                # Выбирает всех мастеров подходящих клиенту кроме универсальных
                masters_for_client = (
                    select(MasterStyles.master_id)
                    .distinct(MasterStyles.master_id)
                    .select_from(
                        join(MasterStyles, Master).join(
                            ClientStyles, ClientStyles.style_id == MasterStyles.style_id
                        )
                    )
                    .where(
                        *filter_type,
                        ClientStyles.client_id == client_id,
                        Master.city != city,
                    )
                )
                # Выбирает всех универсалов подходящих клиенту
                universal_masters_for_client = (
                    select(MasterStyles.master_id)
                    .select_from(join(Master, MasterStyles))
                    .where(
                        and_(
                            *filter_type,
                            MasterStyles.style_id == NUMBER_ALL_STYLES,
                            Master.city != city,
                        ),
                    )
                )
                # Все мастера подходящие клиенту
                all_master_client = masters_for_client.union_all(
                    universal_masters_for_client
                )

            # Запрос для получения кортежа мастеров
            request = (
                select(
                    Master.master_id,
                    Master.name,
                    Master.city,
                    Master.about_master,
                    count(Likes.master_id).label("count_likes"),
                )
                .select_from(outerjoin(Master, Likes))
                .where(
                    and_(
                        Master.city != city,
                        Master.is_blocked.is_(False),
                        Master.master_id.in_(all_master_client),
                    )
                )
                .group_by(Master.master_id, Master.name, Master.city)
                .order_by(desc("count_likes"))
            )

            generator_list_masters = await session.execute(request)
            # Получение нужной части мастеров
            number_iter = len_index // len_return + bool(len_index % len_return)
            for _ in range(number_iter):
                value = generator_list_masters.fetchmany(len_return)
                list_tuples_masters = value
            for tuple_master in list_tuples_masters:
                list_master_id.append(tuple_master[0])

            # Получение списка ссылок на фото работ мастера
            photo_path = await get_master_list_photos(session_maker, list_master_id)

            # Получение списка стилей работ мастера
            styles = await get_master_list_selected_styles(
                session_maker, list_master_id
            )

            # Создание словаря Мастера
            for master in list_tuples_masters:
                master_id = master[0]

                master_dict = {
                    "master_id": master_id,
                    "name": master[1],
                    "city": master[2],
                    "about_master": master[3],
                    "styles": styles[master_id],
                    "photo_path": photo_path[master_id],
                    "likes": master[4],
                }
                result.append(master_dict)

        return result

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_ranking_by_like_none: {error}"
        )


async def get_master_ranking_by_like_with_except(
    session_maker, client_id: int, len_index, len_return=1, filtered="all"
) -> list[dict]:
    """
    Получает часть от всего списка анкет мастеров, отсортированных по количеству лайков у мастера.
    Получаемые анкеты мастеров фильтруются по городу, и опционально по типу и стилю тату клиента.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - len_index (int): Конечный индекс от общего списка анкет всех подходящих мастеров.
    - len_return (int): Количество анкета мастеров, которые необходимо получить.
    - filtered (str):
        'all' - фильтрация по городу, типу и стилям тату клиента;
        'city' - фильтрация по городу;
        'none' - без фильтров, все не заблокированные мастера.

    Возвращает:
    - Список вида [{'master_id':int, 'name': str, 'city': str, 'about_master': str, 'styles': [str],
     'photo_path': [str], 'likes': int}],
    если нет анкет, подходящих под фильтры, вернёт [].

    Фильтры и сортировка:
        Общие фильтры:
            - Заблокированных не показываем.
            - Фейков показываем
    - filtered='all'
        - Тип тату:
            1) если у клиента выбран тип "Оба варианта", то показываем мастеров с любыми типами тату
            2) если у клиента выбран определенный тип, то показываем мастеров с этим же типом
             или типом "Оба варианта".
        - Стиль тату:
            1) если у клиента выбран "Все стили" показываем мастеров с любыми стилями
            2) если у клиента выбрано несколько стилей показываем тех,
             в чьих списках выбранных стилей содержится стили клиента и мастеров,
              у которых выбрано "Все стили".
        - Город - мастера только из города клиента
    - filtered='city'
        - В этом фильтре не показываем анкеты мастеров, которые были в  filtered='all':
        - Город - мастера только из города клиента.
    - filtered='none'
        - В этом фильтре не показываем анкеты мастеров, которые были в filtered='all' и в
        filtered='city'
        - Такие же фильтры, как в filtered='all', но показываем мастеров не из города клиента.

    Пример применения:
    Количество анкет, которые необходимо получить len_return = 50.
    При len_index = 50 будут возвращены первые 50 анкет. (Индекс списка всех анкет [0:50]
    При len_index = 100 будут возвращены следующие 50 анкет.(Индекс списка всех анкет [50:100])
    При len_index = 150 будет возвращен следующие 50 анкет. (Индекс списка всех анкет [100:150])
    """

    logger.info("*БД* Вызвана функция get_master_ranking_by_like_with_except")
    try:
        result = []
        filtering_values = ["all", "city", "none"]
        if filtered not in filtering_values:
            return result
        if filtered == filtering_values[0]:
            result = await get_master_ranking_by_like_all(
                session_maker, client_id, len_index, len_return
            )
        elif filtered == filtering_values[1]:
            result = await get_master_ranking_by_like_city(
                session_maker, client_id, len_index, len_return
            )
        else:
            result = await get_master_ranking_by_like_none(
                session_maker, client_id, len_index, len_return
            )

        return result

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_ranking_by_like_with_except: {error}"
        )


async def get_master_liked_client(
    session_maker, client_id: int, len_index: int, len_return=1
) -> list[dict]:
    """
    Получает часть от всего списка анкет мастеров, которым клиент поставил лайк,
     отсортированных по количеству лайков у мастера.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - len_index (int): Конечный индекс от общего списка анкет всех подходящих мастеров.
    - len_return (int): Количество анкет мастеров, которые необходимо получить.

    Возвращает:
    - Список вида [{'master_id': int, 'name': str, 'city': str, 'about_master': str,
     'styles': [str], 'photo_path':[str], 'likes': int}], если нет подходящих анкет, вернёт [].


    Пример применения:
    Количество анкет, которые необходимо получить len_return = 50.
    При len_index = 50 будут возвращены первые 50 анкет. (Индекс списка всех анкет [0:50]
    При len_index = 100 будут возвращены следующие 50 анкет.(Индекс списка всех анкет [50:100])
    При len_index = 150 будет возвращен следующие 50 анкет. (Индекс списка всех анкет [100:150]).
    """

    logger.info("*БД* Вызвана функция get_master_liked_client")
    try:
        result = []  # Окончательный список словарей с подходящими мастерами
        list_master_id = []  # список с master_id Мастеров
        master_foto_list = []
        async with session_maker() as session:
            # Получение списка кортежей мастеров
            like_id_list = (
                select(Likes.master_id)
                .select_from(Likes)
                .where(Likes.client_id == client_id)
            )
            request = (
                select(
                    Master.master_id,
                    Master.name,
                    Master.city,
                    Master.about_master,
                    count(Likes.master_id),
                )
                .select_from(Master)
                .join(Likes, isouter=True)
                .where(Master.master_id.in_(like_id_list), Master.is_blocked.is_(False))
                .group_by(
                    Master.master_id, Master.name, Master.city, Master.about_master
                )
                .order_by(count(Likes.master_id).desc())
            )
            generator_list_masters = await session.execute(request)
            number_iter = len_index // len_return + bool(len_index % len_return)
            for _ in range(number_iter):
                value = generator_list_masters.fetchmany(len_return)
                list_tuples_masters = value

            for tuple_master in list_tuples_masters:
                list_master_id.append(tuple_master[0])
            # Получение списка ссылок на фото работ мастера
            add_foto_to_string = func.string_agg(
                MasterPhotos.photo_path,
                aggregate_order_by(literal_column("';'"), MasterPhotos.master_id),
            )
            table_foto_str = await session.execute(
                select(add_foto_to_string)
                .select_from(MasterPhotos)
                .where(MasterPhotos.master_id.in_(list_master_id))
                .group_by(MasterPhotos.master_id)
            )
            for foto_str_row in table_foto_str:
                foto_str = foto_str_row[0]
                foto_split = foto_str.split(";")
                master_foto_list.append(foto_split)
            # Получение списка стилей
            styles_to_string = func.string_agg(
                Styles.style_name,
                aggregate_order_by(literal_column("';'"), MasterStyles.master_id),
            )
            styles_str = await session.execute(
                select(MasterStyles.master_id, styles_to_string)
                .select_from(MasterStyles)
                .join(Styles)
                .where(MasterStyles.master_id.in_(list_master_id))
                .group_by(MasterStyles.master_id)
            )
            style_master_dict = dict(styles_str.all())

            # Создание словаря Мастера
            for master in range(len(list_tuples_masters)):
                master_dict = {
                    "master_id": list_tuples_masters[master][0],
                    "name": list_tuples_masters[master][1],
                    "city": list_tuples_masters[master][2],
                    "about_master": list_tuples_masters[master][3],
                    "styles": style_master_dict[list_master_id[master]].split(";"),
                    "photo_path": master_foto_list[master],
                    "likes": list_tuples_masters[master][4],
                }

                result.append(master_dict)

            return result

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_liked_client: {error}"
        )


async def get_master_new_registered(
    session_maker, client_id: int, len_index: int, len_return=1
) -> list[dict]:
    """
    Получает часть от всего списка анкет мастеров, которые зарегистрировались не позднее 1 недели
    назад.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - len_index (int): Конечный индекс от общего списка анкет всех подходящих мастеров.
    - len_return (int): Количество анкет мастеров, которые необходимо получить.

    Возвращает:
    - Список вида [{'master_id': int, 'name': str, 'city': str, 'about_master': str,
     'styles': [str], 'photo_path':[str], 'likes': int}], если нет подходящих анкет, вернёт [].


    Пример применения:
    При запуске функции 26.07.23-19:55 будут выбраны мастера, которые зарегистрировались
    не раньше 19.07.23-19:55.
    Количество анкет, которые необходимо получить len_return = 50.
    При len_index = 50 будут возвращены первые 50 анкет. (Индекс списка всех анкет [0:50]
    При len_index = 100 будут возвращены следующие 50 анкет.(Индекс списка всех анкет [50:100])
    При len_index = 150 будет возвращен следующие 50 анкет. (Индекс списка всех анкет [100:150]).
    """
    logger.info("*БД* Вызвана функция get_master_new_registered")
    try:
        result = []
        list_tuples_masters = []

        async with session_maker() as session:
            day_ago = datetime.datetime.now() - datetime.timedelta(weeks=1)

            client_city = (
                select(Client.city)
                .where(Client.client_id == client_id)
                .scalar_subquery()
            )
            reg_day_ago = (
                select(Master.master_id)
                .where(and_(Master.city == client_city, Master.date_of_reg > day_ago))
                .scalar_subquery()
            )
            request = (
                select(
                    Master.master_id,
                    Master.name,
                    Master.city,
                    Master.about_master,
                    count(Likes.master_id).label("count_likes"),
                )
                .select_from(outerjoin(Master, Likes))
                .where(
                    and_(
                        Master.master_id.in_(reg_day_ago), Master.is_blocked.is_(False)
                    )
                )
                .group_by(
                    Master.master_id, Master.name, Master.city, Master.about_master
                )
                .order_by(desc("count_likes"))
            )

            generator_masters = await session.execute(request)
            number_iter = len_index // len_return + bool(len_index % len_return)
            for _ in range(number_iter):
                value = generator_masters.fetchmany(len_return)
                if not value:
                    return result
                list_tuples_masters = value
            list_master_id = [master_info[0] for master_info in list_tuples_masters]
            # Получение списка ссылок на фото работ мастера
            photo_path = await get_master_list_photos(session_maker, list_master_id)

            # Получение списка стилей работ мастера
            styles = await get_master_list_selected_styles(
                session_maker, list_master_id
            )

            # Создание словаря Мастера
            for master in list_tuples_masters:
                master_id = master[0]

                master_dict = {
                    "master_id": master_id,
                    "name": master[1],
                    "city": master[2],
                    "about_master": master[3],
                    "styles": styles[master_id],
                    "photo_path": photo_path[master_id],
                    "likes": master[4],
                }
                result.append(master_dict)

        return result

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_new_registered: {error}"
        )
