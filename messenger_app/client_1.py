from socket import socket, AF_INET, SOCK_STREAM
import time
import argparse
import pickle
from threading import Thread
import datetime
import dis
import sys
from PyQt5 import uic, QtWidgets, QtSql, QtCore
from PyQt5.QtSql import QSqlTableModel, QSqlQuery
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QPushButton, QMessageBox, QLineEdit


def createParser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", default="7777")
    parser.add_argument("-a", "--addr", default="localhost")
    parser.error = myerror

    return parser


def myerror(message):
    return f"Применен недопустимый аргумент {message}"


contacts = []


def receiving_messages(sock, instance_class_Ui):
    while True:
        raw_data = sock.recv(1024)
        data = pickle.loads(raw_data)
        if "chat" in data:
            print(data["from"], " :: ", data["message"], "\n")
        elif "contacts" in data:

            global contacts
            contacts = data["contacts"]

        elif "msg" in data:
            # print(data["to"], "-->", data["msg"], "\n")  # to тк в msg server они поменяны местами
            msg_text = data["to"] + " --> " + data["msg"]
            Ui.users_messages(instance_class_Ui, msg_text)
        elif data["response"] > 200:
            # print(data["alert"], "\n")
            Ui.service_messages(instance_class_Ui, data["alert"])  # передаем экз = self и данные
        else:
            pass


def msg_user_to_user(to, message):
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


def add_contact(contact_name):
    # contact_name = input("Укажите логин добавляемого друга: \n")
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


def user_action(sock, action=0, to_user="", message_text="", login_add_cont=""):
    if action == "1":
        sock.send(pickle.dumps(msg_user_to_user(to=to_user, message=message_text)))

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
        add_cont = add_contact(login_add_cont)
        sock.send(pickle.dumps(add_cont))

    if action == "5":
        del_cont = del_contact()
        sock.send(pickle.dumps(del_cont))


def user_registration(sock, user_login):
    global user_name
    user_name = user_login
    msg = {
        "action": "authenticate",
        "time": time.time(),
        "user": {"account_name": user_name, "password": ""},
    }
    sock.send(pickle.dumps(msg))
    data = sock.recv(1024)
    print(pickle.loads(data)["alert"])
    if pickle.loads(data)["response"] == 200:
        return True
    else:
        return False


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
        global s
        s = socket(AF_INET, SOCK_STREAM)  # Создать сокет TCP
        s.connect((self.addr, self.port))  # Соединиться с сервером

    def thread_start(instance_class_Ui):  # получили экз класса для отображения сообщений (ф-ция receiving_messages)
        listen = Thread(target=receiving_messages, args=(s, instance_class_Ui))
        listen.start()


Login_form, _ = uic.loadUiType("login.ui")

Message_form, _ = uic.loadUiType("message.ui")

Form, _ = uic.loadUiType("client_gui.ui")


class Message_window(QtWidgets.QDialog, Message_form):
    def __init__(self, instance_Ui, recipient):
        super(Message_window, self).__init__()
        self.instance_Ui = instance_Ui  # получили экз класса Ui
        self.recipient = recipient  # получили имя из формы Ui
        self.setupUi(self)
        self.label.setText(f"Сообщение для {self.recipient}")
        self.pushButton.clicked.connect(self.send_message)
        self.pushButton_2.clicked.connect(self.close_message_window)

    def send_message(self):
        user_message = self.textEdit_3.toPlainText()
        user_action(s, action="1", to_user=self.recipient, message_text=user_message)
        my_message = f"{user_name} >>> {self.recipient} --> {user_message}"
        Ui.my_message(self.instance_Ui, my_message)  # передаем свое сообщение в ф-цию
        self.close()

    def close_message_window(self):
        self.close()


class Ui(QtWidgets.QDialog, Form):
    def __init__(self, login):
        super(Ui, self).__init__()
        self.setupUi(self)
        self.login = login
        self.label.setText(f"Привет {self.login}")
        self.pushButton.clicked.connect(self.show_contacts)  # обработчик нажатия кнопки
        self.pushButton_3.clicked.connect(self.add_contact)

    def show_contacts(self):
        user_action(s, action="3")

        self.listWidget.clear()  # очищаем поле перед вставкой данных
        time.sleep(0.3)  # установка задержки, т.к. получение данных идет в отдельном потоке
        if contacts:
            for contact in contacts:
                self.listWidget.addItem(str(contact))
            self.listWidget.itemDoubleClicked.connect(self.selecting_recipient)
        else:
            self.listWidget.addItem("Ваш список контактов пуст")

    def selecting_recipient(self):
        for recipient in self.listWidget.selectedItems():
            self.w2 = Message_window(
                self, recipient.text()
            )  # передаем в новое окно имя получателя и экз класса (для self)
            self.w2.show()

    def add_contact(self):
        contact_login = self.textEdit_2.toPlainText()
        if len(contact_login) > 1:
            user_action(s, action="4", login_add_cont=contact_login)
            time.sleep(0.5)
            self.show_contacts()  # автоматически обновляем список
        self.textEdit_2.clear()

    def service_messages(self, data_1):
        self.listWidget_2.addItem(str(data_1))

    def users_messages(self, message):
        self.listWidget_3.addItem(str(message))

    def my_message(self, message):  # отображение своих сообщений
        self.listWidget_3.addItem(str(message))

    def closeEvent(self, event):
        print(f"До свидания {user_name}")
        raise KeyboardInterrupt


class Login(QtWidgets.QDialog, Login_form):
    def __init__(self):
        super(Login, self).__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.log_in)

    def log_in(self):
        user_login = self.textEdit.toPlainText()
        if len(user_login) > 2:
            if user_registration(s, user_login):
                self.w1 = Ui(user_login)
                self.w1.show()
                self.close()
                # стартуем thread на получение сообщений от сервера + передаем экземпляр класса
                Client.thread_start(self.w1)
            else:
                self.label_5.setText("Этот логин уже занят")
        self.textEdit.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = Login()
    w.show()
    client = Client()
    client.create_socket()
    sys.exit(app.exec_())
