import socket
import threading
import tkinter as tk

from gui import ChatGUI

class ChatClientApp:
    def __init__(self, root):
        self.root = root
        self.gui = ChatGUI(root)
        self.sock = None
        self.connected = False
        self.username = None

        # bind GUI callbacks
        self.gui.set_on_connect(self.connect)
        self.gui.set_on_send(self.send_message)
        self.gui.set_on_close(self.on_closing)

    def connect(self, server, port, name):
        if self.connected:
            self.disconnect()
            return

        self.username = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.gui.add_message(f"Connecting to {server}:{port}...", "system")
            self.sock.connect((server, port))

            # send username followed by newline
            self.sock.sendall((name + '\n').encode('utf-8'))

            self.connected = True
            self.gui.add_message(f"Connected as {name}", "system")
            self.gui.update_status(True)

            # start receiver thread
            t = threading.Thread(target=self._receive_loop, daemon=True)
            t.start()

        except Exception as e:
            self.gui.add_message(f"Connection failed: {e}", "error")
            if self.sock:
                try:
                    self.sock.close()
                except Exception:
                    pass
                self.sock = None

    def disconnect(self):
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

        self.gui.add_message("Disconnected from server", "system")
        self.gui.update_status(False)

    def _receive_loop(self):
        buffer = b''
        try:
            while self.connected:
                data = self.sock.recv(4096)
                if not data:
                    # server closed
                    self.gui.root.after(0, lambda: self.gui.add_message("Server closed connection", "error"))
                    self.root.after(0, self.disconnect)
                    break

                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    try:
                        message = line.decode('utf-8', errors='ignore')
                        # post to GUI thread
                        self.gui.add_message(message, "received")
                    except Exception as e:
                        self.gui.add_message(f"Decode error: {e}", "error")

        except Exception as e:
            if self.connected:
                self.gui.add_message(f"Receive error: {e}", "error")
                self.root.after(0, self.disconnect)

    def send_message(self, message):
        if not self.connected or not self.sock:
            self.gui.add_message("Not connected.", "error")
            return

        try:
            self.sock.sendall((message + '\n').encode('utf-8'))
            self.gui.add_message(f"You: {message}", "sent")
        except Exception as e:
            self.gui.add_message(f"Send failed: {e}", "error")
            self.disconnect()

    def on_closing(self):
        # called when the GUI is closed
        if self.connected:
            try:
                self.sock.close()
            except Exception:
                pass
            self.connected = False
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ChatClientApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()

