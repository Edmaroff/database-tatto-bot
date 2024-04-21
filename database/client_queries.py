from config_data.config import MODEL_RETURN_INDEX_COUNT
from importlib import import_module

from database.db_utils import validate_style_ids
from database.models import (
    Attachments_to_web,
    Client,
    ClientStyles,
    Message_for_dev,
    MessageToWeb,
    Styles,
    Master,
)
from logging_errors.logging_setup import logger

from sqlalchemy import select, exists, delete, update, and_
from sqlalchemy.exc import IntegrityError


async def create_client(
    session_maker,
    client_id: int,
    username: str,
    client_url: str,
    name: str,
    city: str,
    tattoo_type: str,
    is_model: bool,
    is_advertising_allowed: bool = True,
    is_blocked: bool = False,
) -> bool:
    """
    Создает новую запись о клиенте в таблице Client.

    Параметры:
    - client_id (int): ID клиента в Telegram.
    - client_url (str): Ссылка на пользователя.
    - username (str): Логин клиента в Telegram (если логина нет, то = '').
    - name (str): Имя клиента.
    - city (str): Город клиента
    - tattoo_type (str): Тип татуировки, который предпочитает клиент.
    - is_advertising_allowed (bool): Согласен ли пользователь получать рекламу.
    - is_model (bool): Согласен ли пользователь быть моделью.

    Возвращает:
    - True, если клиент создан.
    - False, если клиент уже есть в таблице 'Master'.
    - False, если мастер уже есть в таблице 'Client'.
    """

    logger.info("*БД* Вызвана функция create_client")
    try:
        # Импорт с importlib для избежания цикличного импорта
        master_queries = import_module(".master_queries", package="database")

        if await master_queries.check_master_in_db(session_maker, client_id):
            raise ValueError(f"Telegram ID пользователя {client_id}")

        if not username:
            username = None

        async with session_maker() as session:
            async with session.begin():
                client = Client(
                    client_id=client_id,
                    username=username,
                    client_url=client_url,
                    name=name,
                    city=city,
                    tattoo_type=tattoo_type,
                    is_model=is_model,
                    is_advertising_allowed=is_advertising_allowed,
                    is_blocked=is_blocked,
                )
                session.add(client)
                return True

    except (IntegrityError, ValueError) as client_exists:
        logger.warning(
            f"*БД* Клиент уже есть в БД, функция create_client: {client_exists}"
        )
        return False
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции create_client: {error}")


async def check_client_in_db(session_maker, client_id: int) -> bool:
    """
    Проверяет есть ли пользователь в таблице Client.

    Параметры:
    - client_id (int): Telegram ID пользователя.

    Возвращает:
    - True, если пользователь есть в Client, иначе False.
    """

    logger.info("*БД* Вызвана функция check_client_in_db")
    try:
        async with session_maker() as session:
            query = select(exists().where(Client.client_id == client_id))
            user_exists = await session.scalar(query)
            return user_exists
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции check_client_in_db: {error}")


