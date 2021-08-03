import argparse
import datetime
import dis
import hashlib
import hmac
import os
import pickle
import time
from select import select
from socket import AF_INET, SOCK_STREAM, socket

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, String,
                        create_engine, exc)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship


# класс работы с БД
class Storage:
    engine = create_engine("sqlite:///messenger_sqlite.db")
    engine.connect()
    Base = declarative_base()
    session = Session(bind=engine)

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        login = Column(String(100), nullable=False, unique=True)
        password = Column(String(100), nullable=False)
        is_admin = Column(Integer(), nullable=False)
        info = Column(String(100), nullable=False)

        history = relationship("History")
        contacts = relationship("Contact")

    class History(Base):
        __tablename__ = "history"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        ip = Column(String(20))
        enter_time = Column(DateTime())

    class Contact(Base):
        __tablename__ = "contacts"
        id = Column(Integer, primary_key=True)
        user_id = Column(Integer, ForeignKey("users.id"))
        friend_id = Column(Integer)

    class Message(Base):
        __tablename__ = "messages"
        id = Column(Integer, primary_key=True)
        from_user_id = Column(Integer, ForeignKey("users.id"))
        to_user_id = Column(Integer, ForeignKey("users.id"))
        message = Column(String(100))
        time = Column(DateTime())

    Base.metadata.create_all(engine)

    def db_write_user(login, password, is_admin, info, db=User, engine=engine):
        session = Session(bind=engine)
        data = db(login=login, password=password, is_admin=is_admin, info=info)
        try:
            session.add(data)
            session.commit()
        except exc.IntegrityError:  # Все имена уникальны, при попытке записать в бд ловим исключение
            #  в функции authenticate это уже проверяется для текущей сессии
            pass

    # проверяем есть ли записи в таблице users, если нет, то первому юзеру назначаем админа (id мб не обязательно 1, т.к. до этого могли быть удаления юзеров админом и прочее)
    def users_records_exist(db=User, engine=engine):
        session = Session(bind=engine)
        rows_count = session.query(db).count()
        return rows_count

    def get_user_id(user_name, db=User, engine=engine):
        session = Session(bind=engine)
        user_id = session.query(db.id).filter(db.login == user_name).first()
        return user_id  # возвращаем ID нужного пользователя

    def db_write_history(user_id, ip, time, db=History, engine=engine):
        session = Session(bind=engine)
        data = db(user_id=user_id, ip=ip, enter_time=time)
        session.add(data)
        session.commit()

    def db_write_contact(user_id, friend_id, db=Contact, engine=engine):
        session = Session(bind=engine)
        data = db(user_id=user_id, friend_id=friend_id)
        session.add(data)
        session.commit()

    def friend_exist(user_id, friend_id, db=Contact, engine=engine):
        session = Session(bind=engine)
        exist = session.query(db.friend_id).filter(db.user_id == user_id).all()
        if (friend_id,) in exist:  # сравниваем кортеж со списком кортежей
            return False
        return True  # если нет в списке, то вернем True и запишем

    def get_contacts(user_id, db_1=Contact, db_2=User, engine=engine):
        id_list = []
        name_list = []
        session = Session(bind=engine)
        contacts_id = session.query(db_1.friend_id).filter(db_1.user_id == user_id).all()

        for el in contacts_id:  # создаем лист для вложенного запроса в contacts_name
            id_list.append(*el)

        contacts_name = session.query(db_2.login).filter(db_2.id.in_(id_list))
        results = contacts_name.all()

        for name in results:  # создаем лист с именами друзей
            name_list.append(*name)

        return name_list

    def db_del_contact(user_id, friend_id, db=Contact, engine=engine):
        session = Session(bind=engine)
        row_to_del = session.query(db).filter(db.user_id == user_id, db.friend_id == friend_id).one()
        session.delete(row_to_del)
        session.commit()

    def db_write_message(from_user, to_user, message, time, db=Message, engine=engine):
        session = Session(bind=engine)
        data = db(from_user_id=from_user, to_user_id=to_user, message=message, time=time)
        session.add(data)
        session.commit()

    def password_check(user_id, hash_password, db=User, engine=engine):
        session = Session(bind=engine)
        db_hash_password = session.query(db.password).filter(db.id == user_id).one()
        # сравниваем два кортежа, для этого hash_password превратили в кортеж
        return db_hash_password == (hash_password,)

    def db_user_is_admin(user_name, db=User, engine=engine):
        session = Session(bind=engine)
        is_user_admin = session.query(db.is_admin).filter(db.login == user_name).one()
        if is_user_admin == (1,):
            return True
        return False


