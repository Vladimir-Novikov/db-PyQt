"""Модуль клиентской части приложения Мессенджер"""


import datetime
import dis
import hmac
import pickle
import sys
import time
from socket import AF_INET, SOCK_STREAM, socket
from threading import Thread

from PyQt5 import QtSql, QtWidgets, uic
from PyQt5.QtSql import QSqlQuery, QSqlTableModel
from PyQt5.QtWidgets import QApplication


contacts = []


def receiving_messages(sock, instance_class_Ui):
    """Получение и разбор сообщений от сервера"""
    while True:
        raw_data = sock.recv(1024)
        data = pickle.loads(raw_data)
        if "chat" in data:
            print(data["from"], " :: ", data["message"], "\n")
        elif "contacts" in data:

            global contacts
            contacts = data["contacts"]

        elif "msg" in data:
            msg_text = data["to"] + " --> " + data["msg"]
            Ui.users_messages(instance_class_Ui, msg_text)

        elif data["response"] > 200:
            Ui.service_messages(instance_class_Ui, data["alert"])  # передаем экз = self и данные
        else:
            pass


def msg_user_to_user(to, message):
    """Подготовка сообщения от юзера - юзеру
    Получили имя отправителя и получателя и сформировали словарь"""
    msg = {
        "action": "msg",
        "time": datetime.datetime.now(),
        "to": to,
        "from_user": user_name,
        "encoding": "ascii",
        "message": message,
    }
    return msg


def get_contacts():
    """Подготовка сообщения для запроса на сервер со списком друзей"""
    msg = {
        "action": "get_contacts",
        "time": time.time(),
        "from_user": user_name,
    }
    return msg


def add_contact(contact_name):
    """Подготовка сообщения для запроса на сервер на добавления юзера в список друзей"""
    msg = {
        "action": "add_contact",
        "time": time.time(),
        "from_user": user_name,
        "contact_name": contact_name,
    }
    return msg


def del_contact():
    """Подготовка сообщения для запроса на сервер на удаление юзера из списка друзей"""
    contact_name = input("Укажите логин удалаемого друга: \n")
    msg = {
        "action": "del_contact",
        "time": time.time(),
        "from_user": user_name,
        "contact_name": contact_name,
    }
    return msg


def user_action(sock, action=0, to_user="", message_text="", login_add_cont=""):
    """Принимает сокет и аргументы, вызывает необходимую функцию для получения шаблона сообщения.
    После чего отправляет сформированное сообщение на сервер"""
    if action == "1":
        sock.send(pickle.dumps(msg_user_to_user(to=to_user, message=message_text)))

    if action == "3":
        my_contacts = get_contacts()
        sock.send(pickle.dumps(my_contacts))

    if action == "4":
        add_cont = add_contact(login_add_cont)
        sock.send(pickle.dumps(add_cont))

    if action == "5":
        del_cont = del_contact()
        sock.send(pickle.dumps(del_cont))


def user_registration(sock, user_login, user_password):
    """Регистрация пользователя до запуска Thread, в окне логирования.
    Возвращает True, если регистрация прошла успешно.
    Либо ответ сервера с описанием проблемы.
    Также возвращает статус пользователя - админ или нет"""
    global user_name
    user_name = user_login
    user_pswrd = user_password
    msg = {
        "action": "authenticate",
        "time": time.time(),
        "user": {"account_name": user_name, "password": user_pswrd},
    }
    sock.send(pickle.dumps(msg))
    data = sock.recv(1024)
    print(pickle.loads(data)["alert"])
    if pickle.loads(data)["response"] == 200:
        return (True, pickle.loads(data)["is_admin"])
    else:
        return pickle.loads(data)["alert"]


class ClientVerifier(type):
    """Метакласс проверки, что класс Client не содержит некорректных для клиентской части вызовов, и что создается TCP/IP сокет"""

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
        """Указание порта и адреса клиентского приложения"""
        self.port = port
        self.addr = addr

    def create_socket(self):
        """Создает сокет"""
        global s
        s = socket(AF_INET, SOCK_STREAM)  # Создать сокет TCP
        s.connect((self.addr, self.port))  # Соединиться с сервером

    def thread_start(instance_class_Ui):  # получили экз класса для отображения сообщений (ф-ция receiving_messages)
        """Запускает поток receiving_messages на прием сообщений"""
        listen = Thread(target=receiving_messages, args=(s, instance_class_Ui))
        listen.start()


