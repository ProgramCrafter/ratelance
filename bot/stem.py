import logging
import socket
import time


STEM_ADDR = ('stem.fomalhaut.me', 5733)


def byte(n):
    return bytes([n])


class RetriableSocket:
    def __init__(self, addr, reconnect_callback=None):
        self.reconnect_callback = reconnect_callback
        self.sock = socket.socket()
        self.sock.connect(addr)
        self.sock.settimeout(0.1)
        self.addr = addr
    
    def close(self):
        self.sock.close()
    
    def reconnect(self):
        while True:
            try:
                self.close()
                logging.info('[STEM]    Reconnecting...')
                time.sleep(0.5)
                self.sock = socket.socket()
                self.sock.connect(self.addr)
                self.sock.settimeout(0.1)
                
                if self.reconnect_callback: self.reconnect_callback()
                return
            except (ConnectionResetError, TimeoutError, socket.timeout):
                pass
    
    def send(self, s):
        if isinstance(s, int): s = byte(s)
        if isinstance(s, str): s = s.encode('utf-8')
        
        while True:
            try:
                self.sock.sendall(s)
                return
            except (ConnectionResetError, TimeoutError, socket.timeout):
                self.reconnect()
    
    def recv(self, n):
        try:
            data = b''
            while len(data) < n: data += self.sock.recv(n - len(data))
            return data
        except (ConnectionResetError, TimeoutError, socket.timeout):
            self.reconnect()
            return None


class StemClient:
    def __init__(self):
        self.subscribed = set()
        self.sock = RetriableSocket(STEM_ADDR, self.resubscribe)
    
    def resubscribe(self):
        for channel in self.subscribed:
            self.send_package(1, channel)
    
    def disconnect(self):
        if self.sock:
            self.sock.close()
            self.sock = None
    
    def send_package(self, _type, _id, _message=None):
        pack = byte(_type)
        if _type == 3 or _type == 4:
            pack += _id
        else:
            pack += byte(len(_id.encode('utf-8')))
            pack += _id.encode('utf-8')
            if _message: pack += _message.encode('utf-8')
        
        self.sock.send(len(pack) // 256)
        self.sock.send(len(pack) % 256)
        self.sock.send(pack)
    
    def subscribe(self, channel):
        self.subscribed.add(channel)
        self.send_package(1, channel)
    
    def unsubscribe(self, channel):
        self.subscribed.discard(channel)
        self.send_package(2, channel)
    
    def send(self, channel, msg):
        self.send_package(0, channel, msg)
    
    def recv(self):
        pack_len = self.sock.recv(2)
        pack_type = self.sock.recv(1)
        if not pack_len: return None
        if not pack_type: return None
        
        if pack_type == b'\0': # incoming msg
            ch_len = self.sock.recv(1)[0] # getting int from byte string
            if not ch_len: return None
            ch_id = self.sock.recv(ch_len)
            if not ch_id: return None
            
            msg_len = pack_len[0] * 256 + pack_len[1]
            msg_len -= ch_len + 2
            msg = self.sock.recv(msg_len)
            if not msg: return None
            
            return msg
            # return str(msg, 'utf-8')
        elif pack_type == b'\3': # pinging
            msg_len = pack_len[0] * 256 + pack_len[1] - 1
            pong_data = self.sock.recv(msg_len)
            if not pong_data: return None
            self.send_package(4, pong_data)
            
            return None
