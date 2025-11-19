
import socket
import threading
import argparse

clients_lock = threading.Lock()
clients = {}  # socket -> username

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
FILE_MARKER = b'__FILE__\n'

def broadcast(message_bytes, except_sock=None):
    #Send message_bytes to all connected clients except except_sock.
    with clients_lock:
        dead = []
        for sock in list(clients.keys()):
            if sock is except_sock:
                continue
            try:
                sock.sendall(message_bytes)
            except Exception:
                dead.append(sock)
        for s in dead:
            try:
                s.close()
            except:
                pass
            if s in clients:
                del clients[s]

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

            while True:
                # FIRST: look for marker anywhere in buffer
                marker_idx = buffer.find(FILE_MARKER)
                if marker_idx != -1:
                    # process any text before the marker as normal chat
                    if marker_idx > 0:
                        before = buffer[:marker_idx]
                        # process complete lines in 'before'
                        while b'\n' in before:
                            line, before = before.split(b'\n', 1)
                            if not line:
                                continue
                            try:
                                text = line.decode(errors='ignore')
                            except:
                                text = "<decode error>"
                            out = f'{username}: {text}\n'.encode()
                            broadcast(out, except_sock=None)
                        # leftover partial bytes before marker stay before marker
                        buffer = before + buffer[marker_idx:]
                    # Now buffer starts with marker; handle file header & bytes
                    if buffer.startswith(FILE_MARKER):
                        # ensure header complete (header ends with b'\n\n')
                        while b'\n\n' not in buffer:
                            chunk = conn.recv(4096)
                            if not chunk:
                                raise ConnectionError("Client disconnected during file header")
                            buffer += chunk
                        header, buffer = buffer.split(b'\n\n', 1)
                        parts = header.split(b'\n')
                        if len(parts) < 3:
                            print("[!] Malformed file header from", username)
                            continue
                        _, filename_b, filesize_b = parts[:3]
                        try:
                            filesize = int(filesize_b.decode())
                        except Exception:
                            print("[!] Invalid filesize from", username)
                            continue
                        if filesize < 0 or filesize > MAX_FILE_SIZE:
                            print(f"[!] File size {filesize} invalid/too large from {username}")
                            # drain bytes if present
                            to_drain = filesize
                            while to_drain > 0:
                                chunk = conn.recv(min(4096, to_drain))
                                if not chunk:
                                    break
                                to_drain -= len(chunk)
                            try:
                                conn.sendall(b"ERROR: File too large or invalid\n")
                            except:
                                pass
                            continue

                        header_bytes = header + b'\n\n'
                        have = len(buffer)
                        if have >= filesize:
                            file_bytes = buffer[:filesize]
                            rest = buffer[filesize:]
                            try:
                                broadcast(header_bytes + file_bytes, except_sock=conn)
                            except Exception:
                                pass
                            buffer = rest
                        else:
                            if have > 0:
                                try:
                                    broadcast(header_bytes + buffer, except_sock=conn)
                                except Exception:
                                    pass
                                remaining = filesize - have
                            else:
                                try:
                                    broadcast(header_bytes, except_sock=conn)
                                except Exception:
                                    pass
                                remaining = filesize
                            while remaining > 0:
                                chunk = conn.recv(min(4096, remaining))
                                if not chunk:
                                    raise ConnectionError("Client disconnected during file upload")
                                try:
                                    broadcast(chunk, except_sock=conn)
                                except Exception:
                                    pass
                                remaining -= len(chunk)
                        # file handled — continue outer loop
                        continue

                # No marker found (or handled) — handle text lines normally
                if b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    # legacy: if client sent FILE: JSON (older approach), forward unchanged
                    if line.startswith(b'FILE:'):
                        try:
                            broadcast(line + b'\n', except_sock=None)
                        except Exception:
                            pass
                    else:
                        text = line.decode(errors='ignore')
                        out = f'{username}: {text}\n'.encode()
                        broadcast(out, except_sock=None)
                else:
                    # read more data
                    chunk = conn.recv(1024)
                    if not chunk:
                        break
                    buffer += chunk

        except Exception as e:
            print(f"[!] Exception in client {addr}: {e}")
        finally:
            with clients_lock:
                name = clients.pop(conn, None)
            if name:
                leave_msg = f'*** {name} has left the chat ***\n'.encode()
                broadcast(leave_msg)
            print(f"[-] Connection closed: {addr}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=5000)
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
