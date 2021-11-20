import socket
import argparse
import threading
import pickle
import time

class Client(threading.Thread):
    BUFFER_SIZE = 15360

    def __init__(self, server, s):
        print("New client request established...")
        threading.Thread.__init__(self)
        self.server = server
        self.s = s

    def run(self):
        pckld_creds = self.s.recv(self.BUFFER_SIZE)
        cred_data = pickle.loads(pckld_creds)
        self.username = cred_data['username']
        self.public_key = cred_data['public_key']
        self.server.addCreds(self.username, self.public_key)
        self.server.relayCreds()
        self.server.relayData({
            'command': 'generalMsgg',
            'msg': f"{self.username} has connected..."
            })
        self.listenForData()

    def listenForData(self):
        while True:
            try:
                org_data = self.s.recv(self.BUFFER_SIZE)
                data = pickle.loads(org_data)
                del org_data

                if data['command'] == 'encryptedmsgfromclient':
                    self.server.relayData({
                        'command': 'encryptedmsgfromserver',
                        'data': data['data'],
                        'username': self.username
                        })
                    continue

                if data['command'] == 'reqCred':
                    self.server.relayCreds()
                    continue
            except:
                print(f"Connection to '{self.username}' was lost!")
                self.Destruct()
                break

    def Destruct(self):
        self.server.rmvCreds(str(self.username))
        for client in self.server.clients_connected:
            if client == self:
                self.server.clients_connected.remove(self)


    def sendData(self, data:dict):
        try:
            pckld_data = pickle.dumps(data)
            self.s.send(pckld_data)
        except Exception as e:
            print("There was an error sending data!")
            print(e)

class Server(threading.Thread):
    def __init__(self, ip:str, port:int):
        threading.Thread.__init__(self)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.clients_connected = []
        self.creds = {}
        self.ip = ip
        self.port = port

    def run(self):
        while True:
            try:
                self.s.bind((self.ip, self.port))
                print("The server is now starting...!\n")
                break
            except Exception as e:
                print("The socket is already binded... retrying")
                time.sleep(2)

        self.s.listen(2)
        print("The server is now open and listening for clients!")
        self.listenForConnections()

    def listenForConnections(self):
        while True:
            client, addr = self.s.accept()
            c = Client(self, client)
            c.start()
            self.clients_connected.append(c)

    def addCreds(self, username, public_key):
        self.creds[username] = public_key

    def rmvCreds(self, username:str):
        self.creds.pop(username)
        self.relayCreds()

    def relayData(self, data:dict):
        for client in self.clients_connected:
            try:
                client.sendData(data)
            except socket.error:
                self.client.Destruct()

    def relayCreds(self):
        self.relayData({
            'command': 'returnCreds',
            'data': pickle.dumps(self.creds)
        })

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', required=True)
    args = parser.parse_args()
    s = Server(args.ip, 4444).start()
