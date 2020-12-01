import socket
import threading
import sys
import json
import os 
from datetime import datetime, date, time, timedelta
import sched

server_IP = sys.argv[1]
server_port = int(sys.argv[2])
client_udp_port = int(sys.argv[3])
global global_TempID
global_TempID = None 
global global_TempID_start_time
global_TempID_start_time = None
global global_TempID_end_time
global_TempID_end_time = None
lock = threading.Lock()

class ClientServer(threading.Thread): 
    def __init__(self, server_IP, server_port): 
        threading.Thread.__init__(self)
        self.server_address = (server_IP, server_port)
        self.login_status = 0
        self.current_TempID = None
        self.username = None
        self.password = None
        self.sock = None
    
    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect(self.server_address)
        self.loginHandler()
        self.requestHandler()

    def loginHandler(self): 
        while (self.login_status == 0): 
            username = input(" > Username:")
            password = input(" > Password:")
            MessageType = "Login"
            data = self.messageCreator(MessageType, username, password, 0, None, None)
            self.sock.sendall(data.encode())
            while (self.login_status == 0):
                data = self.sock.recv(4096).decode()
                data = json.loads(data)
                if (data.get('LoginStatus') == 1): 
                    print(" > You are now logged into the server")
                    self.login_status = 1
                    self.username = username
                    self.password = password
                    return 
                elif (data.get('LoginStatus') == 2):
                    print(" > Your account is blocked due to multiple login failures. Please try again later")
                    break
                elif (data.get('LoginStatus') == 3):
                    print(" > Invalid password. Your account has been blocked. Please try again later.")
                    break
                else:
                    print(" > Incorrect username or password has been entered")
                    break
             
    def requestHandler(self): 
        print(" > Welcome to the Bluetrace simulator!")
        while True: 
            command = input(" > Enter a command:")
            print(" > You have entered command: {}".format(command))
            if (command == "Download_tempID"): 
                print(" > Running command: Download_tempID")
                self.downloadTempID()
            elif (command == "Upload_contact_log"): 
                print(" > Running command: Upload_contact_log")
                self.uploadContactLog()
                print(" > Contact log uploaded")
            elif (command == "logout"): 
                self.logoutHandler()
            else :
                command_input = command.split(' ')
                if ((command_input[0]) == "Beacon"):
                    print(" > Attempting to run Beacon command ")
                    dest_IP = (command_input[1]).strip()
                    dest_port = int((command_input[2]).strip())
                    self.sendBeacon(dest_IP, dest_port)
                else:
                    print(" > Error. Invalid command")

    def downloadTempID(self): 
        MessageType = "Download_TempID"
        data = self.messageCreator(MessageType, self.username, self.password, 1, None, None)
        self.sock.sendall((data).encode())
        while True: 
            data = self.sock.recv(4096).decode()
            data = json.loads(data)
            issued_ID = data['TempID']
            issued_ID = issued_ID.split(' ')
            self.current_TempID = (issued_ID[1]).strip()
            global global_TempID_start_time 
            global_TempID_start_time  = (issued_ID[2]) + " " + issued_ID[3]
            global global_TempID_end_time 
            global_TempID_end_time = (issued_ID[4]) + " " + issued_ID[5]
            global global_TempID 
            global_TempID = self.current_TempID
            print(" > TempID{}".format(self.current_TempID))
            return
    
    def messageCreator(self, MessageType, Username, Password, LoginStatus, TempID, ContactLog):
        message = {}
        message['MessageType'] = MessageType
        message['Username'] = Username
        message['Password'] = Password
        message['LoginStatus'] = LoginStatus
        message['TempID'] = TempID
        message['ContactLog'] = ContactLog #Should be passsed as a dictionary
        message = json.dumps(message)
        return message

    def uploadContactLog(self):
        data = {}
        data['MessageType'] = "Upload_Contact_Log"
        if (os.path.exists("z3417347_contactlog.txt")): 
            self.checkContactLog()
            f = open("z3417347_contactlog.txt", "r+")
            log = {}
            print(" > Uploading contact log...")
            for line in f:
                line = line.strip()
                if not line:
                    continue
                else:
                    line = line.split()
                    start_time = line[1] + " " + line[2]
                    end_time = line[3] + " " + line[4]
                    logid = {"StartTime":start_time, "EndTime":end_time }
                    log[line[0]] = logid
                    print(line[0]+ ",")
                    print(start_time + ",")
                    print(end_time + ";")
            data['ContactLog'] = log
            data['Username'] = self.username
            data = json.dumps(data)
            self.sock.sendall((data).encode())
            return
        else:
            log = {}
            data['ContactLog'] = log
            data['Username'] = self.username
            data = json.dumps(data)
            self.sock.sendall((data).encode())
            print("Empty contact log has been uploaded to server")

    def logoutHandler(self): 
        MessageType = 'Logout'
        data = self.messageCreator(MessageType, self.username, self.password, self.login_status, None, None)
        self.sock.sendall((data).encode())
        self.sock.recv(4096)
        self.login_status = 0
        print(" > You have now been logged out of the server")
        sys.exit()

    def sendBeacon(self, dest_IP, dest_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if (global_TempID == None):
            print(" > Cannot send a Beacon as no TempID has been allocated to client")
            return 0 
        else:
            time1 = datetime.strptime(global_TempID_start_time,"%d/%m/%Y %H:%M:%S") - timedelta(minutes= 30)
            time1 = time1.strftime("%d/%m/%Y %H:%M:%S")
            message = "1" + "," + global_TempID + "," + global_TempID_start_time + "," + time1
            sock.sendto(bytes((message).encode()), (dest_IP, dest_port))
            return 0 
    
    def checkContactLog(self): 
        lock.acquire()
        f = open("z3417347_contactlog.txt", "r")
        log_check_time = datetime.now().replace(microsecond = 0)
        log_check_time = datetime.strftime(log_check_time, "%d/%m/%Y %H:%M:%S")
        log_check_time = datetime.strptime(log_check_time, "%d/%m/%Y %H:%M:%S")
        data = f.readlines()
        f.close()
        f = open("z3417347_contactlog.txt", "w+")
        for line in data:
            if line.strip():
                expiry_time = line.split(' ')
                expiry_time = expiry_time[5].strip() + " " + expiry_time[6].strip()
                expiry_time = datetime.strptime(expiry_time, "%d/%m/%Y %H:%M:%S")
                if (expiry_time > log_check_time): 
                    f.write(line)
                else:
                    pass
            else:
                continue
        f.close()
        lock.release()
        return 0

class PeerToPeerListener(threading.Thread): 
    def __init__(self, client_udp_port): 
        threading.Thread.__init__(self)
        self.listen_address = ('', client_udp_port)
        self.sock = None
        self.checklog = []
        self.clean_log_active = 0

    def run(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # Need to confirme exact binding procedure here for socket 
        self.sock.bind(self.listen_address)
        self.receiveBeacon()

    def receiveBeacon(self):
        while True: 
            data, address = self.sock.recvfrom(4096)
            data = str(data.decode())
            data = data.split(",")
            start_time = data[2].strip()
            start_time = datetime.strptime(start_time, "%d/%m/%Y %H:%M:%S")
            start_time1 = start_time.strftime("%d/%m/%Y %H:%M:%S")
            print(str(start_time1) + ",")
            end_time = data[3].strip()
            end_time= datetime.strptime(end_time, "%d/%m/%Y %H:%M:%S")
            end_time1 = end_time.strftime("%d/%m/%Y %H:%M:%S")
            print(str(end_time1) + ",")
            current_time = datetime.now().replace(microsecond= 0)
            current_time1 = current_time.strftime("%d/%m/%Y %H:%M:%S")
            print(str(current_time1) + ";")
            if ((start_time < current_time) and (end_time > current_time)):
                print("Beacon is valid")
                temp_id = data[1]
                self.addBeaconToLog(temp_id, start_time1, end_time1)
                self.checklog.append(current_time)
                t = threading.Timer(180, self.checkLog)
                t.start()
            else:
                print("Beacon is invalid")

    def addBeaconToLog(self, temp_id, start_time, end_time):
        if (os.path.exists("z3417347_contactlog.txt")): 
            f = open("z3417347_contactlog.txt", "a+")
            expiry_time = (datetime.now().replace(microsecond= 0) + timedelta(seconds= 180)).replace(microsecond= 0)
            expiry_time = expiry_time.strftime("%d/%m/%Y %H:%M:%S")
            log_entry = temp_id + " " + str(start_time) + " " + str(end_time) + " " + expiry_time
            f.write("\n")
            f.write(log_entry)
            f.close()
            return
        else: 
            f = open("z3417347_contactlog.txt", "w+")
            expiry_time = (datetime.now().replace(microsecond= 0) + timedelta(seconds= 180)).replace(microsecond= 0) 
            expiry_time = expiry_time.strftime("%d/%m/%Y %H:%M:%S")
            log_entry = temp_id + " " + str(start_time) + " " + str(end_time) + " " + expiry_time
            f.write("\n")
            f.write(log_entry)
            f.close()
            return
    
    def checkLog(self):
        print("Check Log......")
        current_time = datetime.now().replace(microsecond= 0)
        print("Current Time: {}".format(current_time))
        print("Check Log: {}".format(self.checklog))
        lock.acquire()
        f = open("z3417347_contactlog.txt", "r+")
        data = f.readlines()
        f.close()
        f = open("z3417347_contactlog.txt", "w+")
        for line in data:
            if line.strip():
                line1 = line.split(" ")
                expire_time = line1[5].strip() + " " + line1[6].strip()
                expire_time = datetime.strptime(expire_time, "%d/%m/%Y %H:%M:%S")
                if (expire_time > current_time):
                    f.write("\n")
                    f.write(line)
                    print("Added Line: {}".format(line))
                else:
                    print("Removing Line: {}".format(line))
                    pass
        f.close()
        lock.release()
        return 0

def main():
    Server_Thread =  ClientServer(server_IP, server_port)
    Server_Thread.start()
    PeerToPeer_Thread = PeerToPeerListener(client_udp_port)
    PeerToPeer_Thread.start()

if __name__ == "__main__": 
    main()