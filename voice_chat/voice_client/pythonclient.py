print("client started")
print("_________________________________________________________________________________")

# client sends self id
# client sends recipient id
# client sends data


from threading import Thread, Lock, Condition
import json
import sys
import socket
import sounddevice as sd
from time import sleep
import pickle
import numpy as np
import random
from Crypto.Cipher import AES
from socket import timeout
import argparse
# socket connect to the server

LEN = 1024
NUM = 3

DELIMITER = b'|DELIMITER|'
SERVER_IP = '130.193.36.61'
SERVER_PORT = 9001
BUFMAX = 512
running = True
mutex_t = Lock()
item_available = Condition()
# SLEEPTIME = 0.00001
SLEEPTIME = 0.000001
audio_available = Condition()

i_sdstream = sd.InputStream(samplerate=44100, channels=1, dtype='float32', latency='low')
o_sdstream = sd.OutputStream(samplerate=44100, channels=1, dtype='float32')
i_sdstream.start()
o_sdstream.start()

key = b'thisisthepasswordforAESencryptio'
# random.seed(input("ENTER RANDOM SEED :"))
random.seed('changethisrandomseed')
# iv_seed = hash(hash(key))
# random.seed(iv_seed)
iv = ''.join([chr(random.randint(0, 0xFF)) for i in range(16)])
iv = iv.encode()
cipher = AES.new(key, AES.MODE_CBC, iv[:16])
# nonce = cipher.nonce
# ciphertext, tag = cipher.encrypt_and_digest(data)
def get_iv():
    return (''.join([chr(random.randint(0, 0xFF)) for i in range(16)])).encode()[:16]

def decrypt(enc_data):
    cphr = AES.new(key, AES.MODE_CBC, enc_data[:16])
    decoded = cphr.decrypt(enc_data)[16:]
    return decoded.rstrip()

def encrypt(data_string):
    iv = get_iv()
    cphr = AES.new(key, AES.MODE_CBC, iv)
    d = iv + data_string
    d = (d + (' ' * (len(d) % 16)).encode())
    d = d[:(0 - (len(d) % 16))]

    return cipher.encrypt(d)

class SharedBuf:
    def __init__(self):
        self.buffer = np.array([], dtype='float32')

    def clearbuf(self):
        self.buffer = []

    def addbuf(self, arr):
        self.buffer = np.append(self.buffer, arr)
    def extbuf(self, arr):
        self.buffer = np.append(self.buffer, arr)
    def getlen(self):
        return len(self.buffer)
    def getbuf(self):
        return self.buffer
    def getx(self, x):
        data = self.buffer[0:x]
        self.buffer = self.buffer[x:]
        return data


def callibrate():
    global running
    if running:
        i_sdstream.read(i_sdstream.read_available)

# record t seconds of audio
def record(t):
    global running
    if running:
        return i_sdstream.read(t)[0]


def transmit(buf, socket):
    global running
    # print(f"PICKLED VAL ____ = {pickle.dumps(buf)}")
    pickled = pickle.dumps(buf) + DELIMITER
    # print(f"PICKLED ______ =  {pickled}")
    encrypted_str = pickled #encrypt(pickled)
    # print(len(pickled))
    # decrypted = decrypt(encrypted_str)
    # print(f"PICKLED ___ENC = {decrypted}")
    try:
        socket.send(encrypted_str)
    except timeout:
        print("SOCKET TIMEOUT 2")
        running = False
    except BrokenPipeError:
        print("Recipient disconnected")
        running = False


def record_transmit_thread(serversocket):
    print("***** STARTING RECORD TRANSMIT THREAD *****")
    tbuf = SharedBuf()
    global running

    def recorder_producer(buf):
        global running
        while running:
            sleep(SLEEPTIME)
            data = record(32)
            with item_available:
                item_available.wait_for(lambda: buf.getlen() <= BUFMAX)
                buf.extbuf(data)
                item_available.notify()

        print("RECORDER ENDS HERE")

    def transmitter_consumer(buf, serversocket):
        global running
        while running:
            sleep(SLEEPTIME)
            with item_available:
                item_available.wait_for(lambda: buf.getlen() >= 32)
                transmit(buf.getx(32), serversocket)
                item_available.notify()

        print("TRANSMITTER ENDS HERE")

    rec_thread = Thread(target=recorder_producer, args=(tbuf,))
    tr_thread = Thread(target=transmitter_consumer, args=(tbuf,serversocket))

    rec_thread.start()
    tr_thread.start()

    rec_thread.join()
    tr_thread.join()
    return