# обработка командной строки с параметрами
def createParser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default="7777")
    parser.add_argument("-a", "--addr", default="0.0.0.0")
    parser.error = myerror
    return parser


def myerror(message):
    return f"Применен недопустимый аргумент {message}"


def get_key(users_dict, value):
    for k, v in users_dict.items():
        if v == value:
            return k


def checking_data(r_clients, ip, all_clients):

    for sock in r_clients:
        try:
            message = sock.recv(1024)
        except Exception:
            print("Клиент {} {} отключился".format(sock.fileno(), sock.getpeername()))
            all_clients.remove(sock)
            # если юзер закрыл программу - удаляем его из списка подключенных
            user_name_key = get_key(authorized_users, sock)
            try:
                del authorized_users[user_name_key]
            except KeyError:
                pass

        # если клиент набрал exit, то False, и дальнейшие условия не проверяем (без этого сервер вылетал)

        if len(message) == 0:
            return False

        if len(message) > 640:  # проверка длины пакета
            return {
                "response": 400,
                "time": time.time(),
                "error": "Длина объекта больше 640 символов",
            }

        dict_of_commands = {
            "authenticate": authenticate,
            "presence": presence,
            "msg": msg,
            "quit": quit_s,  # т.к. в python есть ф-ция quit - определил для ф-ции другое имя
            "join": join,
            "leave": leave,
            "create": create,
            "quick_chat": quick_chat,
            "get_contacts": get_contacts,
            "add_contact": add_contact,
            "del_contact": del_contact,
        }
        data = pickle.loads(message)
        action = data["action"]
        if action not in dict_of_commands:

            return {"response": 404, "time": time.time(), "error": f"Неизвестная команда {action}"}
        if action == "authenticate":
            return authenticate(sock, ip, **data)

        processing_the_action = dict_of_commands[action]  # находим в словаре обработчик и присваиваем его переменной

        return processing_the_action(**data)  # выполняем нужную функцию


authorized_users = {}
chat_rooms = {}


def hash_pass(salt, password):  # в качестве соли добавляем имя пользователя
    hash_password = hashlib.sha256(salt.encode() + password.encode()).hexdigest()
    return hash_password


def authenticate(sock, ip, **kwargs):
    user_name = kwargs["user"]["account_name"]
    user_password = kwargs["user"]["password"]
    hash_password = hash_pass(user_name, user_password)
    user_id = Storage.get_user_id(user_name)  # проверяем есть ли юзер в БД
    now = datetime.datetime.now()
    if user_id is not None:  # если юзер уже есть в базе - сравниваем хэш паролей
        if Storage.password_check(*user_id, hash_password):
            if user_name in authorized_users:
                # закоментировать этот return если должна быть возможность входа со многих устройств
                return {
                    "response": 409,
                    "time": time.time(),
                    "alert": f"уже имеется подключение с логином {user_name} ",
                    "sock": sock,
                    "from": user_name,
                }

            Storage.db_write_history(*user_id, ip, now)  # записываем в таблицу history IP и время входа
            authorized_users[user_name] = sock

            return {
                "response": 200,
                "time": time.time(),
                "alert": f"Пользователь {user_name} успешно авторизован",
                "from": user_name,
                "is_admin": Storage.db_user_is_admin(user_name),
            }

        else:
            return {
                "response": 409,
                "time": time.time(),
                "alert": "Неправильный пароль",
                "sock": sock,
                "from": user_name,
            }

    # если в таблице users нет записей, то устанавливаем первому юзеру статус админ. В дальнейшем адиминистратор через админку сам сможет назначить администраторов
    # id мб не обязательно 1, т.к. до этого могли быть удаления юзеров админом и прочее
    if Storage.users_records_exist() == 0:
        Storage.db_write_user(login=user_name, password=hash_password, is_admin=1, info="-")
    else:
        Storage.db_write_user(
            login=user_name, password=hash_password, is_admin=0, info="-"
        )  # записываем в БД всех пользователей при авторизации
    user_id = Storage.get_user_id(user_name)  # получаем ID юзера для дальнейших записей в БД

    Storage.db_write_history(*user_id, ip, now)  # записываем в таблицу history IP и время входа
    authorized_users[user_name] = sock

    return {
        "response": 200,
        "time": time.time(),
        "alert": f"Пользователь {user_name} успешно авторизован",
        "from": user_name,
        "is_admin": Storage.db_user_is_admin(user_name),
    }


