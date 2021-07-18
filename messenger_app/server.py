import pickle
from socket import socket, AF_INET, SOCK_STREAM
import time
import datetime
from select import select
import argparse
import dis
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Session
from sqlalchemy import exc


# класс работы с БД
class Storage:
    engine = create_engine("sqlite:///server_sqlite.db")
    engine.connect()
    Base = declarative_base()
    session = Session(bind=engine)

    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True)
        login = Column(String(100), nullable=False, unique=True)
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
        friend_name = Column("friend_name", String)

    Base.metadata.create_all(engine)

    def db_write_user(login, info, db=User, engine=engine):
        session = Session(bind=engine)
        data = db(login=login, info=info)
        try:
            session.add(data)
            session.commit()
        except exc.IntegrityError:  # Все имена уникальны, при попытке записать в бд ловим исключение
            #  в функции authenticate это уже проверяется для текущей сессии
            pass

    def get_user_id(user_name, db=User, engine=engine):
        session = Session(bind=engine)
        user_id = session.query(db.id).filter(db.login == user_name).first()
        return user_id  # возвращаем ID нужного пользователя

    def db_write_history(user_id, ip, time, db=History, engine=engine):
        session = Session(bind=engine)
        data = db(user_id=user_id, ip=ip, enter_time=time)
        session.add(data)
        session.commit()

    def db_write_contact(user_id, friend_id, friend_name, db=Contact, engine=engine):
        session = Session(bind=engine)
        data = db(user_id=user_id, friend_id=friend_id, friend_name=friend_name)
        session.add(data)
        session.commit()

    def friend_exist(user_id, friend_id, db=Contact, engine=engine):
        session = Session(bind=engine)
        exist = session.query(db.friend_id).filter(db.user_id == user_id).all()
        if (friend_id,) in exist:  # сравниваем кортеж со списком кортежей
            return False
        return True  # если нет в списке, то вернем True и запишем


# обработка командной строки с параметрами
def createParser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default="7777")
    parser.add_argument("-a", "--addr", default="0.0.0.0")
    parser.error = myerror
    return parser


def myerror(message):
    return f"Применен недопустимый аргумент {message}"


def checking_data(r_clients, ip, all_clients):

    for sock in r_clients:
        try:
            message = sock.recv(1024)
        except:
            print("Клиент {} {} отключился".format(sock.fileno(), sock.getpeername()))
            all_clients.remove(sock)
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


def authenticate(sock, ip, **kwargs):  # пароль не запрашивается на данном этапе разработки
    user_name = kwargs["user"]["account_name"]
    if user_name in authorized_users:
        return {
            "response": 409,
            "time": time.time(),
            "alert": f"уже имеется подключение с указанным логином {user_name} ",
            "sock": sock,
        }

    Storage.db_write_user(user_name, "-")  # записываем в БД всех пользователей при авторизации
    user_id = Storage.get_user_id(user_name)  #  получаем ID юзера
    now = datetime.datetime.now()
    Storage.db_write_history(*user_id, ip, now)  # записываем в таблицу history IP и время входа
    authorized_users[user_name] = sock

    return {
        "response": 200,
        "time": time.time(),
        "alert": f"Пользователь {user_name} успешно авторизован",
        "from": user_name,
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


def msg(**kwargs):
    from_user = kwargs["from_user"]
    to_user = kwargs["to"]
    message = kwargs["message"]

    # в БД друзей добавляем даже если в данный момент адресат не в сети.
    # сообщение не будет доставлено, но запись в БД о друге добавим
    # но в любом случае проверяем есть ли адресат в БД, те. правильное ли имя указал пользователь

    from_user_id = Storage.get_user_id(from_user)  # получаем ID юзера - отправителя (его добавим в друзья)
    to_user_id = Storage.get_user_id(to_user)  # проверяем есть ли получатель в БД (правильное ли имя),и получаем его ID

    if to_user_id is not None:
        # проверим нет ли отправителя уже в списке друзей если есть, то не пишем его в БД, если нет - пишем
        # если True, то нужно записать в список друзей
        if Storage.friend_exist(*to_user_id, *from_user_id):
            Storage.db_write_contact(*to_user_id, *from_user_id, from_user)

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

    sock = authorized_users[requests["from"]]  # ответы сервера возвращаем тому, кто отправил запрос
    sock.send(pickle.dumps(requests))


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
                except OSError as e:
                    pass  # timeout вышел
                else:
                    print("Получен запрос на соединение от %s" % str(addr))
                    clients.append(conn)
                finally:
                    # Проверить наличие событий ввода-вывода
                    wait = 10
                    r = []
                    try:
                        r, w, e = select(clients, [], [], wait)
                    except:
                        pass  # Ничего не делать, если какой-то клиент отключился

                    requests = checking_data(r, ip, clients)  # Сохраним запросы клиентов

                    if requests:
                        write_responses(requests)


if __name__ == "__main__":
    # если классу Server не передавать значение порта, то используем умолчание = 7777
    # при передаче некорректного номера, также используем умолчание = 7777
    server = Server()
    server.create_socket()
    db_sqlite = Storage()
    db_sqlite
