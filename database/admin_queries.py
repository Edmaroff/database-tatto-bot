from database.models import Master, Client
from database.master_queries import create_master

from logging_errors.logging_setup import logger

from sqlalchemy.exc import ProgrammingError
from sqlalchemy.sql.functions import count
from sqlalchemy import select, update, desc, exists, and_


async def create_fake_master(
    session_maker,
    master_id: int,
    username: str,
    master_url: str,
    name: str,
    city: str,
    about_master: str,
    tattoo_type: str,
    phone_number: str,
) -> None:
    """
    Создает новую запись о фейковом мастере в таблице Master. Создает специальный master_id
    для фейковых мастеров.

    Параметры:
    - username (str): Логин мастера в Telegram.
    - name (str): Имя мастера.
    - city (str): Город мастера.
    - about_master (str): Информация о мастере.
    - tattoo_type (str): Тип татуировки, в котором работает мастер: Цветная,Однотонная,Оба варианта.
    - phone_number (str): Телефон мастера, по-умолчанию +79123456789.

    Возвращает:
    - None
    """

    logger.info("*БД* Вызвана функция create_fake_master")

    try:
        await create_master(
            session_maker,
            master_id=master_id,
            username=username,
            master_url=master_url,
            name=name,
            city=city,
            about_master=about_master,
            tattoo_type=tattoo_type,
            phone_number=phone_number,
            is_fake=True,
        )
    except Exception as error:
        logger.exception(f"*БД* Произошла ошибка в функции create_fake_master: {error}")


async def check_master_fake_in_db(session_maker, master_id: int) -> bool:
    """
    Проверяет есть ли фейковый мастер в таблице Master.

    Параметры:
    - master_id (int): Telegram ID пользователя.

    Возвращает:
    - True, если мастер есть в Master и он фейк, иначе False.
    """

    logger.info("*БД* Вызвана функция check_master_fake_in_db")
    try:
        async with session_maker() as session:
            query = select(
                exists().where(
                    and_(Master.master_id == master_id, Master.is_fake.is_(True))
                )
            )
            user_exists = await session.scalar(query)
            return user_exists
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции check_master_fake_in_db: {error}"
        )


async def get_stats_for_admin(session_maker) -> dict:
    """
    Получает статистику по пользователям бота для админов:
    - Общее количество мастеров, Количество фейковых мастеров, Количество заблокированных мастеров,
    Общее количество клиентов, Количество заблокированных клиентов.

    Возвращает:
    - dict - Словарь со статистикой по пользователям.
    """
    logger.info("*БД* Вызвана функция get_stats_for_admin")
    try:
        requests = []
        async with session_maker() as session:
            for request in [Master, Client]:
                count_users_all = select(count()).select_from(request)
                requests.append(count_users_all)
                count_users_blocked = (
                    select(count())
                    .select_from(request)
                    .where(request.is_blocked.is_(True))
                )
                requests.append(count_users_blocked)
            count_master_fake = (
                select(count()).select_from(Master).where(Master.is_fake.is_(True))
            )
            requests.append(count_master_fake)

            client_list = await session.scalars(
                requests[0].union_all(
                    requests[4], requests[1], requests[2], requests[3]
                )
            )
            result_list = client_list.all()
            return {
                "Общее число мастеров": result_list[0],
                "Число фейковых мастеров": result_list[1],
                "Число заблокированных мастеров": result_list[2],
                "Общее число клиентов": result_list[3],
                "Число заблокированных клиентов": result_list[4],
            }

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_stats_for_admin: {error}"
        )


async def get_master_id_by_url(session_maker, master_url: str) -> int | None:
    """
    Получает master_id по master_url в таблице Master.

    Параметры:
    - master_url (str): Ссылка на мастера в Telegram.

    Возвращает:
    - int | None: master_id, если мастер с заданным URL найден, иначе вернёт None.
    """
    logger.info("*БД* Вызвана функция get_master_id_by_url")
    try:
        async with session_maker() as session:
            query = select(Master.master_id).where(Master.master_url == master_url)
            result = await session.execute(query)
            master_id = result.scalar_one_or_none()
            return master_id
    except ProgrammingError:
        pass
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_id_by_url: {error}"
        )


async def get_master_ids_for_mailing(session_maker) -> list[int]:
    """
    Получает список всех не заблокированных master_id для рассылки администрации.

    Возвращает:
    - Список master_id (list[int]) мастеров. Если мастеров нет, вернёт [].
    """

    logger.info("*БД* Вызвана функция get_master_ids_for_mailing")
    try:
        async with session_maker() as session:
            query = select(Master.master_id).where(
                and_(Master.is_blocked.is_(False), Master.is_fake.is_(False))
            )
            result = await session.execute(query)
            master_ids = [row[0] for row in result]
        return master_ids

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_ids_for_mailing: {error}"
        )


