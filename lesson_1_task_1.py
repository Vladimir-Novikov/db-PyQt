import subprocess
import ipaddress


def host_ping(addr_list):
    for address in addr_list:
        ip_address = ipaddress.ip_address(address)
        # отправляем 1 запрос, время ожидания 200 мс, и перенаправляем вывод, чтобы в консоли не было лишней информации
        # p = subprocess.Popen(f"ping -n 1 -w 200 {ip_address}", stdout=subprocess.PIPE) так работает под win
        p = subprocess.Popen(["ping", "-n", "1", "-w", "200", str(ip_address)], stdout=subprocess.PIPE)
        # такой вариант с [] под win и unix, но в unix надо уменьшить -w
        # p.wait()  # ждем завершения процесса, и получаем код завершения (можно через poll())
        if p.wait() == 0:
            print(f"Узел {ip_address} доступен")
        else:
            print(f"Узел {ip_address} НЕДОСТУПЕН")


adresses_list = ["49.12.165.216", "149.12.165.216", "77.88.55.65", "77.88.55.60"]

if __name__ == "__main__":
    host_ping(adresses_list)