def presence(**kwargs):
    user_name = kwargs["user"]["account_name"]
    if user_name in authorized_users:

        return {
            "response": 200,
            "time": time.time(),
            "alert": f"Хорошо, {user_name} присутсвует в списке подключенных пользователей",
        }
    return {"response": 404, "time": time.time(), "error": f"пользователь {user_name} отсутствует на сервере"}


def add_contact(**kwargs):
    from_user = kwargs["from_user"]
    contact_name = kwargs["contact_name"]
    from_user_id = Storage.get_user_id(from_user)  # получаем ID юзера - отправителя
    # проверяем есть ли добавляемое имя в БД (правильное ли имя), и получаем его ID
    to_user_id = Storage.get_user_id(contact_name)

    if to_user_id is not None and (
        from_user_id != to_user_id
    ):  # дополнительно убедимся, что пользователь добавил не себя
        # проверим нет ли отправителя уже в списке друзей если есть, то не пишем его в БД, если нет - пишем
        # если True, то нужно записать в список друзей
        if Storage.friend_exist(*to_user_id, *from_user_id):
            Storage.db_write_contact(*to_user_id, *from_user_id)

        if Storage.friend_exist(*from_user_id, *to_user_id):  # также отправителю добавляем получателя в друзья
            Storage.db_write_contact(*from_user_id, *to_user_id)

        return {  # если добавляемый юзер есть в БД, то возвращаем ОК, даже если он уже был в друзьях
            "response": 202,
            "time": time.time(),
            "alert": "OK",
            "from": from_user,
        }

    return {  # если добавляемого юзера нет в БД, то возвращаем Предупреждение
        "response": 400,
        "time": time.time(),
        "alert": "Такого пользователя нет на сервере / или указан собственный логин",
        "from": from_user,
    }


def del_contact(**kwargs):
    from_user = kwargs["from_user"]
    contact_name = kwargs["contact_name"]
    from_user_id = Storage.get_user_id(from_user)  # получаем ID юзера - отправителя
    to_user_id = Storage.get_user_id(contact_name)  # получаем ID юзера - друга

    if to_user_id is not None and (
        from_user_id != to_user_id
    ):  # дополнительно убедимся, что пользователь указал не себя
        # проверим есть ли друг в списке друзей

        if not Storage.friend_exist(*from_user_id, *to_user_id):  # тк ф-ция возвращает false, если друг найден, то not
            Storage.db_del_contact(*from_user_id, *to_user_id)

            # отправителя из списка друзей удаленного друга не удаляем

            return {
                "response": 202,
                "time": time.time(),
                "alert": "OK",
                "from": from_user,
            }

    return {  # если добавляемого юзера нет в БД, то возвращаем Предупреждение
        "response": 400,
        "time": time.time(),
        "alert": "Такого пользователя нет на сервере или в списке друзей, или указан собственный логин",
        "from": from_user,
    }


def msg(**kwargs):
    from_user = kwargs["from_user"]
    to_user = kwargs["to"]
    message = kwargs["message"]
    now = kwargs["time"]
    # в друзья добавляем всех, кто отправил пользователю сообщение (и можно отдельно добавлять см. отдельную ф-цию)
    # в БД друзей добавляем даже если в данный момент адресат не в сети.
    # сообщение не будет доставлено, но запись в БД о друге добавим
    # но в любом случае проверяем есть ли адресат в БД, те. правильное ли имя указал пользователь

    from_user_id = Storage.get_user_id(from_user)  # получаем ID юзера - отправителя (его добавим в друзья)
    to_user_id = Storage.get_user_id(to_user)  # проверяем есть ли получатель в БД (правильное ли имя),и получаем его ID

    if to_user_id is not None and (
        from_user_id != to_user_id
    ):  # дополнительно убедимся, что пользователь отправил сообщение не себе
        # проверим нет ли отправителя уже в списке друзей если есть, то не пишем его в БД, если нет - пишем
        # если True, то нужно записать в список друзей
        if Storage.friend_exist(*to_user_id, *from_user_id):
            Storage.db_write_contact(*to_user_id, *from_user_id)

        if Storage.friend_exist(*from_user_id, *to_user_id):  # также отправителю добавляем получателя в друзья
            Storage.db_write_contact(*from_user_id, *to_user_id)

        # сохранение сообщений (всех кроме чата) и если получатель указан верно, те. ошибочные не сохраняем
        # но если получатель есть в бд, но не в сети, то сохраним это сообщение
        Storage.db_write_message(*from_user_id, *to_user_id, message, now)

    if from_user not in authorized_users:
        return {
            "response": 401,
            "time": time.time(),
            "alert": f"Пользователь {from_user} не авторизован",
            "from": from_user,
        }

    if to_user[0] == "#":
        chat = to_user[1:]
        if chat not in chat_rooms:
            return {"response": 404, "time": time.time(), "error": f"Чат {chat} пока не создан"}
        return {
            "response": 200,
            "time": time.time(),
            "from": from_user,
            "message": message,  # message вместо msg, чтобы не было ошибок при обработке
            "chat": chat,
        }
    if to_user not in authorized_users:
        return {
            "response": 404,
            "time": time.time(),
            "alert": f"Пользователь {to_user} не в сети",
            "from": from_user,
        }

    return {
        "response": 200,
        "time": time.time(),
        "alert": f"Сообщение от {from_user} успешно доставлено {to_user}",
        "to": from_user,  # from to поменяны местами, тк сообщение нужно доставить не автору, а адресату
        "from": to_user,
        "msg": message,
    }