Login_form, _ = uic.loadUiType("login.ui")

Message_form, _ = uic.loadUiType("message.ui")

Form, _ = uic.loadUiType("client_gui.ui")

Admin_form, _ = uic.loadUiType("admin.ui")


class Admin(QtWidgets.QDialog, Admin_form):
    """Графическое оформление окна админка"""

    def __init__(self):
        super(Admin, self).__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.get_file_path)  # обработчик нажатия кнопки получения пути до файла
        self.comboBox.currentTextChanged.connect(self.get_item_combo_box)  # обработчик comboBox
        self.pushButton_2.clicked.connect(self.get_info)  # обработчик нажатия кнопки статистики всех клиентов

    def db_connect(self, filename):
        """Подключаемся к БД"""
        conn = QtSql.QSqlDatabase.addDatabase("QSQLITE")
        conn.setDatabaseName(filename)
        conn.open()
        tables_list = conn.tables()[:]  # список всех таблиц в выбранной БД
        if "sqlite_sequence" in tables_list:
            tables_list.remove("sqlite_sequence")  # удаляем служебную таблицу
        self.combo_box(tables_list)

    def combo_box(self, tables_list):
        self.comboBox.clear()  # при смене БД комбобокс очищаем
        self.comboBox.addItems(tables_list)

    def get_item_combo_box(self):
        """Получаем имя текущей таблицы и передаем его в загрузку в tableView"""
        current_db = self.comboBox.currentText()
        self.load_table(current_db)

    def load_table(self, current_db):
        model = QSqlTableModel()
        model.setTable(f"{current_db}")
        model.setEditStrategy(QSqlTableModel.OnFieldChange)  # указываем стратегию (можно менять данные)
        self.tableView.setModel(model)
        model.select()

    def get_file_path(self):
        filename = QtWidgets.QFileDialog.getOpenFileName(self, "Выберите файл БД", "", "*.db *.sqlite *.sqlite3")
        if filename[0]:  # если нажата кнопка ОТМЕНА, то будет пустой путь
            self.label.setText((filename[0]))
            self.db_connect(filename[0])

    def get_info(self):
        """По запросу к БД получает имена всех пользователей и количество отправленных ими сообщений"""
        query = QSqlQuery()
        query = """
            SELECT users.login as 'Пользователь', count(from_user_id) as 'Сообщений' FROM messages inner join users on messages.from_user_id = users.id GROUP BY from_user_id;"""
        q = QSqlQuery(query)
        model = QSqlTableModel()
        model.setQuery(q)
        self.tableView.setModel(model)
        model.select()


class Message_window(QtWidgets.QDialog, Message_form):
    """Графическое оформление окна сообщений"""

    def __init__(self, instance_Ui, recipient):
        super(Message_window, self).__init__()
        self.instance_Ui = instance_Ui  # получили экз класса Ui
        self.recipient = recipient  # получили имя из формы Ui
        self.setupUi(self)
        self.label.setText(f"Сообщение для {self.recipient}")
        self.pushButton.clicked.connect(self.send_message)
        self.pushButton_2.clicked.connect(self.close_message_window)

    def send_message(self):
        """Считывание данных из формы и передача в главное окно для вставки в окно сообщений"""
        user_message = self.textEdit_3.toPlainText()
        user_action(s, action="1", to_user=self.recipient, message_text=user_message)
        my_message = f"{user_name} >>> {self.recipient} --> {user_message}"
        Ui.my_message(self.instance_Ui, my_message)  # передаем свое сообщение в ф-цию
        self.close()

    def close_message_window(self):
        self.close()