async def create_client_styles(
    session_maker, client_id: int, style_ids: list[int]
) -> None:
    """
    Создает записи о стилях тату, которые предпочитает клиент, перед созданием
     удаляет записи об уже выбранных стилях в таблице ClientStyles.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - style_ids (list[int]): Список ID стилей из таблицы Styles.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция create_style_client")
    try:
        # Удаление уже выбранных стилей клиента
        await delete_client_style(session_maker, client_id)

        # Проверка style_ids
        style_ids = await validate_style_ids(style_ids)

        async with session_maker() as session:
            async with session.begin():
                for style_id in style_ids:
                    query = select(Styles).where(Styles.style_id == style_id)
                    style = await session.execute(query)
                    style = style.scalar_one_or_none()

                    if style:
                        client_styles = ClientStyles(
                            client_id=client_id, style_id=style_id
                        )
                        session.add(client_styles)
                    else:
                        logger.warning(
                            f"Стиля со style_id={style_id} не существует в Styles"
                        )
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции create_style_client: {error}"
        )


async def get_client_field_value(
    session_maker, client_id: int, field_name: str
) -> bool:
    """
    Получает значение поля field_name для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - field_name (str): Имя поля, значение которого нужно получить.

    Возвращает:
    - Значение поля field_name.
    """

    logger.info("*БД* Вызвана функция get_client_field_value")
    try:
        async with session_maker() as session:
            query = select(getattr(Client, field_name)).where(
                Client.client_id == client_id
            )
            result = await session.execute(query)
            field_value = result.scalar()
            if field_value is not None:
                return field_value
            logger.warning(f"Мастер с client_id={client_id} не найден.")
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_field_value: {error}"
        )


async def get_client_main_info(session_maker, client_id: int) -> dict:
    """
    Получает основную информацию (имя, город, тип тату) о клиенте.

    Параметры:
    - client_id (int): Telegram ID клиента.

    Возвращает:
    dict - Словарь вида {"name": str, "city": str, "tattoo_type": str, "is_model": bool},
     если клиент не найден, вернёт {}.
    """
    logger.info("*БД* Вызвана функция get_client_main_info")
    try:
        async with session_maker() as session:
            client = await session.get(Client, client_id)
            if client:
                return {
                    "name": client.name,
                    "city": client.city,
                    "tattoo_type": client.tattoo_type,
                    "is_model": client.is_model,
                }
            return {}
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_main_info: {error}"
        )


async def get_client_url(session_maker, client_id: int) -> bool:
    """
    Получает значение поля client_url для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.

    Возвращает:
    - Значение поля client_url(ссылка на клиента в Telegram).
    """

    logger.info("*БД* Вызвана функция get_client_url")
    try:
        field_name = "client_url"
        field_value = await get_client_field_value(session_maker, client_id, field_name)
        return field_value
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции get_client_url: {error}")


async def get_client_is_advertising_allowed(session_maker, client_id: int) -> bool:
    """
    Получает значение поля is_advertising_allowed для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.

    Возвращает:
    - Значение поля is_advertising_allowed(согласен ли клиент получать рекламу).
    """

    logger.info("*БД* Вызвана функция get_client_is_advertising_allowed")
    try:
        field_name = "is_advertising_allowed"
        field_value = await get_client_field_value(session_maker, client_id, field_name)
        return field_value
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_is_advertising_allowed: {error}"
        )


async def get_client_is_model(session_maker, client_id: int) -> bool | None:
    """
    Получает значение поля is_model для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.

    Возвращает:
    - Значение поля is_model(согласен ли клиент на тату по себестоимости).
    """

    logger.info("*БД* Вызвана функция get_client_is_model")
    try:
        async with session_maker() as session:
            query = select(Client.is_model).where(Client.client_id == client_id)
            result = await session.scalar(query)
            return result
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_is_model: {error}"
        )


async def get_client_is_bot_usage_consent(session_maker, client_id: int) -> bool:
    """
    Получает значение поля is_bot_usage_consent для указанного клиента из таблицы Client.
    Также является проверкой задавали ли клиенту вопрос "Согласен использовать бота?"

    Параметры:
    - client_id (int): Telegram ID клиента.

    Возвращает:
    - bool - Значение поля is_bot_usage_consent(согласен ли клиент на использование бота).
    True - если задавали вопрос клиенту, иначе False

    """

    logger.info("*БД* Вызвана функция get_client_is_bot_usage_consent")
    try:
        async with session_maker() as session:
            query = select(Client.is_bot_usage_consent).where(
                Client.client_id == client_id
            )
            result = await session.scalar(query)
            return result
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_is_bot_usage_consent: {error}"
        )


async def get_client_is_blocked(session_maker, client_id: int) -> bool:
    """
    Получает значение поля is_blocked для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.

    Возвращает:
    - Значение поля is_blocked (заблокирован ли клиент).
    """

    logger.info("*БД* Вызвана функция get_client_is_blocked")
    try:
        field_name = "is_blocked"
        field_value = await get_client_field_value(session_maker, client_id, field_name)
        return field_value
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_is_blocked: {error}"
        )


async def get_client_ids_by_cities(session_maker) -> list[int]:
    """
    Получает список client_id, которым необходимо отправить рассылку о новых мастерах.
    (Функция используется для рассылки сообщений о новых мастерах)

    Возвращает:
    - list - список client_id. Если не было мастеров,
     которые зарегистрировались не позднее 1 недели назад или клиенты не найдены, вернёт []
    """

    logger.info("*БД* Вызвана функция get_client_ids_by_cities")

    try:
        # Импорт с importlib для избежания цикличного импорта
        master_queries = import_module(".master_queries", package="database")
        cities = await master_queries.get_master_cities_new_registered(session_maker)

        if cities:
            async with session_maker() as session:
                query = select(Client.client_id).where(
                    and_(Client.is_blocked.is_(False), Client.city.in_(cities))
                )
                result = await session.execute(query)
                client_ids = [row[0] for row in result.unique()]
                return client_ids
        else:
            return []
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_ids_by_cities: {error}"
        )


async def get_client_ids_by_city_master(session_maker, master_id: int) -> list[int]:
    """
    (СТАРАЯ ВЕРСИЯ, НЕ ИСПОЛЬЗУЕТСЯ)
    Получает список client_id для клиентов, проживающих в городе мастера(для рассылки).

    Параметры:
    - master_id (int): Telegram ID мастера, по которому происходит поиск.

    Возвращает:
    - Список client_id (list[int]) клиентов. Если клиентов нет в городе мастера, вернёт [].
    """

    logger.info("*БД* Вызвана функция get_client_ids_by_city_master")
    try:
        async with session_maker() as session:
            master_city = (
                select(Master.city)
                .where(Master.master_id == master_id)
                .scalar_subquery()
            )
            client_list = await session.scalars(
                select(Client.client_id).where(
                    and_(
                        Client.city == master_city,
                        Client.is_blocked.is_(False),
                    )
                )
            )
            result = client_list.all()
            return result

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_ids_by_city_master: {error}"
        )


async def get_client_ids_models(
    session_maker,
    master_id: int,
    len_index: int,
    len_return: int = MODEL_RETURN_INDEX_COUNT,
) -> list[dict]:
    """
    Получает список client_id клиентов-моделей, которые проживают в городе мастера.

    Параметры:
    - master_id (int): Telegram ID мастера, по городу которого происходит поиск.
    - len_index (int): Начальный индекс от общего списка всех подходящих клиентов.
    - len_return (int): Количество клиентов, которые необходимо получить.

    Возвращает:
    list[dict] - Список словарей вида {'name': str, 'client_url': str},
     если модели не найдены, вернёт [].

    Пример применения:
    Количество клиентов, которые необходимо получить len_return = 50.
    При len_index = 0 будут возвращены первые 50 клиентов. (Индекс списка всех анкет [0:50]
    При len_index = 50 будут возвращены следующие 50 клиентов.(Индекс списка всех анкет [50:100])
    При len_index = 100 будет возвращен следующие 50 клиентов. (Индекс списка всех анкет [100:150])
    """

    logger.info("*БД* Вызвана функция get_client_ids_models")
    try:
        async with session_maker() as session:
            if len_index < 0:
                return []
            query = (
                select(Client.name, Client.client_url)
                .join(Master, and_(Client.city == Master.city))
                .filter(
                    Master.master_id == master_id,
                    Client.is_model.is_(True),
                    Client.is_blocked.is_(False),
                )
            )
            result = await session.execute(query)
            models = result.fetchall()

            # Определяем начальный и конечный индексы для среза (чтобы не выйти за пределы списка)
            start_index = min(len_index, len(models))
            end_index = min(start_index + len_return, len(models))

            # Формируем список моделей, соответствующих заданному диапазону
            model_list = [
                {"name": model[0], "client_url": model[1]}
                for model in models[start_index:end_index]
            ]
            return model_list
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_ids_models: {error}"
        )


async def get_client_selected_styles(session_maker, client_id: int) -> dict:
    """
    Получает словарь стилей, которые выбрал клиент.

    Параметры:
    - client_id (int): Telegram ID клиента.

    Возвращает:
    - dict - словарь вида {номер стиля (int): название стиля (str)},
     если клиент не найден, вернёт {}.
    """

    logger.info("*БД* Вызвана функция get_client_selected_styles")
    try:
        async with session_maker() as session:
            style_list = await session.execute(
                select(ClientStyles.style_id, Styles.style_name)
                .select_from(ClientStyles)
                .join(Styles)
                .where(ClientStyles.client_id == client_id)
            )
            result = {}
            if style_list:
                result_list = style_list.all()
                for style in result_list:
                    result[style[0]] = style[1]

            return result
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_selected_styles: {error}"
        )


async def update_client_field_value(
    session_maker, client_id: int, field_name: str, new_value: bool | str
) -> None:
    """
    Изменяет значение поля field_name для указанного клиента в таблице Client.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - field_name (str): Имя поля, значение которого нужно изменить.
    - new_value (bool | str): Новое значение поля.

    Возвращает:
    - None
    """

    logger.info("*БД* Вызвана функция update_client_field_value")
    try:
        async with session_maker() as session:
            async with session.begin():
                query = (
                    update(Client)
                    .where(Client.client_id == client_id)
                    .values({field_name: new_value})
                )
                await session.execute(query)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_client_field_value: {error}"
        )


async def update_client_is_advertising_allowed(
    session_maker, client_id: int, new_value: bool
) -> None:
    """
    Обновляет значение поля is_advertising_allowed для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - new_value (bool): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_client_is_advertising_allowed")
    try:
        field_name = "is_advertising_allowed"
        await update_client_field_value(session_maker, client_id, field_name, new_value)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_client_is_advertising_allowed: {error}"
        )