def get_contacts(**kwargs):
    from_user = kwargs["from_user"]
    user_id = Storage.get_user_id(from_user)  # получаем id пользователя - инициатора запроса
    user_contacts = Storage.get_contacts(*user_id)
    return {
        "response": 202,
        "time": time.time(),
        "contacts": user_contacts,
        # "alert": user_contacts,
        "from": from_user,
    }


def quit_s(**kwargs):
    user_name = kwargs["user"]["account_name"]
    if user_name in authorized_users:

        # т.к. пользователя из словаря мы удалили, получим его сокет для отправки сообщения
        sock = authorized_users.pop(user_name, None)

        return {
            "response": 200,
            "time": time.time(),
            "sock": sock,
            "quit": True,
        }  # передаем ключ quit для завершения потока


def quick_chat(**kwargs):
    chat_name = kwargs["chat_name"]
    user = kwargs["from"]
    if chat_name in chat_rooms:
        if user not in chat_rooms[chat_name]:
            chat_rooms[chat_name].append(user)
            return {
                "response": 200,
                "time": time.time(),
                "alert": f"Пользователь {user} добавлен в {chat_name} ",
                "from": user,
            }
        return {
            "response": 200,
            "time": time.time(),
            "alert": f"Пользователь {user} уже в чате {chat_name} ",
            "from": user,
        }

    chat_rooms[chat_name] = [user]
    return {
        "response": 200,
        "time": time.time(),
        "alert": f"Создан чат {chat_name} с пользователем {user}",
        "from": user,
    }


def join(**kwargs):
    chat_name = kwargs["chat_name"]
    user = kwargs["from"]
    if user not in authorized_users:
        return {"response": 404, "time": time.time(), "error": f"пользователь {user} отсутствует на сервере"}
    if chat_name in chat_rooms:
        if user not in chat_rooms[chat_name]:
            chat_rooms[chat_name].append(user)
            return {
                "response": 200,
                "time": time.time(),
                "alert": f"Пользователь {user} добавлен в {chat_name} ",
            }

        return {
            "response": 409,
            "time": time.time(),
            "error": f"Пользователь {user} уже присутствует в чате {chat_name}  ",
        }
    return {
        "response": 409,
        "time": time.time(),
        "error": f"Чат {chat_name} пока не создан",
    }


def leave(**kwargs):
    chat_name = kwargs["chat_name"]
    user = kwargs["from_user"]
    if user not in authorized_users:

        return {"response": 404, "time": time.time(), "error": f"пользователь {user} отсутствует на сервере"}
    if chat_name in chat_rooms:

        if user in chat_rooms[chat_name]:

            chat_rooms[chat_name].remove(user)

            return {
                "response": 200,
                "time": time.time(),
                "alert": f"Пользователь {user} вышел из чата",
                "message": f"Пользователь {user} вышел из чата",  # эта строка для показа в чате всем пользователям
                "from": user,
                "chat": chat_name,
            }
        return {
            "response": 409,
            "time": time.time(),
            "error": f"Пользователя {user} нет в чате {chat_name}  ",
        }
    return {
        "response": 409,
        "time": time.time(),
        "error": f"Чат {chat_name} пока не создан",
    }


def create(**kwargs):
    chat_name = kwargs["chat_name"]
    user = kwargs["from"]
    if user not in authorized_users:
        return {"response": 404, "time": time.time(), "error": f"пользователь {user} отсутствует на сервере"}
    if chat_name in chat_rooms:
        return {
            "response": 409,
            "time": time.time(),
            "alert": f"уже имеется чат с указанным названием {chat_name} ",
        }
    chat_rooms[chat_name] = [user]  # создаем чат и список его участников
    return {"response": 200, "time": time.time(), "alert": f"Чат {chat_name} успешно создан"}


