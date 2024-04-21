from sqlalchemy import (
    Column,
    Integer,
    Boolean,
    String,
    ForeignKey,
    DateTime,
    UniqueConstraint,
    func,
    BigInteger,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Client(Base):
    """
    Таблица с информацией о клиенте.

    Атрибуты:
    - client_id (int): ID клиента в Telegram.
    - username (str): Логин клиента в Telegram.
    - client_url (str): Ссылка на клиента в Telegram.
    - name (str): Имя клиента.
    - city (str): Город клиента.
    - tattoo_type (str): Тип татуировки клиента (цветная/одноцветная/оба варианта).
    - is_advertising_allowed (bool): Флаг, указывающий, согласен ли пользователь получать
     рекламные сообщения. True - согласен, False - не согласен.
    - is_model (bool): Флаг, указывающий, согласен ли пользователь быть моделью
     (делать тату по себестоимости). True - согласен, False - не согласен.
    - is_bot_usage_consent (bool): Флаг, указывающий согласен ли пользователь использовать бота.
     True - согласен, False - не согласен.
    - is_blocked (bool): Флаг, указывающий, заблокирован ли пользователь в боте.
     True - заблокирован, False - не заблокирован.
    """

    __tablename__ = "client"

    client_id = Column(BigInteger, primary_key=True, autoincrement=False)
    username = Column(String(60), nullable=True)
    client_url = Column(String(130), nullable=False)
    name = Column(String(130), nullable=False)
    city = Column(String(70), nullable=False)
    tattoo_type = Column(String(60), nullable=False)
    date_of_reg = Column(DateTime, nullable=False, server_default=func.now())
    is_advertising_allowed = Column(Boolean, default=True, nullable=False)
    is_model = Column(Boolean, default=False, nullable=False)
    is_bot_usage_consent = Column(Boolean, default=False, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)

    complaints = relationship(
        "Complaints", back_populates="client", cascade="delete, delete-orphan"
    )
    likes = relationship(
        "Likes", back_populates="client", cascade="delete, delete-orphan"
    )
    contact_requests = relationship(
        "ContactRequests", back_populates="client", cascade="delete, delete-orphan"
    )
    styles = relationship(
        "ClientStyles", back_populates="client", cascade="delete, delete-orphan"
    )


class Master(Base):
    """
    Таблица с информацией о мастере.

    Атрибуты:
    - master_id (int): ID мастера в Telegram.
    - master_url (str): Ссылка на мастера в Telegram.
    - username (str): Логин мастера в Telegram.
    - name (str): Имя мастера.
    - city (str): Город мастера.
    - about_master (str): Информация о мастере.
    - tattoo_type (str): Тип татуировки.
    - phone_number (str): Номер телефона.
     в котором работает мастер (цветная/одноцветная/оба варианта).
    - is_notifications_allowed (bool): Флаг, указывающий, согласен ли пользователь получать
     уведомление о лайках клиента. True - согласен, False - не согласен.
    - is_fake (bool): Флаг, указывающий, настоящий это мастер или созданные админами.
     True - настоящий, False - создан админами.
    - is_blocked (bool): Флаг, указывающий, заблокирован ли пользователь в боте.
     True - заблокирован, False - не заблокирован.
    """

    __tablename__ = "master"

    master_id = Column(BigInteger, primary_key=True, autoincrement=False)
    username = Column(String(70), nullable=True)
    master_url = Column(String(140), nullable=False)
    name = Column(String(130), nullable=False)
    city = Column(String(70), nullable=False)
    about_master = Column(String(850), nullable=False)
    tattoo_type = Column(String(60), nullable=False)
    phone_number = Column(String(13), nullable=False)
    date_of_reg = Column(DateTime, nullable=False, server_default=func.now())
    is_notifications_allowed = Column(Boolean, default=False, nullable=False)
    is_fake = Column(Boolean, default=False, nullable=False)
    is_blocked = Column(Boolean, default=False, nullable=False)

    complaints = relationship(
        "Complaints", back_populates="master", cascade="delete, delete-orphan"
    )
    likes = relationship(
        "Likes", back_populates="master", cascade="delete, delete-orphan"
    )
    contact_requests = relationship(
        "ContactRequests", back_populates="master", cascade="delete, delete-orphan"
    )
    styles = relationship(
        "MasterStyles", back_populates="master", cascade="delete, delete-orphan"
    )
    photos = relationship(
        "MasterPhotos", back_populates="master", cascade="delete, delete-orphan"
    )


class Complaints(Base):
    """
    Таблица с информацией о жалобах

    Атрибуты:

    - complaint_id (int): Уникальный идентификатор жалобы.
    - complaint_text (str): Текст жалобы.
    - complaint_date (data): Дата жалобы.

    - client_id (int): Внешний ключ для связи с таблицей Сlient.
    - client (Сlient): Объект связи с таблицей Сlient.

    - master_id (int): Внешний ключ для связи с таблицей Master.
    - master (Master): Объект связи с таблицей Master.
    """

    __tablename__ = "complaints"

    complaint_id = Column(Integer, primary_key=True)
    client_id = Column(BigInteger, ForeignKey("client.client_id"), nullable=False)
    master_id = Column(BigInteger, ForeignKey("master.master_id"), nullable=False)
    complaint_text = Column(String(1200), nullable=False)
    complaint_date = Column(DateTime, nullable=False, server_default=func.now())

    client = relationship("Client", back_populates="complaints")
    master = relationship("Master", back_populates="complaints")


class Likes(Base):
    """
    Таблица с информацией о лайках

    Атрибуты:

    - like_id (int): Уникальный идентификатор лайка.
    - like_date (data): Дата лайка.

    - client_id (int): Внешний ключ для связи с таблицей Сlient.
    - client (Сlient): Объект связи с таблицей Сlient.

    - master_id (int): Внешний ключ для связи с таблицей Master.
    - master (Master): Объект связи с таблицей Master.
    """

    __tablename__ = "likes"

    like_id = Column(Integer, primary_key=True)
    client_id = Column(BigInteger, ForeignKey("client.client_id"), nullable=False)
    master_id = Column(BigInteger, ForeignKey("master.master_id"), nullable=False)
    like_date = Column(DateTime, nullable=False, server_default=func.now())

    client = relationship("Client", back_populates="likes")
    master = relationship("Master", back_populates="likes")

    # Гарантирует, что один клиент не сможет 2 раза лайкнуть на мастера
    __table_args__ = (
        UniqueConstraint("client_id", "master_id", name="unique_client_master_likes"),
    )


class ContactRequests(Base):
    """
    Таблица с информацией о запросах клиента на контакты мастера.

    Атрибуты:
    - request_id (int): Уникальный идентификатор запроса.
    - request_date (data): Дата соединения.

    - client_id (int): Внешний ключ для связи с таблицей Сlient.
    - client (Сlient): Объект связи с таблицей Сlient.

    - master_id (int): Внешний ключ для связи с таблицей Master.
    - master (Master): Объект связи с таблицей Master.
    """

    __tablename__ = "contact_requests"

    request_id = Column(Integer, primary_key=True)
    client_id = Column(BigInteger, ForeignKey("client.client_id"), nullable=False)
    master_id = Column(BigInteger, ForeignKey("master.master_id"), nullable=False)
    request_date = Column(DateTime, nullable=False, server_default=func.now())

    client = relationship("Client", back_populates="contact_requests")
    master = relationship("Master", back_populates="contact_requests")

    # Гарантирует, что один клиент не сможет 2 раза запросить контакты мастера
    __table_args__ = (
        UniqueConstraint("client_id", "master_id", name="unique_client_master_contact"),
    )


class Styles(Base):
    """
    Таблица с информацией о стилях тату.

    Атрибуты:
    - style_id (int): Уникальный идентификатор стиля тату.
    - style_name (str): Название стиля.
    """

    __tablename__ = "styles"

    style_id = Column(Integer, primary_key=True, autoincrement=False)
    style_name = Column(String(70), nullable=False)

    client_styles = relationship("ClientStyles", back_populates="style")
    master_styles = relationship("MasterStyles", back_populates="style")


class ClientStyles(Base):
    """
    Таблица с информацией о стилях тату, которые выбрал клиент.

    Атрибуты:
    - id (int): Уникальный идентификатор стиля.

    - client_id (int): Внешний ключ для связи с таблицей Сlient.
    - client (Сlient): Объект связи с таблицей Сlient.

    - style_id (int): Внешний ключ для связи с таблицей Style.
    - style (Style): Объект связи с таблицей Style.
    """

    __tablename__ = "client_styles"

    id = Column(Integer, primary_key=True)
    client_id = Column(BigInteger, ForeignKey("client.client_id"), nullable=False)
    style_id = Column(Integer, ForeignKey("styles.style_id"), nullable=False)

    client = relationship("Client", back_populates="styles")
    style = relationship("Styles", back_populates="client_styles")

    # Гарантирует, что один клиент не сможет 2 раза выбрать один стиль
    __table_args__ = (
        UniqueConstraint("client_id", "style_id", name="unique_client_styles"),
    )


class MasterStyles(Base):
    """
    Таблица с информацией о стилях тату, которые выбрал мастер.

    Атрибуты:
    - id (int): Уникальный идентификатор стиля мастера.

    - master_id (int): Внешний ключ для связи с таблицей Master.
    - master (Master): Объект связи с таблицей Master.

    - style_id (int): Внешний ключ для связи с таблицей Style.
    - style (Style): Объект связи с таблицей Style.
    """

    __tablename__ = "master_styles"

    id = Column(Integer, primary_key=True)
    master_id = Column(BigInteger, ForeignKey("master.master_id"), nullable=False)
    style_id = Column(Integer, ForeignKey("styles.style_id"), nullable=False)

    master = relationship("Master", back_populates="styles")
    style = relationship("Styles", back_populates="master_styles")

    # Гарантирует, что один мастер не сможет 2 раза выбрать один стиль
    __table_args__ = (
        UniqueConstraint("master_id", "style_id", name="unique_master_styles"),
    )


class MasterPhotos(Base):
    """
    Таблица с фото работ мастеров.

    Атрибуты:
    - photo_id (int): Уникальный идентификатор фото.
    - photo_number (int): Номер фото.
    - photo_path (str): Путь хранения фото.

    - master_id (int): Внешний ключ для связи с таблицей Master.
    - master (Master): Объект связи с таблицей Master.
    """

    __tablename__ = "master_photos"

    photo_id = Column(Integer, primary_key=True)
    master_id = Column(BigInteger, ForeignKey("master.master_id"), nullable=False)
    photo_path = Column(String(400), nullable=False)

    master = relationship("Master", back_populates="photos")