async def update_client_is_model(
    session_maker, client_id: int, new_value: bool
) -> None:
    """
    Обновляет значение поля is_model для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - new_value (bool): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_client_is_model")
    try:
        field_name = "is_model"
        await update_client_field_value(session_maker, client_id, field_name, new_value)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_client_is_model: {error}"
        )


async def update_client_is_bot_usage_consent(
    session_maker, client_id: int, new_value: bool
) -> None:
    """
    Обновляет значение поля is_bot_usage_consent для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - new_value (bool): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_client_is_bot_usage_consent")
    try:
        field_name = "is_bot_usage_consent"
        await update_client_field_value(session_maker, client_id, field_name, new_value)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_client_is_bot_usage_consent: {error}"
        )


async def update_client_name(session_maker, client_id: int, new_value: str) -> None:
    """
    Обновляет значение поля name для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - new_value (str): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_client_name")
    try:
        field_name = "name"
        await update_client_field_value(session_maker, client_id, field_name, new_value)
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции update_client_name: {error}")


async def update_client_city(session_maker, client_id: int, new_value: str) -> None:
    """
    Обновляет значение поля city для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - new_value (str): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_client_city")
    try:
        field_name = "city"
        await update_client_field_value(session_maker, client_id, field_name, new_value)
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции update_client_city: {error}")


