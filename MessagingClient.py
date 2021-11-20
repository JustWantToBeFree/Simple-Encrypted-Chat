try:
    import socket
    import pickle
    import argparse
    import threading
    import random
    import time
    import sys
    from nacl.public import PrivateKey, Box
    import tkinter as tk
    from tkinter.scrolledtext import ScrolledText
except:
    print("You need to install some libaries to run this. could be one or both")
    print("sudo python3 -m pip install PyNaCl")
    print("sudo apt-get install python3-tk")
    sys.exit()

class GUI(tk.Tk, threading.Thread):
    def __init__(self, client):
        self.client = client
        super().__init__()
        threading.Thread.__init__(self)
        self.windowProperties()
        self.createTextbox()
        self.createUserInputBox()
        self.bind("<Return>", self.key_pressed)

    def key_pressed(self, event):
        txt = self.userinp.get("1.0", tk.END)
        self.client.sendEncryptedMsg(bytes(txt, 'utf-8'))
        self.userinp.delete("1.0","end")

    def windowProperties(self):
        self.geometry("1000x800")
        self.resizable(False, False)
        self.title("Secure Chat")

    def createTextbox(self):
        self.textbox = ScrolledText(self, height=40, bg='black')
        self.textbox['state'] = tk.DISABLED
        self.textbox.tag_configure('green', foreground='green')
        self.textbox.tag_configure('error', foreground='red')
        self.textbox.tag_configure('self', foreground='white')
        self.textbox.tag_configure('generalmsg', foreground='purple')
        self.textbox.tag_configure('otherusr', foreground='orange')
        self.textbox.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def createUserInputBox(self):
        self.userinp = tk.Text(self, height=2)
        self.userinp.pack(side=tk.BOTTOM, expand=tk.NO, fill=tk.BOTH)

    def renderText(self, text:str, tag:str):
        self.textbox['state'] = tk.NORMAL
        self.textbox.insert(tk.END, text, tag)
        self.textbox.see(tk.END)
        self.textbox['state'] = tk.DISABLED

    def renderError(self, errormsg:str):
        self.renderText(errormsg, 'error')

class Main:
    BUFFER_SIZE = 15360

    def __init__(self, ip:str, port:int, username:str):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = username
        self.port = port
        self.ip = ip
        self.creds = {}
        self.box = None
        self.private_key = PrivateKey.generate()
        self.public_key = self.private_key.public_key
        self.connectToServer()

        self.gui = GUI(self)

        self.tr1 = threading.Thread(target=self.listenForData)
        self.tr1.start()

        self.gui.start()

        self.gui.mainloop()

    def listenForData(self):
        while True:
            org_data = self.sock.recv(self.BUFFER_SIZE)
            data = dict(pickle.loads(org_data))

            if data['command'] == 'encryptedmsgfromserver':
                if self.box == None:
                    if not self.createBoxWithOtherClient():
                        self.gui.renderError("Recieved a message but no box is created therefore unable to decrypt. Consult billyb0b about this!\n\n")
                        continue
                try:
                    encrypted_msg = data['data']
                    msg = self.box.decrypt(encrypted_msg).decode()[:-2]
                    msg = f"{data['username']} < {msg}\n"
                    tag = 'otherusr'
                    if self.username == data['username']: tag = 'self'
                    self.gui.renderText(msg, tag)
                except Exception as e:
                    self.gui.renderError("There was an error decrypting the message")



            elif data['command'] == 'returnCreds':
                self.creds = pickle.loads(data['data'])
                self.createBoxWithOtherClient()

            elif data['command'] == 'generalMsgg':
                self.gui.renderText(f"\n{data['msg']}\n", 'generalmsg')

    def connectToServer(self):
        try:
            self.sock.connect((self.ip, self.port))
            self.sendData({
                'username': self.username,
                'public_key': self.public_key
            })
        except socket.error as e:
            self.gui.renderError("Failed to connect to the server!")
            self.gui.renderError(e)

    def createBoxWithOtherClient(self):
        for cred in self.creds:
            if cred == self.username:
                continue
            self.box = Box(self.private_key, self.creds[cred])
            return True
        return False

    def sendData(self, data:dict):
        try:
            pckld_data = pickle.dumps(data)
            self.sock.send(pckld_data)
        except socket.error as e:
            self.gui.renderError("There was an error sending data!")
            self.gui.renderError(e)

    def requestCreds(self):
        self.sendData({
            'command':'reqCred'
        })
        if self.box == None:
            self.createBoxWithOtherClient()

    def sendEncryptedMsg(self, msg:bytes):
        if self.box == None:
            self.requestCreds()
            if not self.createBoxWithOtherClient():
                self.gui.renderError("There is current no-one else online!")
                return

        encrypted_msg = self.box.encrypt(msg)
        self.sendData({
            'command': 'encryptedmsgfromclient',
            'data': encrypted_msg
        })

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', required=True)
    parser.add_argument('-port', required=True)
    parser.add_argument('-m', required=True)
    args = parser.parse_args()

    if int(args.m) == 0:
        username = str(input("Enter a username: "))
    else:
        username = f"user_{random.randint(100, 999)}"

    Main(args.ip, int(args.port), username)
