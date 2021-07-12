import pickle
from socket import socket, AF_INET, SOCK_STREAM
import time
import sys
from select import select
import argparse
import logging

# from logs._server_log_decorator import log


# from logs import _server_log_config

"""Раскомментировать этот код в случае применения _client_log_config (без декораторов)"""
# logger = logging.getLogger("app.server")
# logger.info("app start")


"""
декоратор mockable тестируется на функциях: authenticate(), quit_s(), presence()
для этого DEBUG = TRUE и запуск модуля server.py
в консоли выйдyт сообщения response 
"""
DEBUG = False
test_data = {
    "user": {"account_name": "user_mock", "password": "123"},
}


def mockable(func):
    def wrap(*args, **kwargs):
        result = func(**test_data) if DEBUG else func(*args, **kwargs)
        if DEBUG:
            print(result)
        return result

    return wrap


# @log()
# обработка командной строки с параметрами
def createParser():
    # logger.info("parser start")
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default="7777")
    parser.add_argument("-a", "--addr", default="0.0.0.0")
    parser.error = myerror
    return parser


# @log(level="error")
def myerror(message):
    # logger.error(f"parser wrong argument: {message}")
    # print(f"Применен недопустимый аргумент {message}")
    return f"Применен недопустимый аргумент {message}"


def checking_data(r_clients, all_clients):

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
            # logger.error("Длина пакета больше 640")
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
            # "test": test,
        }
        data = pickle.loads(message)
        action = data["action"]
        if action not in dict_of_commands:
            # logger.error("wrong command in message")
            return {"response": 404, "time": time.time(), "error": f"Неизвестная команда {action}"}
        if action == "authenticate":
            return authenticate(sock, **data)
        # if action == "test":
        #     return test(sock, **data)
        processing_the_action = dict_of_commands[action]  # находим в словаре обработчик и присваиваем его переменной
        # logger.info(f"processing {action}")

        return processing_the_action(**data)  # выполняем нужную функцию


# возвращаем сокет

# def test(sock, **kwargs):
#     from_user = kwargs["from"]
#     sock_1 = authorized_users[kwargs["from"]]
#     sock_2 = authorized_users[kwargs["con_to_user"]]
#     return {
#         "test": True,
#         "response": 200,
#         "from_user_sock": "<socket.socket fd=400, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=0, laddr=('127.0.0.1', 7777), raddr=('127.0.0.1', 64433)>",
#         "to_user_sock": "sock_2",
#         "alert": "Сообщение от vova успешно доставлено vova",
#         "to": "vova",
#         "from": "vova",
#         "msg": "hi",
#     }

# return {"test": True, "from_user_sock": authorized_users[from_user], "to_user_sock": authorized_users[con_to_user]}


authorized_users = {}
chat_rooms = {}


# @log(level="info", return_values=2)
@mockable
def authenticate(sock, **kwargs):  # пароль не запрашивается на данном этапе разработки
    user_name = kwargs["user"]["account_name"]
    if user_name in authorized_users:
        # logger.warning(f"уже имеется подключение с указанным логином {user_name}")
        return {
            "response": 409,
            "time": time.time(),
            "alert": f"уже имеется подключение с указанным логином {user_name} ",
            "sock": sock,
        }
    authorized_users[user_name] = sock

    # logger.info(f"Пользователь {user_name} успешно авторизован")
    return {
        "response": 200,
        "time": time.time(),
        "alert": f"Пользователь {user_name} успешно авторизован",
        "from": user_name,
    }


# @log(level="info", return_values=2)
@mockable
def presence(**kwargs):
    user_name = kwargs["user"]["account_name"]
    if user_name in authorized_users:
        # logger.info(f"presence {user_name} присутсвует в списке подключенных пользователей")
        return {
            "response": 200,
            "time": time.time(),
            "alert": f"Хорошо, {user_name} присутсвует в списке подключенных пользователей",
        }
    # logger.error(f"response 404 пользователь {user_name} отсутствует на сервере")
    return {"response": 404, "time": time.time(), "error": f"пользователь {user_name} отсутствует на сервере"}