async def update_client_tattoo_type(
    session_maker, client_id: int, new_value: str
) -> None:
    """
    Обновляет значение поля tattoo_type для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - new_value (str): Новое значение.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция update_client_tattoo_type")
    try:
        field_name = "tattoo_type"
        await update_client_field_value(session_maker, client_id, field_name, new_value)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_client_tattoo_type: {error}"
        )


async def delete_client(session_maker, client_id: int) -> None:
    """
    Удаляет клиента из таблицы Client и всех связанных таблиц.

    Параметры:
    - client_id (int): ID клиента в Telegram.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция delete_client")
    try:
        async with session_maker() as session:
            async with session.begin():
                query = select(Client).where(Client.client_id == client_id)
                result = await session.execute(query)
                client = result.scalar_one_or_none()
                if client is not None:
                    await session.delete(client)
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции delete_client: {error}")


async def delete_client_style(session_maker, client_id: int) -> None:
    """
    Удаляет все записи из таблицы ClientStyles для указанного client_id.

    Параметры:
    - client_id (int): Telegram ID клиента.

    Возвращает:
    - None.
    """

    logger.info("*БД* Вызвана функция delete_client_style")
    try:
        async with session_maker() as session:
            async with session.begin():
                delete_query = delete(ClientStyles).where(
                    ClientStyles.client_id == client_id
                )
                await session.execute(delete_query)
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции delete_client_style: {error}"
        )
