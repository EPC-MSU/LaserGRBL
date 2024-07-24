import socket
import threading
import random
import re
import os, subprocess, time

import xmlrpc.client

# Destination of commands
XMLRPC_HOST = "127.0.0.1"
XMLRPC_PORT = 40000

# For telnet address in LaserGRBL
HOST = '172.16.129.40'
PORT = 6023

X=0.0
Y=0.0
Z=0.0
F=0

def send_g_command(new_command: str):
    print(repr(new_command), end='\t->\t')
    if new_command == 'M100P1':
        new_command = ['M100', 'P1']
    elif new_command == 'M100P0':
        new_command = ['M100', 'P0']
    elif new_command.startswith('M'):
        m_code = new_command.split(' ')[1:]
        if m_code == '3' or m_code == '4':
            new_command = ['M100', 'P1'] # 'M62 P211'
        elif m_code == '5':
            new_command = ['M100', 'P0']
        else:
            new_command = 'IDK'
    elif "YF" in new_command or "XF" in new_command:
        for L in "XYZIJ":
            new_command = new_command.replace(f"{L}", f"^%^{L}")
        new_command = new_command.split("^%^")
    else:
        for L in "XYZFIJF":
            new_command = new_command.replace(f"{L}", f"^%^{L}")
        new_command = new_command.split("^%^")
    new_command = ' '.join(new_command).replace('  ', ' ').replace('  ', ' ').replace('  ', ' ').replace('  ', ' ')

    with xmlrpc.client.ServerProxy("http://{}:{}/".format(XMLRPC_HOST, XMLRPC_PORT)) as gcode_loader_server:
        try:
            print(repr(new_command), end='')
            result = gcode_loader_server.add_g_command(new_command)
            r = 'ok'
        except xmlrpc.client.Fault as e:
            print(e)
            r = 'error'
    print('\t[res: ', r, ']')
    return r


def send_g_jogging_command(new_command):
    global X
    global Y
    global Z
    if "YF" in new_command or "XF" in new_command:
        for L in "XYZIJ":
            new_command = new_command.replace(f"{L}", f"^%^{L}")
        new_command = new_command.split("^%^")
    else:
        for L in "XYZFIJF":
            new_command = new_command.replace(f"{L}", f"^%^{L}")
        new_command = new_command.split("^%^")

    _g, *axis, _speed = new_command
    speed = int(_speed[1:])

    # print(axis, speed)
    # with xmlrpc.client.ServerProxy("http://{}:{}/".format('172.16.132.223', 51000)) as gcode_loader_server:
    #     try:
    #         for ax_diff in axis:
    #             if 'X' in ax_diff:
    #                 result = gcode_loader_server.jog_axis(1, float(ax_diff[1:]), speed)
    #             if 'Y' in ax_diff:   
    #                 result = gcode_loader_server.jog_axis(2, float(ax_diff[1:]), speed)
    #             if 'Z' in ax_diff:
    #                 result = gcode_loader_server.jog_axis(3, float(ax_diff[1:]), speed)
            
    #         states = gcode_loader_server.get_system_status()['axes']

    #         for i in range(len(states)):
    #             if states[i]['axisName'] == 'X':
    #                 X = states[i]['position']
    #             if states[i]['axisName'] == 'Y':
    #                 Y = states[i]['position']
    #             if states[i]['axisName'] == 'Z':
    #                 Z = states[i]['position']
    #         print(X, Y, Z)
    #     except xmlrpc.client.Fault as e:
    #         result = e
    # print('res', result)
    # if result == 0:
    #     return 'ok'
    # else:
    #     return 'error'

    new_command = ' '.join(new_command)


    with xmlrpc.client.ServerProxy("http://{}:{}/".format(XMLRPC_HOST, XMLRPC_PORT)) as gcode_loader_server:
        try:
            print(repr(new_command), end='')
            result = gcode_loader_server.add_g_command(new_command)
            r = 'ok'
        except xmlrpc.client.Fault as e:
            result = e
            r = 'error'
    print('\t[res: ', r, ']')
    return r



def jogging(data):
    data = data[3:]

    return send_g_jogging_command(data)
    # data = data.replace("X", "^%^X").replace("Y", "^%^Y").replace("Z", "^%^Z").replace("F", "^%^F")
    # commands = data.split("^%^")
    
    # gcode = commands[0]
    # if gcode == 'G90':
    #     X, Y, Z, F = 0.0, 0.0, 0.0, 0
    # for command in commands:
    #     if 'X' in command:
    #         X += float(command[1:])
    #     if 'Y' in command:
    #         Y += float(command[1:])
    #     if 'Z' in command:
    #         Z += float(command[1:])
    #     if 'F' in command:
    #         F += float(command[1:])
    # return "ok"


def get_grbl(data: str) -> str:
    if data == "$I":
        r = "Build info"
    elif data == "$$":
        r = "View gcode parameters"
    elif data.startswith("$J="):
        r = jogging(data)
    else:
        r = ""
    return r


def get_resp(data: str) -> str:
    if data == '?':
        r = f"<Idle|MPos:{X},{Y},{Z}|FS:{F}>"
    elif data.startswith("$"):
        r = get_grbl(data)
    elif data.startswith("G"):
        r = send_g_command(data)
    elif data.startswith("M"):
        r = send_g_command(data)
    elif data.startswith("X"):
        r = send_g_command(data)
    elif data.lower() == "version":
        r = "1.1e"
    elif data == "$":
        r = "help text"
    else:
        r = "error: Unsupported command"
    r += "\n"
    return r

f = open('power_speed_test3.txt', 'w+')
def handle_client(client_socket):
    global f
    client_socket.sendall("Connected\n".encode('utf-8'))

    while True:
        data: str = client_socket.recv(1024).decode("utf-8")# .strip()
        
        if not data:
            break

        
        f.write(data)

        for d in data.split('\n'):
            #print(d, "\t", end='')
            r = get_resp(d)
            #print(r.strip())
            client_socket.sendall(r.encode("utf-8"))

    client_socket.close()

if __name__ == "__main__":
    print('started...')
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)

    while True:
        client_socket, addr = server.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()



# with xmlrpc.client.ServerProxy("http://{}:{}/".format(XMLRPC_HOST, XMLRPC_PORT)) as gcode_loader_server:
#    print("Client connected to server.")

#    """
#    gcode_loader_server.add_g_command("G1 X200 F400")

#    print("Client send command: G1 X200 F400")
#    try:
#        gcode_loader_server.add_g_command("qwer")
#    except xmlrpc.client.Fault as e:
#        print("Error check. Error message:", str(e))
#    """

#    while 1:
#        print("Insert new gcode command: ", end="")
#        new_command = input()

#        try:
#            result = gcode_loader_server.add_g_command(new_command)
#        except xmlrpc.client.Fault as e:
#            result = e
#        print("Result:", result)