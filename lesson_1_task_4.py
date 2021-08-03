from subprocess import CREATE_NEW_CONSOLE, Popen

# в данном скрипте также запускаем сервер, т.к. без него клиенты сразу отключатся
# на сервере и на клиенте отключил логирование, т.к. с ним не находит путь до файлов логирования
# связано с путями виндовс \\

number = int(input("Укажите кол-во клиентов: "))
server = Popen("python messenger_app/server.py", creationflags=CREATE_NEW_CONSOLE)
for i in range(number):
    client = Popen("python messenger_app/client_1.py", creationflags=CREATE_NEW_CONSOLE)
print(f" Запущено клиентов: {number}")
