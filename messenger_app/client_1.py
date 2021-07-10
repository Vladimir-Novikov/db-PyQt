from socket import socket, AF_INET, SOCK_STREAM
import time
import sys
import argparse
import pickle
import logging
from threading import Thread
import time


# from logs import _client_log_config
# from logs._client_log_decorator import log

"""Раскомментировать этот код в случае применения _client_log_config (без декораторов)"""
# logger = logging.getLogger("app.client")
# logger.info("app start")


# @log()
def createParser():
    # logger.info("parser start")
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default="7777")
    parser.add_argument("-a", "--addr", default="localhost")
    parser.error = myerror

    return parser


# @log("error")
def myerror(message):
    # print(f"Применен недопустимый аргумент {message}")
    return f"Применен недопустимый аргумент {message}"


# @log()
def receiving_messages(sock):
    while True:
        raw_data = sock.recv(1024)
        data = pickle.loads(raw_data)
        if "chat" in data:
            print(data["from"], " :: ", data["message"], "\n")
        # if "quit" in data:
        #     return False
        elif "msg" in data:
            print(data["to"], "-->", data["msg"], "\n")  # to тк в msg server они поменяны местами
        elif data["response"] > 200:
            print(data["alert"], "\n")
        else:
            pass


# @log()
def msg_user_to_user(testing=False):
    if testing:
        message = "Hi"
    else:
        to = input("Кому: ")
        message = input("Сообщение: ")
    msg = {
        "action": "msg",
        "time": time.time(),
        "to": to,
        "from_user": user_name,
        "encoding": "ascii",
        "message": message,
    }
    return msg


# @log()
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


# @log()
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


# @log()
def user_action(sock):
    while True:
        while True:
            time.sleep(0.5)  # задерживаем вывод сообщения, для корректного отображения в консоли (в нужном порядке)
            action = input("Выберите действие: 1 - сообщение пользователю, 2 - общение в чате, exit для выхода: \n")
            if action == "exit":
                print("Клиент закрыт")
                msg = {
                    "action": "quit",
                    "time": time.time(),
                    "user": {"account_name": user_name},
                }
                sock.send(pickle.dumps(msg))
                return False
            if action in ["1", "2"]:
                break
        if action == "1":
            sock.send(pickle.dumps(msg_user_to_user()))

        if action == "2":
            chat = create_quick_chat()
            chat_name = chat["chat_name"]
            sock.send(pickle.dumps(chat))
            print(f"Вы в чате {chat_name}, exit для выхода из чата \n")
            msg_to_chat(chat_name, sock)


# @log()
def main():
    parser = createParser()
    namespace = parser.parse_args(sys.argv[1:])
    s = socket(AF_INET, SOCK_STREAM)  # Создать сокет TCP
    s.connect((namespace.addr, int(namespace.port)))  # Соединиться с сервером
    if not user_registration(s):  # передаем в функцию сокет, для отправки регистрационных данных
        print("Клиент закрыт")
        s.close()
    else:
        listen = Thread(target=receiving_messages, args=(s,))
        listen.start()
        action = Thread(target=user_action, args=(s,))
        action.start()


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


if __name__ == "__main__":
    try:
        main()
    except Exception as er:
        pass


"""
образцы сообщений
msg = {
    "action": "authenticate",
    "time": time.time(),
    "user": {"account_name": "C0deMaver1ck", "password": "CorrectHorseBatteryStaple"},
}
msg = {
    "action": "quit",
    "time": time.time(),
    "type": "status",
    "user": {"account_name": "C0deMaver1ck", "status": "Yep, I am here!"},
}
msg = {
    "action": "presence",
    "time": time.time(),
    "type": "status",
    "user": {"account_name": "C0deMaver1ck", "status": "Yep, I am here!"},
}
msg = {
    "action": "msg",
    "time": time.time(),
    "to": "C0deMaver1ck",
    "from": "User_1",
    "encoding": "ascii",
    "message": "message"
}
msg = {
    "action": "create",
    "time": time.time(),
    "from": "C0deMaver1ck",
    "chat_name": "My_chat",
}
msg = {
    "action": "join",
    "time": time.time(),
    "from": "User_1",
    "chat_name": "My_chat",
}
msg = {
    "action": "leave",
    "time": time.time(),
    "from": "User_1",
    "chat_name": "My_chat",
}
"""