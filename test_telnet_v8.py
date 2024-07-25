import socket
import threading
import random
import re
import os, subprocess, time

import xmlrpc.client

# Unotor GCode Loader
XMLRPC_HOST = "127.0.0.1"
XMLRPC_PORT = 40000

# Real axes status (NOT WORK)
AXES_HOST = '172.16.132.223'
AXES_PORT = 50502

# Telnet address for LaserGRBL
HOST = '172.16.129.40'
PORT = 6024

X=0.0
Y=0.0
Z=0.0
F=0

last_G = None


def normalize(line: str) -> str:
    # add spaces before letters
    new_line = ''
    for char in line:
        if char.isalpha():
            new_line += ' ' + char 
        else:
            new_line += char

    # fix 2-digits-g-code separation by step above
    for k, v in {'X F': 'XF', 'Y F': 'YF', 'Z F': 'ZF', 'U F': 'UF', 'W F': 'WF', 'V F': 'VF'}.items():
        new_line = new_line.replace(k, v) 
    
    # many spaces -> one space
    new_line = ' '.join(new_line.split()) 
    new_line = new_line.strip()

    # Normalize G01 to G1 etc
    tokens = new_line.split()
    if tokens[0].startswith('G'):
        tokens[0] = 'G' + str(int(tokens[0][1:]))
    new_line = ' '.join(tokens)

    return new_line

def first_token(cmd):
    return normalize(cmd).split()[0]

def send_g_command(cmd: str):
    global last_G
    old_cmd = repr(cmd)
    cmd = normalize(cmd)

    # Replace for jogging
    if cmd.startswith('G91'):
        cmd = cmd.replace('G91', 'G0', 1)

    # Remember last seen G-command
    if cmd.startswith('G'):
        last_G = first_token(cmd)
    
    # If command send without M or G or S, this is previous frame still running. We need to add last seen G-command
    if cmd[0] not in 'MGS':
        if last_G is not None:
            cmd = last_G + ' ' + cmd

    # Replaces for unknown M
    if first_token(cmd) in ['M3', 'M4']:
        cmd = 'M100 P1'
    if first_token(cmd) == 'M5':
        cmd = 'M100 P0'
    # Replaces for unknown S
    if cmd.startswith('S'):
        cmd = 'M102'
    
    xmlrtsp_resp = ''
    with xmlrpc.client.ServerProxy(f"http://{XMLRPC_HOST}:{XMLRPC_PORT}/") as gcode_loader_server:
        try:
            xmlrtsp_resp = str(gcode_loader_server.add_g_command(cmd))
            r = 'ok'
        except xmlrpc.client.Fault as e:
            xmlrtsp_resp = str(e)
            r = 'error'
    print('->  ', old_cmd, ' '*(40-len(old_cmd)) + '->' + '  ', repr(cmd), ' '*(40-len(cmd)), '[xmlrpc_resp: ', xmlrtsp_resp, ']', end='')
    return r


def get_grbl(data: str) -> str:
    if data == "$I":
        r = "Build info"
    elif data == "$$":
        r = "$X" # Unlock GRBL?
    elif data == "$$":
        r = "View gcode parameters"
    elif data.startswith("$J="):
        r = send_g_command(data[3:])
    else:
        r = ""
    return r


def get_resp(data: str) -> str:
    if data == '?' or data.replace('?', '') == '\x18' or ' '.join(set(data)) == '?':
        return f"<Idle|MPos:{X},{Y},{Z}|FS:{F}>\n"
    
    data = data.replace('?', '')
    data = data.strip()
    if not len(data):
        return ''


    if data.startswith("$"):
        r = get_grbl(data)
    elif data.lower() == "version":
        r = "1.1e"
    elif data == "$":
        r = "help text"
    elif data[0] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
        r = send_g_command(data)
    else:
        r = 'error'
    return r + "\n"


def handle_client(client_socket):
    global f
    client_socket.sendall("Connected\n".encode('utf-8'))

    while True:
        data: str = client_socket.recv(1024).decode("utf-8")# .strip()
        if not data:
            break

        for d in data.split('\n'):
            if not len(d):
                continue
            print(repr(d), ' '*(40-len(d)), end='')

            r = get_resp(d)
            # time.sleep(0.05)

            print(f'[back to LaserGRBL: {repr(r)}]')
            client_socket.sendall(r.encode("utf-8"))

    client_socket.close()


if __name__ == "__main__":
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)

    print(f'Started telnet server at {HOST}:{PORT}')

    while True:
        client_socket, addr = server.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))
        client_handler.start()
