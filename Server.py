import socket 
import threading
import datetime as dt 
import re
import sys 
import json
import datetime
import os
import random 

server_port = int(sys.argv[1])
block_duration = int(sys.argv[2])
lock = threading.Lock()

#loads the client credentials file to a dictionary on the server
def loadCredentials():
    global server_credentials
    server_credentials = {}
    with open("credentials.txt") as f: 
        for line in f: 
            username, password = line.split(' ')
            password.strip('\r\n')
            if username not in server_credentials: 
                server_credentials[username] = password 
    f.close()

#Creates a block list to maintain users blocked from login 
def blockList(): 
    global block_list
    block_list = {}
 
#Creates a new thread for each TCP client connection 
class NewThread(threading.Thread): 
    def __init__(self,sock_connection, client_address): 
        threading.Thread.__init__(self)
        self.sock_connection = sock_connection
        self.client_address = client_address
        self.login_status = 0
        self.login_counter = 0
        self.username = None

    #Initiates the recvHandler function for the thread 
    def run(self): 
        self.recvHandler(self.sock_connection, self.client_address, self.login_status)       

    #Passes the client to the loginHandler and logs them in 
    def recvHandler(self, sock_connection, client_address, login_status):

        #Continuously reads data from the client and passes this to the login handler while the client is 1. Not Logged in or 2. Blocked 
        while ((self.login_status == 0) or (self.login_status == 2)):
            data = sock_connection.recv(4096).decode()
            parse_data = json.loads(data)
            if parse_data['MessageType'] == 'Login': 
                self.loginHandler(parse_data)


        #Parses commands from the client where the client is logged in
        #Passes the command recieved to the relevant function 1. generateTempID 2. checkContactLog 3. Logout 4 . Print invalid command 
        if (self.login_status == 1): 
            MessageType = "Login"
            data = self.messageCreator(MessageType, None, None, 1, None, None)
            sock_connection.sendall((data).encode())
            while (self.login_status == 1):
                data = sock_connection.recv(4096).decode()
                parse_data = json.loads(data)
                if (parse_data['MessageType'] == "Download_TempID"):
                    TempID = self.generateTempID()
                    print("user: {}".format(self.username))
                    x = TempID.split(' ')
                    print("TempID: {}".format(x[1]))
                    MessageType = "Download_tempID"
                    data = self.messageCreator(MessageType, None, None, self.login_status, TempID, None)
                    sock_connection.sendall(data.encode())
                elif (parse_data['MessageType'] == "Upload_Contact_Log"): 
                    self.checkContactLog(parse_data)
                elif (parse_data['MessageType'] == 'Logout'):
                    self.logoutHandler(parse_data)
                else: 
                    print("Invalid command")
            return 0

    #Handles log in of the client 1. Checks if the client is current blocked 2. Logs client in 3. Records incorrect login attempt by client 
    def loginHandler(self, parse_data):
        user_password = str(server_credentials.get((parse_data.get('Username')))).strip()
        attempt_password = str(parse_data.get('Password')).strip()
        if self.checkBlockList(parse_data) == 2: 
            MessageType = "Login" 
            data = self.messageCreator(MessageType, None, None, 2, None, None)
            self.sock_connection.sendall((data).encode())
            return 0
        if attempt_password == user_password:
            self.login_status = 1
            self.login_counter = 0
            self.username = parse_data['Username']
            return 0
        else:
            self.login_status = 0
            self.login_counter = self.login_counter + 1
            if self.login_counter == 3:
                username = parse_data.get('Username')
                current_time = datetime.datetime.now()
                time_blocked = current_time + datetime.timedelta(0, block_duration)
                self.addToBlockList(username, time_blocked)
                self.login_status = 0
                MessageType = "Login" 
                data = self.messageCreator(MessageType, None, None, 3, None, None)
                self.sock_connection.sendall((data).encode())
                return 0
            elif self.login_counter > 3: 
                username = parse_data.get('Username')
                current_time = datetime.datetime.now()
                time_blocked = current_time + datetime.timedelta(0, block_duration)
                self.addToBlockList(username, time_blocked)
                self.login_status = 0
            print("Login Status {}".format(self.login_status))
            MessageType = "Login" 
            data = self.messageCreator(MessageType, None, None, 0, None, None)
            self.sock_connection.sendall((data).encode())
            return 0 

    #Checks to see if the client is on the blocked list. Removes the client from the block list if the block has expired 
    def checkBlockList(self, parse_data):
        blockedTime = block_list.get(parse_data.get('Username'))
        if blockedTime == None: 
            return 0
        if blockedTime <= datetime.datetime.now():
            lock.acquire()
            del block_list[parse_data.get('Username')]
            lock.release()
            return 0
        else: 
            self.login_counter = 0
            return 2

    #Adds a client to the block list when they have made 3 or more incorrect attempts 
    def addToBlockList(self, username, time_blocked):
        lock.acquire()
        block_list[username] = time_blocked
        lock.release()
        return 0

    #Takes Message inputs and returns a JSON format messgae to be transmitted
    def messageCreator(self, MessageType, Username, Password, LoginStatus, TempID, ContactLog):
        message = {}
        message['MessageType'] = MessageType
        message['Username'] = Username
        message['Password'] = Password
        message['LoginStatus'] = LoginStatus
        message['TempID'] = TempID
        message['ContactLog'] = ContactLog #Takes the contact log which should be added as a dictionary
        message = json.dumps(message)
        return message

    #Generates the TempID for the client and adds this to "TempIDs.txt". If TempIDs.txt does not exist this will create a new file for it
    def generateTempID(self):
        if (os.path.exists("tempIDs.txt")): 
            f = open("tempIDs.txt", "a+")
            while True:
                generatedID = random.randint(10000000000000000000, 99999999999999999999)
                if (self.checkUniqueID(f, generatedID) == False):
                    break
            current_time = datetime.datetime.now().replace(microsecond= 0)
            id_expiry_time = (current_time + datetime.timedelta(minutes = 15)).replace(microsecond= 0)
            id_expiry_time = id_expiry_time.strftime("%d/%m/%Y %H:%M:%S")
            current_time = current_time.strftime("%d/%m/%Y %H:%M:%S")
            new_line = self.username + " " + str(generatedID) + " " + str(current_time) + " " + str(id_expiry_time) + "\n"
            f.write(new_line)
            f.close()
            return new_line
        else: 
            f = open("tempIDs.txt", "w+")
            generatedID = random.randint(10000000000000000000, 99999999999999999999)
            current_time = datetime.datetime.now().replace(microsecond= 0)
            id_expiry_time = (current_time + datetime.timedelta(minutes = 15)).replace(microsecond= 0)
            id_expiry_time = id_expiry_time.strftime("%d/%m/%Y %H:%M:%S")
            current_time = current_time.strftime("%d/%m/%Y %H:%M:%S")
            new_line = self.username + " " + str(generatedID) + " " + str(current_time) + " " + str(id_expiry_time) + "\n"
            f.write(new_line)
            f.close()
            return new_line

    #Checks that the TempID generated is unique within the file 
    def checkUniqueID(self, f, generatedID):
        for line in f:
            line = line.split()
            if line[1] == generatedID: 
                return True
        return False
    
    #Checks the contact log against TempID's issued. Prints the username of any client with a TempID that matches any ID in the contact log 
    def checkContactLog(self, data):
        print(" > Recieved contact log from {}".format(data['Username']))
        contact_log = data['ContactLog']
        for i in contact_log: 
            print(i + ",")
            print(contact_log[i]["StartTime"] + ",")
            print(contact_log[i]["EndTime"] + ";")
        print(" > Contact log checking")
        count = 0
        for i in contact_log:
            f = open("tempIDs.txt", "r+")
            for line in f:
                if line.strip():
                    line = line.split(' ')
                    if (line[1].strip() == i):
                        count = count + 1
                        print(line[0] + ",")
                        print(line[2] + " " + line[3] + ",")
                        print(line[1] + ";")
        if (count == 0):
            print(" > There are no matches in the contact log")
        print(" > All logs printed")
        return

    #Handles logout of the client. Closes the connection with the client upon receipet of the logout command
    def logoutHandler(self, data): 
        self.sock_connection.close()
        self.login_status = 0
        print(" > {} logout".format(data['Username']))
        return 0

#Main sequence 1. Loads valid credentials 2. Initialstes the block list 3. Connects listening socket and continuously listens for new connections
def main(): 
    loadCredentials()
    blockList()
    global block_list 
    block_list = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server = (socket.gethostname(), server_port)
    sock.bind(server)
    print("Starting server on {} on port {}".format(socket.gethostname(),server_port))
    while True:
        sock.listen(20)
        sock_connection, client_address = sock.accept()
        thread = NewThread(sock_connection, client_address)
        thread.start()
    
if __name__ == "__main__": 
    main()