class Ui(QtWidgets.QDialog, Form):
    """Графическое оформление главного окна приложения - чат"""

    def __init__(self, login, admin):
        super(Ui, self).__init__()
        self.setupUi(self)
        self.login = login
        self.admin = admin
        self.label.setText(f"Привет {self.login}")
        self.pushButton.clicked.connect(self.show_contacts)
        self.pushButton_3.clicked.connect(self.add_contact)
        self.show_admin()
        self.pushButton_2.clicked.connect(self.admin_gui_start)

    def admin_gui_start(self):
        """Запуск админки по нажатию кнопки"""
        self.w3 = Admin()
        self.w3.show()

    def login_required(func):
        """Декоратор"""

        def wrapper(self):
            if self.admin:
                func(self, True)
            else:
                func(self, False)

        return wrapper

    @login_required
    def show_admin(self, param):
        """Показывать или скрыть кнопку Админка в зависимости от статуса: is admin"""
        if param:
            self.pushButton_2.show()
        else:
            self.pushButton_2.hide()

    def show_contacts(self):
        """Запуск функциии user_action с параметрами. И после получения ответа - проверка есть ли контакты"""
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
        """Выбор получателя сообщения"""
        for recipient in self.listWidget.selectedItems():
            # передаем в новое окно имя получателя и экз класса (для self)
            self.w2 = Message_window(self, recipient.text())
            self.w2.show()

    def add_contact(self):
        """Обработка нажатия кнопки Добавить друга"""
        contact_login = self.textEdit_2.toPlainText()
        if len(contact_login) > 1:
            user_action(s, action="4", login_add_cont=contact_login)
            time.sleep(0.5)
            self.show_contacts()  # автоматически обновляем список
        self.textEdit_2.clear()

    def service_messages(self, data_1):
        """Добавление служебных сообщений сервера в окно"""
        self.listWidget_2.addItem(str(data_1))

    def users_messages(self, message):
        """Добавление адресованный пользователю сообщений в окно"""
        self.listWidget_3.addItem(str(message))

    def my_message(self, message):
        """Добавление своих сообщений в окно"""
        self.listWidget_3.addItem(str(message))

    def closeEvent(self, event):
        print(f"До свидания {user_name}")
        raise KeyboardInterrupt


class Login(QtWidgets.QDialog, Login_form):
    """Графическое оформление окна логирования"""

    def __init__(self):
        super(Login, self).__init__()
        self.setupUi(self)
        self.pushButton.clicked.connect(self.log_in)
        self.hmac_check = self.client_authenticate()

    def client_authenticate(self):
        """Аутентификация клиента на сервере с помощью hmac (до перехода на страницу сообщений)"""
        secret_key = b"secret_key"
        message = s.recv(32)
        hash = hmac.new(secret_key, message, digestmod="sha256")
        digest = hash.digest()
        s.send(digest)
        # получаем еще 1 сообщение для установления статуса сервера в окне
        message = s.recv(32)
        if message == b"error":
            self.label_4.setText("Сервер отклонил подключение: hmac error")
            return False
        else:
            return True

    def log_in(self):
        """Обработка нажатия ОК в окне логирования
        если не прошли hmac, то закрываем окно при нажатии кнопки ОК
        При успешном ответе от сервера также получаем статус - админ/ не админ"""
        if not self.hmac_check:
            self.setWindowOpacity(0.7)
            time.sleep(0.3)
            self.close()
        else:
            user_login = self.textEdit.toPlainText()
            user_password = self.textEdit_2.toPlainText()
            if len(user_login) > 2 and len(user_password) > 2:
                # разбираем ответ user_registration и в зависимости от него устанавливаем текст label_5
                user_registration_response = user_registration(s, user_login, user_password)
                if user_registration_response[0] is True:
                    self.w1 = Ui(
                        user_login, user_registration_response[1]
                    )  # передаем следующему окну имя юзера и статус - админ/не админ
                    self.w1.show()
                    self.close()
                    # стартуем thread на получение сообщений от сервера + передаем экземпляр класса
                    Client.thread_start(self.w1)

                else:
                    self.label_5.setText(user_registration_response)
            self.textEdit.clear()
            self.textEdit_2.clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    client = Client()
    client.create_socket()
    w = Login()
    w.show()
    sys.exit(app.exec_())