async def get_master_all_fakes(session_maker) -> list[dict]:
    """
    Получает список master_id всех фейковых мастеров.

    Возвращает:
    - list[dict]: Список словарей вида {'master_id': int, 'name': str, 'city': str},
     если нет фейковых мастеров, вернёт [].
    """

    logger.info("*БД* Вызвана функция get_master_all_fakes")
    try:
        async with session_maker() as session:
            query = select(Master.master_id, Master.city, Master.name).where(
                Master.is_fake.is_(True)
            )
            result = await session.execute(query)
            fake_masters_list = [
                {
                    "master_id": master.master_id,
                    "name": master.name,
                    "city": master.city,
                }
                for master in result.all()
            ]
            return fake_masters_list
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_all_fakes: {error}"
        )


async def get_master_main_info_for_admin(session_maker, master_id: int) -> dict:
    """
    Получает основную информацию
    (имя, город, тип тату, номер телефона, информация о себе, логин, ссылка) о мастере для админов.

    Параметры:
    - master_id (int): Telegram ID мастера.

    Возвращает:
    - dict - Словарь вида:
    {"name": str, "city": str, "tattoo_type": str, "phone_number": str, "about_master": str,
    "username":str, "master_url": str}, если мастер не найден или мастер не является фейком,
     вернёт {}.
    """
    logger.info("*БД* Вызвана функция get_master_main_info")
    try:
        async with session_maker() as session:
            master = await session.get(Master, master_id)
            if master and master.is_fake:
                main_info_master = {
                    "master_id": master.master_id,
                    "name": master.name,
                    "city": master.city,
                    "tattoo_type": master.tattoo_type,
                    "phone_number": master.phone_number,
                    "about_master": master.about_master,
                    "username": master.username,
                    "master_url": master.master_url,
                }
                return main_info_master
            return {}
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_master_main_info: {error}"
        )


async def update_master_is_blocked(
    session_maker, master_id: int, new_value: bool
) -> bool:
    """
    Обновляет значение поля is_blocked для указанного мастера из таблицы Master.

    Параметры:
    - master_id (int): Telegram ID мастера.
    - new_value (bool): Новое значение.

    Возвращает:
    - bool - True, если обновление прошло успешно, иначе False.
    """

    logger.info("*БД* Вызвана функция update_master_is_blocked")
    try:
        async with session_maker() as session:
            async with session.begin():
                query = (
                    update(Master)
                    .where(Master.master_id == master_id)
                    .values(is_blocked=new_value)
                )
                result = await session.execute(query)
                affected_rows = result.rowcount
                return affected_rows > 0
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_master_is_blocked: {error}"
        )


async def get_client_id_by_url(session_maker, client_url: str) -> int | None:
    """
    Получает client_id по client_url в таблице Client.

    Параметры:
    - client_url (str): Ссылка на клиента в Telegram.

    Возвращает:
    - int | None: client_id, если клиент с заданным URL найден, иначе вернёт None.
    """
    logger.info("*БД* Вызвана функция get_client_id_by_url")
    try:
        async with session_maker() as session:
            query = select(Client.client_id).where(Client.client_url == client_url)
            result = await session.execute(query)
            client_id = result.scalar_one_or_none()
            return client_id

    except ProgrammingError:
        pass
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_id_by_url: {error}"
        )


async def get_client_ids_for_mailing(session_maker) -> list[int]:
    """
    Получает список всех не заблокированных client_id для рассылки администрации.

    Возвращает:
    - Список client_id (list[int]) клиентов. Если клиентов нет, вернёт [].
    """

    logger.info("*БД* Вызвана функция get_client_ids_for_mailing")
    try:
        async with session_maker() as session:
            query = select(Client.client_id).where(Client.is_blocked.is_(False))
            result = await session.execute(query)
            client_ids = [row[0] for row in result]
            return client_ids

    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции get_client_ids_for_mailing: {error}"
        )


async def update_client_is_blocked(
    session_maker, client_id: int, new_value: bool
) -> bool:
    """
    Обновляет значение поля is_blocked для указанного клиента из таблицы Client.

    Параметры:
    - client_id (int): Telegram ID клиента.
    - new_value (bool): Новое значение.

    Возвращает:
    - bool - True, если обновление прошло успешно, иначе False.
    """

    logger.info("*БД* Вызвана функция update_client_is_blocked")
    try:
        async with session_maker() as session:
            async with session.begin():
                query = (
                    update(Client)
                    .where(Client.client_id == client_id)
                    .values(is_blocked=new_value)
                )
                result = await session.execute(query)
                affected_rows = result.rowcount
                return affected_rows > 0
    except Exception as error:
        logger.exception(
            f"*БД* Произошла ошибка в функции update_client_is_blocked: {error}"
        )
