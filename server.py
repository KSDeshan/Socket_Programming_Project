import socket
import threading
import argparse

clients_lock = threading.Lock()
clients = {}  # socket -> username

def broadcast(message_bytes, except_sock=None):
    #Send message_bytes to all connected clients except except_sock
    with clients_lock:
        for sock in list(clients.keys()):
            if sock is except_sock:
                continue
            try:
                sock.sendall(message_bytes)
            except Exception:
                # client likely disconnected — cleanup
                try:
                    sock.close()
                except:
                    pass
                del clients[sock]

def handle_client(conn, addr):
    #Handle an individual client connection
    with conn:
        try:
            conn.sendall(b'WELCOME: Please send your username followed by newline.\n')
            buffer = b''
            # read username (until newline)
            while b'\n' not in buffer:
                chunk = conn.recv(1024)
                if not chunk:
                    return
                buffer += chunk
            username = buffer.split(b'\n',1)[0].decode(errors='ignore').strip()
            with clients_lock:
                clients[conn] = username
            welcome_msg = f'*** {username} has joined the chat ***\n'.encode()
            print(f"[+] {addr} as {username}")
            broadcast(welcome_msg, except_sock=conn)
            # remaining data after username
            buffer = buffer.split(b'\n',1)[1] if b'\n' in buffer else b''

            # main loop: collect lines and broadcast
            while True:
                if b'\n' in buffer:
                    line, buffer = buffer.split(b'\n',1)
                    text = line.decode(errors='ignore')
                    out = f'{username}: {text}\n'.encode()
                    broadcast(out, except_sock=None)
                else:
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    buffer += chunk
        except Exception as e:
            print(f"[!] Exception in client {addr}: {e}")
        finally:
            # cleanup
            with clients_lock:
                name = clients.pop(conn, None)
            if name:
                leave_msg = f'*** {name} has left the chat ***\n'.encode()
                broadcast(leave_msg)
            print(f"[-] Connection closed: {addr}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=9090)
    args = parser.parse_args()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.host, args.port))
    server.listen(50)
    print(f"Chat server listening on {args.host}:{args.port}")

    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\nShutting down server.")
    finally:
        server.close()

if __name__ == '__main__':
    main()
