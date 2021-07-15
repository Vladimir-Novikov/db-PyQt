# серверная часть *********************************
import dis


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
    port = PortVerifier()

    def __init__(self, port=7777, addr="0.0.0.0"):
        self.port = port
        self.addr = addr

    def create_socket(self):
        clients = []
        with socket(AF_INET, SOCK_STREAM) as s:  # Создает сокет TCP
            s.bind((self.addr, int(self.port)))  # Присваивает порт
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
                    try:
                        r, w, e = select(clients, [], [], wait)
                    except:
                        pass  # Ничего не делать, если какой-то клиент отключился

                    requests = checking_data(r, clients)  # Сохраним запросы клиентов

                    if requests:
                        write_responses(requests)


if __name__ == "__main__":
    # если классу Server не передавать значение порта, то используем умолчание = 7777
    # при передаче некорректного номера, также используем умолчание = 7777
    server = Server()
    server.create_socket()


# клиентская часть ****************************************


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
