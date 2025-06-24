import tkinter as tk
from datetime import datetime

class ConsolePanel:
    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add scrollbar for console
        scroll_y = tk.Scrollbar(self.frame)
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Text widget for console output
        self.console_text = tk.Text(self.frame, height=20, wrap=tk.WORD, yscrollcommand=scroll_y.set)
        self.console_text.pack(fill=tk.BOTH, expand=True)
        scroll_y.config(command=self.console_text.yview)
    
    def log_message(self, message):
        """Add a message to the console with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.console_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.console_text.see(tk.END)  # Auto-scroll to bottom