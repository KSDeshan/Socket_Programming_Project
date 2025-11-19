import tkinter as tk
from tkinter import scrolledtext, messagebox
from datetime import datetime

class ChatGUI:
    def __init__(self, root, title="Chat Client", width=720, height=600):
        self.root = root
        self.root.title(title)
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(500, 400)

        # Callbacks the client will set
        self.on_connect = None   # signature: func(server, port, name)
        self.on_send = None      # signature: func(message)
        self.on_close = None     # signature: func()

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _build_ui(self):
        conn_frame = tk.Frame(self.root, bg="#2c3e50", padx=10, pady=10)
        conn_frame.pack(fill=tk.X)

        tk.Label(conn_frame, text="Server:", bg="#2c3e50", fg="white", font=("Arial", 10)).grid(row=0, column=0, padx=5)
        self.server_entry = tk.Entry(conn_frame, width=20, font=("Arial", 10))
        self.server_entry.insert(0, "localhost")
        self.server_entry.grid(row=0, column=1, padx=5)

        tk.Label(conn_frame, text="Port:", bg="#2c3e50", fg="white", font=("Arial", 10)).grid(row=0, column=2, padx=5)
        self.port_entry = tk.Entry(conn_frame, width=8, font=("Arial", 10))
        self.port_entry.insert(0, "9090")
        self.port_entry.grid(row=0, column=3, padx=5)

        tk.Label(conn_frame, text="Name:", bg="#2c3e50", fg="white", font=("Arial", 10)).grid(row=0, column=4, padx=5)
        self.name_entry = tk.Entry(conn_frame, width=15, font=("Arial", 10))
        self.name_entry.grid(row=0, column=5, padx=5)

        self.connect_btn = tk.Button(conn_frame, text="Connect", command=self._connect_clicked,
                                     bg="#27ae60", fg="white", font=("Arial", 10, "bold"),
                                     padx=15, cursor="hand2")
        self.connect_btn.grid(row=0, column=6, padx=5)

        self.status_label = tk.Label(conn_frame, text="● Disconnected",
                                     bg="#2c3e50", fg="#e74c3c", font=("Arial", 9))
        self.status_label.grid(row=0, column=7, padx=10)

        chat_frame = tk.Frame(self.root, bg="#ecf0f1")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=("Arial", 10),
            bg="#ffffff",
            fg="#2c3e50",
            state=tk.DISABLED,
            relief=tk.FLAT,
            padx=10,
            pady=10
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)

        # text tags
        self.chat_display.tag_config("system", foreground="#7f8c8d", font=("Arial", 9, "italic"))
        self.chat_display.tag_config("sent", foreground="#2980b9", font=("Arial", 10, "bold"))
        self.chat_display.tag_config("received", foreground="#27ae60", font=("Arial", 10, "bold"))
        self.chat_display.tag_config("error", foreground="#e74c3c", font=("Arial", 9))
        self.chat_display.tag_config("timestamp", foreground="#95a5a6", font=("Arial", 8))

        input_frame = tk.Frame(self.root, bg="#ecf0f1", padx=10, pady=5)
        input_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.message_entry = tk.Entry(
            input_frame,
            font=("Arial", 11),
            bg="#ffffff",
            relief=tk.FLAT,
            state=tk.DISABLED
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, ipady=8, padx=(0, 5))
        self.message_entry.bind("<Return>", lambda e: self._send_clicked())

        self.send_btn = tk.Button(
            input_frame,
            text="Send",
            command=self._send_clicked,
            bg="#3498db",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=20,
            state=tk.DISABLED,
            cursor="hand2",
            relief=tk.FLAT
        )
        self.send_btn.pack(side=tk.RIGHT, ipady=5)

    # ----- Public API for client code -----
    def set_on_connect(self, callback):
        self.on_connect = callback

    def set_on_send(self, callback):
        self.on_send = callback

    def set_on_close(self, callback):
        self.on_close = callback

    def add_message(self, message, tag=""):
        """Thread-safe method to add message to the chat display."""
        if not self._in_main_thread():
            self.root.after(0, lambda: self.add_message(message, tag))
            return

        self.chat_display.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")

        if tag:
            self.chat_display.insert(tk.END, f"[{timestamp}] ", "timestamp")
            self.chat_display.insert(tk.END, f"{message}\n", tag)
        else:
            self.chat_display.insert(tk.END, f"[{timestamp}] {message}\n")

        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def update_status(self, connected: bool, text: str = None):
        if text is None:
            text = "● Connected" if connected else "● Disconnected"

        color = "#27ae60" if connected else "#e74c3c"
        self.status_label.config(text=text, fg=color)

        if connected:
            self.connect_btn.config(text="Disconnect", bg="#e74c3c")
            self.message_entry.config(state=tk.NORMAL)
            self.send_btn.config(state=tk.NORMAL)
            self.server_entry.config(state=tk.DISABLED)
            self.port_entry.config(state=tk.DISABLED)
            self.name_entry.config(state=tk.DISABLED)
        else:
            self.connect_btn.config(text="Connect", bg="#27ae60")
            self.message_entry.config(state=tk.DISABLED)
            self.send_btn.config(state=tk.DISABLED)
            self.server_entry.config(state=tk.NORMAL)
            self.port_entry.config(state=tk.NORMAL)
            self.name_entry.config(state=tk.NORMAL)

    def _in_main_thread(self):
        import threading
        return threading.current_thread() == threading.main_thread()

    # ----- Internal UI events -----
    def _connect_clicked(self):
        server = self.server_entry.get().strip()
        port = self.port_entry.get().strip()
        name = self.name_entry.get().strip()

        if not server or not port or not name:
            messagebox.showerror("Error", "Please fill in all connection fields")
            return

        try:
            port = int(port)
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return

        if self.on_connect:
            self.on_connect(server, port, name)

    def _send_clicked(self):
        message = self.message_entry.get().strip()
        if not message:
            return

        if self.on_send:
            self.on_send(message)
            self.message_entry.delete(0, tk.END)

    def _handle_close(self):
        if self.on_close:
            self.on_close()
        else:
            self.root.destroy()