def write_responses(requests):
    if "sock" in requests:  # если имя пользователя уже занято или он отключился, то ответ возвращаем по сокету.
        sock = requests.pop("sock", None)
        sock.send(pickle.dumps(requests))
        return

    if "chat" in requests:  # сообщение в чат
        author = authorized_users[requests["from"]]  # сокет автора сообщения (отсылаем всем, кроме него)
        list_of_users = chat_rooms[requests["chat"]]  # получаем список участников чата
        for user_name in list_of_users:  # проходимся списку пользователей, для получения сокета и последующей отправки
            sock = authorized_users[user_name]
            if sock != author:
                sock.send(pickle.dumps(requests))
        return

    try:
        sock = authorized_users[requests["from"]]  # ответы сервера возвращаем тому, кто отправил запрос
        sock.send(pickle.dumps(requests))
    except ConnectionResetError:  # [WinError 10054] Удаленный хост принудительно разорвал существующее подключение
        pass
    except KeyError:  # если клиент закрыл свое приложение, то отправлять ответ некому, тк. из authorized_users клиента удалили в ф-ции checking_data
        pass


class PortVerifier:
    # дескриптор, проверяющий значение номера порта
    # если значение выходит за установленные рамки, то используем умолчание = 7777
    def __get__(self, instance, owner):
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        if not (1 <= value <= 65535):
            value = 7777
        instance.__dict__[self.name] = value

    def __set_name__(self, owner, name):
        self.name = name


class ServerVerifier(type):
    def __new__(cls, clsname, bases, clsdict):
        instructions = []
        for key in clsdict:
            try:
                instr = dis.get_instructions(clsdict[key])
            except TypeError:
                pass
            for item in instr:
                load_list = ["LOAD_ATTR", "LOAD_METHOD", "LOAD_GLOBAL"]
                if item.opname in load_list:
                    instructions.append(item.argval)
        if "connect" in instructions:
            raise TypeError('На серверной части не может быть вызова "connect" для сокета')
        if "AF_INET" and "SOCK_STREAM" in instructions:
            pass
        else:
            raise TypeError("Попытка создания не TCP/IP сокета")
        return type.__new__(cls, clsname, bases, clsdict)


class Server(metaclass=ServerVerifier):

    port = PortVerifier()  # используем дескриптор

    def __init__(self, port=7777, addr="0.0.0.0"):
        self.port = port
        self.addr = addr

    def create_socket(self):
        clients = []
        ip = ""
        with socket(AF_INET, SOCK_STREAM) as s:  # Создает сокет TCP
            s.bind((self.addr, int(self.port)))  # Присваивает порт
            s.listen(5)  # Переходит в режим ожидания запросов Одновременно обслуживает не более 5 запросов.
            s.settimeout(0.2)
            while True:
                try:
                    conn, addr = s.accept()  # Проверка подключений
                    ip = addr[0]
                except OSError:
                    pass  # timeout вышел
                else:
                    print("Получен запрос на соединение от %s" % str(addr))
                    # если hmac не пройдена, то закрываем подключение
                    if not Server.server_authenticate(conn):
                        print("Клиент %s не прошел аутентификаию hmac" % str(addr))
                        conn.close()
                    else:
                        clients.append(conn)
                finally:
                    # Проверить наличие событий ввода-вывода
                    wait = 10
                    r = []
                    try:
                        r, w, e = select(clients, [], [], wait)
                    except Exception:
                        pass  # Ничего не делать, если какой-то клиент отключился
                    try:
                        requests = checking_data(r, ip, clients)  # Сохраним запросы клиентов
                    except UnboundLocalError:
                        pass
                    if requests:
                        write_responses(requests)

    def server_authenticate(conn):
        secret_key = b"secret_key"
        message = os.urandom(32)
        conn.send(message)
        # 2. Вычисляется HMAC-функция от послания с использованием секретного ключа
        hash = hmac.new(secret_key, message, digestmod="sha256")
        digest = hash.digest()
        # # 3. Пришедший ответ от клиента сравнивается с локальным результатом HMAC
        response = conn.recv(len(digest))
        # посылаем клиенту еще 1 сообщение для установления статуса в окне логирования
        # чтобы клиент увидел статус сервера
        if hmac.compare_digest(digest, response):
            status_message = b"ok"
        else:
            status_message = b"error"
        conn.send(status_message)
        return hmac.compare_digest(digest, response)


if __name__ == "__main__":
    # если классу Server не передавать значение порта, то используем умолчание = 7777
    # при передаче некорректного номера, также используем умолчание = 7777
    server = Server()
    server.create_socket()
    db_sqlite = Storage()
    db_sqlite
