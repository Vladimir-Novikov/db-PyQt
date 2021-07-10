import subprocess
from tabulate import tabulate


def host_range_ping_tab():
    reachable = []
    unreachable = []
    number_of_octets = 0
    while number_of_octets < 3:
        three_octets = input("Введите первые 3 октета IP адреса через пробел (числа от 0 до 255): ").split()[:3]
        number_of_octets = 0
        octets = []
        for octet in three_octets:
            try:
                number = int(octet[:3])
                number_of_octets += 1
                if number < 0 or number > 255:
                    number_of_octets = 0
                    print("Вводить можно только числа от 0 до 255")
                octets.append(octet[:3])
            except ValueError:
                print("Вводить можно только числа")
                number_of_octets = 0
    adress = ".".join(octets)
    print(f"Начинаем перебор IP адресов в диапазоне {adress}.0-255")

    for i in range(256):
        ip_address = adress + "." + str(i)
        p = subprocess.Popen(["ping", "-n", "1", "-w", "100", str(ip_address)], stdout=subprocess.PIPE)
        if p.wait() == 0:
            reachable.append(ip_address)
        else:
            unreachable.append(ip_address)

    # после того, как разложили адреса по двум спискам, дополняем короткий список для корректной работы ф-ции zip

    if len(reachable) > len(unreachable):
        while len(unreachable) != len(reachable):
            unreachable.append("")
    if len(unreachable) > len(reachable):
        while len(reachable) != len(unreachable):
            reachable.append("")

    total_list = list(zip(reachable, unreachable))
    headers_list = ["Reachable", "Unreachable"]
    print(tabulate(total_list, headers=headers_list, tablefmt="grid"))  # печать таблицы


if __name__ == "__main__":
    host_range_ping_tab()
