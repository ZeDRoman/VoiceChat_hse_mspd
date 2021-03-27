from user_info import get_user_data, get_reg_data
import socket
import threading
import sys
import subprocess 
import time


class Client:
    def __init__(self, ip="130.193.36.61", port=32007):
        self.ip = ip
        self.port = port
        self.main_flag = True
        self.name = "Default"
        self.que = []
        self.voice_room_process = None
        self.voice_room_name = None

        print("=" * 32)
        print("STARTING CLIENT")
        print("=" * 32)

        self.login_to_server()

        res = self.admin_socket.recv(1024)
        print("Connecting to server... result: ", res.decode())
        if res.decode() == "ok":
            print("=" * 32)
            self.chat_reader()

        self.admin_socket.close()

    def login_to_server(self):
        """
        Подключаемся к серверу по существующему пользователю или регестрируя нового.
        """
        start = input("What do you want? (register / login) ")
        while start not in {'login', 'register'}:
            start = input("What do you want? (register / login) ")

        if start == 'login':
            package = get_user_data()
        else:
            package = get_reg_data()

        server_socket = socket.socket()
        server_socket.connect((self.ip, self.port))

        self.name = package.split("_")[1]

        server_socket.send(package.encode())

        self.admin_socket = server_socket

    def chat_reader(self):
        writ = threading.Thread(target=self.chat_writter)
        writ.daemon = True
        writ.start()

        while self.main_flag:

            message = input()
            if message == '!exit':
                self.main_flag = False
                mes = message
                self.admin_socket.send(mes.encode())
            elif message.startswith('!join'):
                if self.voice_room_process is not None:
                    print('You already are in room {}'.format(self.voice_room_name))
                else:
                    self.voice_room_name = message.split()[1]
                    self.voice_room_process = subprocess.Popen(['python3', 'pythonclient.py', '', self.voice_room_name])
            elif message == '!leave':
                if self.voice_room_process is None:
                    print('You are not in the room')
                else:
                    self.voice_room_process.kill()
            else:
                mes = self.name + ": " + message
                self.admin_socket.send(mes.encode())
                self.que.append(mes)

        f = open("chat_log.txt", "w")
        for el in self.que:
            f.write(el + '\n')
        f.close()

    def chat_writter(self):

        while self.main_flag:
            in_message = self.admin_socket.recv(1024)
            self.que.append(in_message.decode())
            print(in_message.decode())


if __name__ == '__main__':
    if len(sys.argv) > 1:
        ip = sys.argv[1]
        port = int(sys.argv[2])
        Client(ip, port)
    else:
        Client()
