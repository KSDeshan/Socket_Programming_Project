#!/usr/bin/env python3
"""
GUI Chat Client with file send/receive (binary streaming).
Usage:
    python3 gui_client.py
"""
import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
from datetime import datetime
import os

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
HEADER_MARKER = b'__FILE__\n'

class ChatClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat Client")
        self.root.geometry("700x600")
        self.root.minsize(500, 400)

        self.sock = None
        self.connected = False
        self.username = ""

        self.setup_ui()

    def setup_ui(self):
        conn_frame = tk.Frame(self.root, bg="#2c3e50", padx=10, pady=10)
        conn_frame.pack(fill=tk.X)

        tk.Label(conn_frame, text="Server:", bg="#2c3e50", fg="white", font=("Arial", 10)).grid(row=0, column=0, padx=5, sticky='w')
        self.server_entry = tk.Entry(conn_frame, width=20, font=("Arial", 10))
        self.server_entry.insert(0, "localhost")
        self.server_entry.grid(row=0, column=1, padx=5)

        tk.Label(conn_frame, text="Port:", bg="#2c3e50", fg="white", font=("Arial", 10)).grid(row=0, column=2, padx=5, sticky='w')
        self.port_entry = tk.Entry(conn_frame, width=8, font=("Arial", 10))
        self.port_entry.insert(0, "5000")
        self.port_entry.grid(row=0, column=3, padx=5)

        tk.Label(conn_frame, text="Name:", bg="#2c3e50", fg="white", font=("Arial", 10)).grid(row=0, column=4, padx=5, sticky='w')
        self.name_entry = tk.Entry(conn_frame, width=15, font=("Arial", 10))
        self.name_entry.grid(row=0, column=5, padx=5)

        self.connect_btn = tk.Button(conn_frame, text="Connect", command=self.connect,
                                     bg="#27ae60", fg="white", font=("Arial", 10, "bold"),
                                     padx=15, cursor="hand2")
        self.connect_btn.grid(row=0, column=6, padx=5)

        self.status_label = tk.Label(conn_frame, text="Disconnected",
                                     bg="#2c3e50", fg="#e74c3c", font=("Arial", 9))
        self.status_label.grid(row=0, column=7, padx=10)

        # Chat area
        chat_frame = tk.Frame(self.root, bg="#ecf0f1")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, font=("Arial", 10),
                                                     bg="#ffffff", fg="#2c3e50", state=tk.DISABLED,
                                                     relief=tk.FLAT, padx=10, pady=10)
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        self.chat_display.tag_config("system", foreground="#7f8c8d", font=("Arial", 9, "italic"))
        self.chat_display.tag_config("sent", foreground="#2980b9", font=("Arial", 10))
        self.chat_display.tag_config("received", foreground="#27ae60", font=("Arial", 10))
        self.chat_display.tag_config("error", foreground="#e74c3c", font=("Arial", 9))
        self.chat_display.tag_config("timestamp", foreground="#95a5a6", font=("Arial", 8))
        self.chat_display.tag_config("file", foreground="#9b59b6", font=("Arial", 10))

        input_frame = tk.Frame(self.root, bg="#ecf0f1", padx=10, pady=5)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.file_btn = tk.Button(input_frame, text="File", command=self.attach_file,
                                  bg="#9b59b6", fg="white", font=("Arial", 10), width=6, state=tk.DISABLED)
        self.file_btn.pack(side=tk.LEFT, ipady=5, padx=(0,5))

        self.message_entry = tk.Entry(input_frame, font=("Arial", 11), bg="#ffffff", state=tk.DISABLED)
        self.message_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=8, padx=(0, 5))
        self.message_entry.bind("<Return>", lambda e: self.send_message())

        self.send_btn = tk.Button(input_frame, text="Send", command=self.send_message,
                                  bg="#3498db", fg="white", font=("Arial", 10, "bold"), padx=20, state=tk.DISABLED)
        self.send_btn.pack(side=tk.RIGHT, ipady=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def add_message(self, message, tag=""):
        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")
        if tag:
            self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_display.insert(tk.END, f"{message}\n", tag)
        else:
            self.chat_display.insert(tk.END, f"[{timestamp}] {message}\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def connect(self):
        if self.connected:
            self.disconnect()
            return

        server = self.server_entry.get().strip()
        port = self.port_entry.get().strip()
        name = self.name_entry.get().strip()
        if not server or not port or not name:
            messagebox.showerror("Error", "Please fill in all connection fields")
            return
        try:
            port = int(port)
        except:
            messagebox.showerror("Error","Port must be a number")
            return

        self.username = name
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        try:
            self.add_message(f"Connecting to {server}:{port}...", "system")
            self.sock.connect((server, port))
            self.sock.settimeout(None)
            # send username
            self.sock.sendall((name + '\n').encode('utf-8'))
            self.connected = True
            self.add_message(f"Connected as {name}", "system")
            self.status_label.config(text="Connected", fg="#27ae60")
            self.connect_btn.config(text="Disconnect", bg="#e74c3c")
            self.message_entry.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)
            self.file_btn.config(state=tk.NORMAL)
            self.server_entry.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.name_entry.config(state=tk.DISABLED)
            # start receive thread
            threading.Thread(target=self.receive_loop, daemon=True).start()
        except Exception as e:
            self.add_message(f"Connection failed: {e}", "error")
            self.sock = None
            self.connected = False

    def disconnect(self):
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        self.add_message("Disconnected from server", "system")
        self.status_label.config(text="Disconnected", fg="#e74c3c")
        self.connect_btn.config(text="Connect", bg="#27ae60")
        self.message_entry.config(state=tk.DISABLED)
        self.send_btn.config(state=tk.DISABLED)
        self.file_btn.config(state=tk.DISABLED)
        self.server_entry.config(state=tk.NORMAL)
        self.port_entry.config(state=tk.NORMAL)
        self.name_entry.config(state=tk.NORMAL)

    def receive_loop(self):
        """Receive data, handle both text lines and binary file transfers."""
        buffer = b''
        try:
            while self.connected:
                data = self.sock.recv(8192)
                if not data:
                    self.root.after(0, lambda: self.add_message("Server closed connection", "error"))
                    self.root.after(0, self.disconnect)
                    break
                buffer += data
                # process buffer: prefer file marker
                while True:
                    if buffer.startswith(HEADER_MARKER):
                        # ensure header complete
                        if b'\n\n' not in buffer:
                            break  # need more data
                        header, buffer = buffer.split(b'\n\n', 1)
                        parts = header.split(b'\n')
                        if len(parts) < 3:
                            # malformed header, skip
                            continue
                        # parts: __FILE__, filename, filesize
                        filename = parts[1].decode(errors='ignore')
                        try:
                            filesize = int(parts[2].decode())
                        except:
                            filesize = 0
                        # wait until we have the full file bytes
                        if len(buffer) < filesize:
                            while len(buffer) < filesize:
                                more = self.sock.recv(8192)
                                if not more:
                                    raise ConnectionError("Disconnected during file download")
                                buffer += more
                        file_bytes = buffer[:filesize]
                        buffer = buffer[filesize:]
                        # save file (ask user where to save)
                        self.root.after(0, lambda fn=filename, fb=file_bytes: self.on_file_received(fn, fb))
                        continue  # continue processing buffer
                    # otherwise try to process newline-terminated text lines
                    if b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)
                        try:
                            text = line.decode('utf-8', errors='ignore')
                        except:
                            text = "<decode error>"
                        # display text (normal chat message)
                        self.root.after(0, lambda t=text: self.add_message(t, "received"))
                        continue
                    # nothing more to parse right now
                    break
        except Exception as e:
            if self.connected:
                self.root.after(0, lambda: self.add_message(f"Receive error: {e}", "error"))
                self.root.after(0, self.disconnect)

    def on_file_received(self, filename, file_bytes):
        """Called on the GUI thread when a full file has been received."""
        try:
            # show a message and prompt to save
            display_name = os.path.basename(filename)
            self.add_message(f"Received file: {display_name} ({len(file_bytes)} bytes)", "file")

            # Ask user where to save
            default_path = os.path.join(DOWNLOAD_DIR, display_name)
            save_path = filedialog.asksaveasfilename(initialfile=display_name,
                                                     defaultextension=os.path.splitext(display_name)[1],
                                                     initialdir=DOWNLOAD_DIR,
                                                     title=f"Save {display_name}")
            if save_path:
                with open(save_path, 'wb') as f:
                    f.write(file_bytes)
                self.add_message(f"Saved file to: {save_path}", "system")
            else:
                # If user canceled, auto-save into downloads with unique name
                base, ext = os.path.splitext(default_path)
                i = 1
                dest = default_path
                while os.path.exists(dest):
                    dest = f"{base}_{i}{ext}"
                    i += 1
                with open(dest, 'wb') as f:
                    f.write(file_bytes)
                self.add_message(f"Auto-saved file to: {dest}", "system")
        except Exception as e:
            self.add_message(f"Failed saving received file: {e}", "error")

    def attach_file(self):
        if not self.connected:
            messagebox.showwarning("Warning", "Not connected")
            return
        file_path = filedialog.askopenfilename(title="Select file to send")
        if not file_path:
            return
        try:
            size = os.path.getsize(file_path)
            if size == 0:
                messagebox.showerror("Error", "Cannot send empty file")
                return
            if size > MAX_FILE_SIZE:
                messagebox.showerror("Error", f"File too large (limit {MAX_FILE_SIZE} bytes)")
                return
            filename = os.path.basename(file_path)
            # send in background thread
            threading.Thread(target=self._send_file_thread, args=(file_path, filename, size), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to send file: {e}")

    def _send_file_thread(self, file_path, filename, filesize):
        """Send file using header + raw bytes (in a background thread)."""
        try:
            # header: marker + filename + filesize + blank line
            header = HEADER_MARKER + filename.encode('utf-8') + b'\n' + str(filesize).encode('ascii') + b'\n\n'
            # send header
            self.sock.sendall(header)
            # now send file in chunks
            sent = 0
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(4096)
                    if not chunk:
                        break
                    self.sock.sendall(chunk)
                    sent += len(chunk)
            self.root.after(0, lambda: self.add_message(f"Sent file: {filename} ({self.format_size(filesize)})", "file"))
        except Exception as e:
            self.root.after(0, lambda: self.add_message(f"File send failed: {e}", "error"))

    def send_message(self):
        if not self.connected:
            return
        message = self.message_entry.get().strip()
        if not message:
            return
        try:
            self.sock.sendall((message + '\n').encode('utf-8'))
            self.add_message(f"You: {message}", "sent")
            self.message_entry.delete(0, tk.END)
        except Exception as e:
            self.add_message(f"Send failed: {e}", "error")
            self.disconnect()

    def format_size(self, size):
        for unit in ['B','KB','MB','GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    def on_closing(self):
        if self.connected:
            self.disconnect()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ChatClient(root)
    root.mainloop()

if __name__ == '__main__':
    main()
