import socket
import threading
import sys


def login(request):
    request = request.split("_")
    if request[0] == "usrData":
        f = open("vars/users.txt", "r")
        flag = False
        line = f.readline()
        while line:
            line = line.split()
            if line[0] == request[1] and line[1] == request[2]:
                flag = True
            line = f.readline()
        f.close()
    elif request[0] == "regData":
        f = open("vars/users.txt", "a")
        f.write(request[1] + ' ' + request[2] + "\n")
        f.close()
        flag = True
    else:
        flag = False

    if flag:
        return "ok"
    else:
        return "bad"


class Server:
    def __init__(self, ip="127.0.0.1", port=32007):
        self.ip = ip
        self.port = port
        self.users = {}
        self.user_flags = {}
        self.user_num = 0

        self.admin_socket = socket.socket()
        print("Admin_socket: " + self.ip + ":" + str(self.port))
        self.admin_socket.bind((self.ip, self.port))
        self.admin_socket.listen()

        while(True):
            client_socket, client_adress = self.admin_socket.accept()
            threading.Thread(target=self.setup_user, args=(client_socket, client_adress)).start()

    def setup_user(self, client_socket, client_adress):
        data = client_socket.recv(1024)
        data = data.decode()
        result = login(data)
        client_socket.send(result.encode())

        this_num = self.user_num
        self.user_num += 1

        print("User " + client_adress[0] + " result: " + result)
        if result != "ok":
            client_socket.close()
            return 0
        self.users[this_num] = ((data.split('_')[1], client_socket, client_adress))
        self.user_flags[this_num] = True
        while self.user_flags[this_num]:
            try:
                mess = client_socket.recv(1024)
                if mess.decode() != '!exit':
                    print("chat| " + mess.decode())
                    for us in self.users:
                        if self.users[us][2] != client_adress:
                            self.users[us][1].send(mess)
                else:
                    self.user_flags[this_num] = False
            except:
                pass

        self.users.pop(this_num, None)
        self.users.pop(this_num, None)


print("=" * 32)
print("STARTING SERVER")
print("=" * 32)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        ip = sys.argv[1]
        port = int(sys.argv[2])
        rooms = int(sys.argv[3])
        Server(ip, port, rooms)
    else:
        Server()
