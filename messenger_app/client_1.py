from socket import socket, AF_INET, SOCK_STREAM
import time
import argparse
import pickle
from threading import Thread
import datetime
import dis
import sys


def createParser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default="7777")
    parser.add_argument("-a", "--addr", default="localhost")
    parser.error = myerror

    return parser


def myerror(message):
    return f"Применен недопустимый аргумент {message}"


def receiving_messages(sock):
    while True:
        raw_data = sock.recv(1024)
        data = pickle.loads(raw_data)
        if "chat" in data:
            print(data["from"], " :: ", data["message"], "\n")
        elif "msg" in data:
            print(data["to"], "-->", data["msg"], "\n")  # to тк в msg server они поменяны местами
        elif data["response"] > 200:
            print(data["alert"], "\n")
        else:
            pass


def msg_user_to_user(testing=False):
    if testing:
        message = "Hi"
    else:
        to = input("Кому: ")
        message = input("Сообщение: ")
    msg = {
        "action": "msg",
        "time": datetime.datetime.now(),
        "to": to,
        "from_user": user_name,
        "encoding": "ascii",
        "message": message,
    }
    return msg


def create_quick_chat(testing=False):
    if testing:
        chat_name = "Test_chat"
    else:
        chat_name = input("Укажите название чата: \n")
    msg = {
        "action": "quick_chat",
        "time": time.time(),
        "from": user_name,
        "chat_name": chat_name,
    }
    return msg


def msg_to_chat(chat_name, sock, testing=False):
    while True:
        if testing:
            message = "Test"
        else:
            message = input("")
        if message == "exit":
            msg = {
                "action": "leave",
                "time": time.time(),
                "from_user": user_name,
                "chat_name": chat_name,
            }
            #  пользователя нужно убрать из чата если он вышел
            sock.send(pickle.dumps(msg))
            return
        msg = {
            "action": "msg",
            "time": time.time(),
            "to": "#" + chat_name,
            "from_user": user_name,
            "encoding": "ascii",
            "message": message,
        }
        if testing:
            return msg
        else:
            sock.send(pickle.dumps(msg))


def get_contacts():
    msg = {
        "action": "get_contacts",
        "time": time.time(),
        "from_user": user_name,
    }
    return msg


def add_contact():
    contact_name = input("Укажите логин добавляемого друга: \n")
    msg = {
        "action": "add_contact",
        "time": time.time(),
        "from_user": user_name,
        "contact_name": contact_name,
    }
    return msg


def del_contact():
    contact_name = input("Укажите логин удалаемого друга: \n")
    msg = {
        "action": "del_contact",
        "time": time.time(),
        "from_user": user_name,
        "contact_name": contact_name,
    }
    return msg


def user_action(sock):
    while True:
        while True:
            time.sleep(0.5)  # задерживаем вывод сообщения, для корректного отображения в консоли (в нужном порядке)
            try:
                action = input(
                    "Выберите действие: 1 - сообщение пользователю, 2 - общение в чате, 3 - мои контакты, 4 - добавить контакт, 5 - удалить контакт, exit для выхода: \n"
                )
            except KeyboardInterrupt:
                sys.exit()
            if action == "exit":
                print("Клиент закрыт")
                msg = {
                    "action": "quit",
                    "time": time.time(),
                    "user": {"account_name": user_name},
                }
                sock.send(pickle.dumps(msg))
                raise SystemExit
            if action in ["1", "2", "3", "4", "5"]:
                break
        if action == "1":
            sock.send(pickle.dumps(msg_user_to_user()))

        if action == "2":
            chat = create_quick_chat()
            chat_name = chat["chat_name"]
            sock.send(pickle.dumps(chat))
            print(f"Вы в чате {chat_name}, exit для выхода из чата \n")
            msg_to_chat(chat_name, sock)

        if action == "3":
            my_contacts = get_contacts()
            sock.send(pickle.dumps(my_contacts))

        if action == "4":
            add_cont = add_contact()
            sock.send(pickle.dumps(add_cont))

        if action == "5":
            del_cont = del_contact()
            sock.send(pickle.dumps(del_cont))


def user_registration(sock, testing=False):
    global user_name
    if testing:
        user_name = "Test_name"
    else:
        while True:
            user_name = ""  # сбрасываем имя
            while len(user_name) < 2:

                user_name = input("Введите ваше имя: (минимум 2 знака или exit для выхода): ").strip()

            if user_name == "exit":  # если exit, то return и в main закрываем сокет
                return False
            msg = {
                "action": "authenticate",
                "time": time.time(),
                "user": {"account_name": user_name, "password": ""},
            }
            sock.send(pickle.dumps(msg))
            data = sock.recv(1024)
            print(pickle.loads(data)["alert"])
            if pickle.loads(data)["response"] > 200:
                continue
            else:
                break

    return True


class ClientVerifier(type):
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
        for wrong_commands in ("accept", "listen"):
            if wrong_commands in instructions:
                raise TypeError('В клиенте не может быть вызова "accept" или "listen" для сокета')
        if "AF_INET" and "SOCK_STREAM" in instructions:
            pass
        else:
            raise TypeError("Попытка создания не TCP/IP сокета")
        return type.__new__(cls, clsname, bases, clsdict)


class Client(metaclass=ClientVerifier):
    def __init__(self, port=7777, addr="localhost"):
        self.port = port
        self.addr = addr

    def create_socket(self):
        s = socket(AF_INET, SOCK_STREAM)  # Создать сокет TCP
        s.connect((self.addr, self.port))  # Соединиться с сервером
        if not user_registration(s):  # передаем в функцию сокет, для отправки регистрационных данных
            print("Клиент закрыт")
            s.close()
        else:
            listen = Thread(target=receiving_messages, args=(s,))
            listen.start()
            action = Thread(target=user_action, args=(s,))
            action.start()


if __name__ == "__main__":
    client = Client()
    client.create_socket()