# use a sound library to play the buffer
def play(buf):
    global running
    if running:
        o_sdstream.write(buf)

def receive(socket):
    jsn = b''
    while running:
        while (jsn.find(DELIMITER) == -1) and running:
            try:
                jsn += socket.recv(LEN)
            except timeout:
                try:
                    callibrate()
                except Exception as e:
                    print('Cal ex: {}'.format(e))
                print("NO DATA FROM SERVER (maybe you are the only participant)")
                continue
            except ConnectionResetError:
                print("Recipient disconnected")
                yield None

        try:
            pos = jsn.find(DELIMITER)
            dat = jsn[:pos]
            buf = pickle.loads(dat)

        except pickle.UnpicklingError:
            print(f"    @@@@@ UNPICKLE ERROR @@@@@    INPUT______ of len = {sys.getsizeof(dat)} ::{dat}")
            jsn = jsn[pos + len(DELIMITER):]
            continue
        jsn = jsn[pos + len(DELIMITER):]
        if len(jsn) > NUM * LEN:
            jsn = b''
        yield buf

def receive_play_thread(serversocket):
    print("***** STARTING RECEIVE PLAY THREAD *****")
    rbuf = SharedBuf()

    def receiver_producer(buff, serversocket):
        global running
        rece_generator = receive(serversocket)
        while running:
            sleep(SLEEPTIME)
            try:
                data = next(rece_generator)
            except StopIteration:
                break
            if data is None:
                break
            with audio_available:
                audio_available.wait_for(lambda: buff.getlen() <= BUFMAX)
                buff.extbuf(data)
                audio_available.notify()

        print("RECEIVER ENDS HERE")

    def player_consumer(buff):
        while running:
            sleep(SLEEPTIME)
            with audio_available:
                audio_available.wait_for(lambda: buff.getlen() >= 32)
                play(buff.getx(buff.getlen()))
                audio_available.notify()

        print("PLAYER ENDS HERE")

    global running

    rece_thread = Thread(target=receiver_producer,args=(rbuf, serversocket))
    play_thread = Thread(target=player_consumer, args=(rbuf,))
    rece_thread.start()
    play_thread.start()

    rece_thread.join()
    play_thread.join()
    return


def main(args):
    serversocket = connect(args)
    global running
    t_thread = Thread(target=record_transmit_thread, args=(serversocket,))
    p_thread = Thread(target=receive_play_thread, args=(serversocket,))
    t_thread.start()
    p_thread.start()
    while 42:
        sleep(10)
        callibrate()
    running = False
    i_sdstream.stop()
    o_sdstream.stop()
    t_thread.join()
    p_thread.join()
    serversocket.close()


def connect(args):
    global source_name
    global SERVER_IP
    global SERVER_PORT
    global destination_name
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_IP, SERVER_PORT))

    source_name = args.login
    print(f"hello {source_name}")
    print(f"message length = {len((source_name + (' '*(512-len(source_name)))).encode())}")
    s.send((source_name + (' '*(512-len(source_name)))).encode())
    destination_name = args.room

    s.send((destination_name + (' '*(512-len(destination_name)))).encode())
    sleep(2)
    val = s.recv(2)
    if val.decode() != 'go':
        raise TypeError
    # returns socket fd
    s.settimeout(5.0)
    return s


parser = argparse.ArgumentParser(description='Great Description To Be Here')
parser.add_argument("login", help="login")
parser.add_argument("room", help="room")
args = parser.parse_args()

main(args)
# 2 separate websocket connections for receiving and sending files
# 2 separate threads to handle transmission and playback of the audio files


# start recording and keep sending data


# disconnect server


print("client terminating")
