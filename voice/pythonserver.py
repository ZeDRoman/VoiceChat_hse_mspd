from time import sleep
from threading import Thread, Lock, Condition
import pickle
import socket

SOCK_IP = '10.130.0.35'
# SOCK_IP = '10.130.0.35'
# SOCK_IP = '84.252.129.57'
# SOCK_IP = '130.193.36.61'
SOCK_PORT = 9001

class Client:
    availableClients = {}  # {'client name' : client object}
    rooms = {} # {'room_name': set(clients)}
    # client_room = {} # {'client_name': 'room_name'}


    def __init__(self, client_ptr):
        self.cl_ptr = client_ptr
        self.name = None
        self.name = self.get_name()
        self.room_name = None
        self.room_name = self.get_room_name()
        if self.room_name not in Client.rooms:
            Client.rooms[self.room_name] = set()
        Client.rooms[self.room_name].add(self.name)
        print(f"received name {self.name} and recipient {self.room_name}")
        Client.availableClients[self.name] = self
        try:
            self.lobby()
        except ConnectionResetError:
            print("CONNECTION RESET ERROR")
            self.close()
        except BrokenPipeError:
            print("BROKEN PIPE. Closing connection")
            self.close()

    def lobby(self):
        self.cl_ptr[0].send('go'.encode())
        self.converse()
        self.close()

    # Enter a loop to keep searching for recipient in available clients

    def get_name(self):
        if self.name is None:
            # receive name
            self.name = self.cl_ptr[0].recv(512).decode().rstrip()
            print(f"Client connected: {self.name}")
        return self.name

    def get_room_name(self):
        if self.room_name is None:
            # receive recipient name
            self.room_name = self.cl_ptr[0].recv(512).decode().rstrip()
            print(f"Client {self.name} wants to connect to {self.room_name}")
        return self.room_name

    # def getRecipientSocket(self):
    #     search list of available clients

    def converse(self):
        print("establishing connection...")
        try:
            while True:
                if self.get_name() not in Client.availableClients:
                    self.close()
                data = self.read()
                #print('name : {}, room: {}'.format(self.get_name(), Client.rooms[self.get_room_name()]))
                room = Client.rooms[self.get_room_name()].copy()
                for name in room:
                    try:
                        user = Client.availableClients.get(name)
                        if name != self.name:
                            # print('sent from {} to {}'.format(self.name, name))
                            self.send(user, data)
                    except Exception as e:
                        try:
                            Client.rooms[self.get_room_name()].remove(name)
                            Client.availableClients.pop(name, None)
                        except:
                            pass
                        print('Ex : {}'.format(e))
        except KeyboardInterrupt:
            print('KeyboardInterrupt')
            self.close()
        except OSError as e:
            print('Os error: {}'.format(e))
            self.close()

    def send(self, cl_object, data):
        cl_object.cl_ptr[0].send(data)

    def read(self):
        return self.cl_ptr[0].recv(10240)

    def close(self):
        try:
            Client.availableClients.pop(self.get_name(), None)
            self.cl_ptr[0].close()
            print(f"Client {self.name} removed.")
        except:
            pass

def main():
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"binding socket on {SOCK_IP}:{SOCK_PORT}")
    serversocket.bind((SOCK_IP, SOCK_PORT))
    serversocket.listen(3)

    threads = {}

    while True:
        try:
            client_id = (serversocket.accept(),)
            threads[client_id] = Thread(target=client_handler, args=client_id)
            threads[client_id].start()
        except KeyboardInterrupt:
            serversocket.close()
            break

def client_handler(clientid):
    Client(clientid)

main()