# @log(level="info", return_values=2)
def msg(**kwargs):
    from_user = kwargs["from_user"]
    to_user = kwargs["to"]
    message = kwargs["message"]
    if from_user not in authorized_users:
        # logger.error(f"response 401 Пользователь {from_user} не авторизован")
        return {
            "response": 401,
            "time": time.time(),
            "alert": f"Пользователь {from_user} не авторизован",
            "from": from_user,
        }

    if to_user[0] == "#":
        chat = to_user[1:]
        if chat not in chat_rooms:
            # logger.error(f"response 404 error Чат {chat} пока не создан")
            return {"response": 404, "time": time.time(), "error": f"Чат {chat} пока не создан"}
        # logger.info(f"Сообщение от {from_user} успешно доставлено в чат {chat}")
        return {
            "response": 200,
            "time": time.time(),
            # "alert": f"Сообщение от {from_user} успешно доставлено в чат {chat}",
            "from": from_user,
            "message": message,  # message вместо msg, чтобы не было ошибок при обработке
            "chat": chat,
        }
    if to_user not in authorized_users:
        # logger.error(f"response 404 Пользователь {to_user} на сервере не зарегистрирован")
        return {
            "response": 404,
            "time": time.time(),
            "alert": f"Пользователь {to_user} на сервере не зарегистрирован",
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


# @log(level="info", return_values=2)
@mockable
def quit_s(**kwargs):
    user_name = kwargs["user"]["account_name"]
    if user_name in authorized_users:

        # т.к. пользователя из словаря мы удалили, получим его сокет для отправки сообщения
        sock = authorized_users.pop(user_name, None)

        return {
            "response": 200,
            "time": time.time(),
            # "alert": f"Пользователь {user_name} успешно отключен от сервера",
            "sock": sock,
            "quit": True,
        }  # передаем ключ quit для завершения потока
    # logger.error(f"response 404 Пользователь {user_name} на сервере не зарегистрирован")
    # return {"response": 404, "time": time.time(), "error": f"Пользователь {user_name} на сервере не зарегистрирован", "from": from_user,}


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


# @log(level="info", return_values=2)
def join(**kwargs):
    chat_name = kwargs["chat_name"]
    user = kwargs["from"]
    if user not in authorized_users:
        # logger.error(f"response 404 пользователь {user} отсутствует на сервере")
        return {"response": 404, "time": time.time(), "error": f"пользователь {user} отсутствует на сервере"}
    if chat_name in chat_rooms:
        if user not in chat_rooms[chat_name]:
            chat_rooms[chat_name].append(user)
            # logger.info(f"Пользователь {user} добавлен в {chat_name}")
            return {
                "response": 200,
                "time": time.time(),
                "alert": f"Пользователь {user} добавлен в {chat_name} ",
            }
        # logger.error(f"response 409 Пользователь {user} уже присутствует в чате {chat_name}")
        return {
            "response": 409,
            "time": time.time(),
            "error": f"Пользователь {user} уже присутствует в чате {chat_name}  ",
        }
    # logger.error(f"response 409 Чат {chat_name} пока не создан")
    return {
        "response": 409,
        "time": time.time(),
        "error": f"Чат {chat_name} пока не создан",
    }


# @log(level="info", return_values=2)
def leave(**kwargs):
    chat_name = kwargs["chat_name"]
    user = kwargs["from_user"]
    if user not in authorized_users:
        # logger.error(f"response 404 пользователь {user} отсутствует на сервере")
        return {"response": 404, "time": time.time(), "error": f"пользователь {user} отсутствует на сервере"}
    if chat_name in chat_rooms:

        if user in chat_rooms[chat_name]:

            chat_rooms[chat_name].remove(user)

            # logger.info(f"Пользователь {user} удален из {chat_name}")
            return {
                "response": 200,
                "time": time.time(),
                "alert": f"Пользователь {user} вышел из чата",
                "message": f"Пользователь {user} вышел из чата",  # эта строка для показа в чате всем пользователям
                "from": user,
                "chat": chat_name,
            }
        # logger.error(f"response 409 Пользователя {user} нет в чате {chat_name}")
        return {
            "response": 409,
            "time": time.time(),
            "error": f"Пользователя {user} нет в чате {chat_name}  ",
        }
    # logger.error(f"response 409 Чат {chat_name} пока не создан")
    return {
        "response": 409,
        "time": time.time(),
        "error": f"Чат {chat_name} пока не создан",
    }


# @log(level="info", return_values=2)
def create(**kwargs):
    chat_name = kwargs["chat_name"]
    user = kwargs["from"]
    if user not in authorized_users:
        # logger.error(f"response 404 пользователь {user} отсутствует на сервере")
        return {"response": 404, "time": time.time(), "error": f"пользователь {user} отсутствует на сервере"}
    if chat_name in chat_rooms:
        # logger.error(f"response 409 уже имеется чат с указанным названием {chat_name}")
        return {
            "response": 409,
            "time": time.time(),
            "alert": f"уже имеется чат с указанным названием {chat_name} ",
        }
    chat_rooms[chat_name] = [user]  # создаем чат и список его участников
    # logger.info(f"Чат {chat_name} успешно создан")
    return {"response": 200, "time": time.time(), "alert": f"Чат {chat_name} успешно создан"}


def write_responses(requests):
    # if "test" in requests:
    #     print(requests)
    #     sock = authorized_users[requests["from"]]
    #     print(sock)
    #     sock.send(pickle.dumps(requests))

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


def main():
    parser = createParser()
    namespace = parser.parse_args(sys.argv[1:])
    clients = []
    with socket(AF_INET, SOCK_STREAM) as s:  # Создает сокет TCP
        s.bind((namespace.addr, int(namespace.port)))  # Присваивает порт
        s.listen(5)  # Переходит в режим ожидания запросов Одновременно обслуживает не более 5 запросов.
        s.settimeout(0.2)
        while True:
            try:
                conn, addr = s.accept()  # Проверка подключений
            except OSError as e:
                pass  # timeout вышел
            else:
                print("Получен запрос на соединение от %s" % str(addr))
                clients.append(conn)
            finally:
                # Проверить наличие событий ввода-вывода
                wait = 10
                r = []
                # w = []
                try:
                    r, w, e = select(clients, [], [], wait)

                except:
                    pass  # Ничего не делать, если какой-то клиент отключился

                requests = checking_data(r, clients)  # Сохраним запросы клиентов

                if requests:
                    write_responses(requests)


if __name__ == "__main__":
    if not DEBUG:
        try:
            main()
        except Exception as er:
            pass

    if DEBUG:
        authenticate()
        quit_s()
        presence()
