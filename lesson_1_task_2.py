import subprocess


def host_range_ping():
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
    address = ".".join(octets)
    print(f"Начинаем перебор IP адресов в диапазоне {address}.0-255")

    for i in range(256):
        ip_address = address + "." + str(i)
        p = subprocess.Popen(["ping", "-n", "1", "-w", "200", str(ip_address)], stdout=subprocess.PIPE)
        if p.wait() == 0:
            print(f"Узел {ip_address} доступен")
        else:
            print(f"Узел {ip_address} НЕДОСТУПЕН")


if __name__ == "__main__":
    host_range_ping()
