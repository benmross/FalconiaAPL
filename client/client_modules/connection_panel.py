import tkinter as tk
import json
import os

class ConnectionPanel:
    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.LabelFrame(parent, text="Connection", padx=5, pady=5)
        self.frame.pack(fill=tk.X, padx=5, pady=5)
        
        # IP address input with label
        ip_frame = tk.Frame(self.frame)
        ip_frame.pack(fill=tk.X, padx=2, pady=2)
        tk.Label(ip_frame, text="IP Address:").pack(side=tk.LEFT)
        self.ip_entry = tk.Entry(ip_frame)
        self.ip_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        # Load saved IP address
        self.load_config()
        
        # Save IP button
        self.save_ip_button = tk.Button(self.frame, text="Save IP", command=self.save_config)
        self.save_ip_button.pack(fill=tk.X, padx=2, pady=2)
        
        # Connect button
        self.connect_button = tk.Button(self.frame, text="Connect", command=self.app.toggle_connection)
        self.connect_button.pack(fill=tk.X, padx=2, pady=2)
    
    def load_config(self):
        """Load configuration from JSON file"""
        try:
            if os.path.exists(self.app.config_file):
                with open(self.app.config_file, 'r') as f:
                    config = json.load(f)
                    if "ip_address" in config:
                        self.ip_entry.insert(0, config["ip_address"])
        except Exception as e:
            print(f"Error loading config: {e}")
            # Set default IP
            #self.ip_entry.insert(0, "172.20.10.2")
    
    def save_config(self):
        """Save configuration to JSON file"""
        try:
            # Load existing config first to preserve other settings
            config = {}
            if os.path.exists(self.app.config_file):
                with open(self.app.config_file, 'r') as f:
                    config = json.load(f)
            
            # Update only the IP address
            config["ip_address"] = self.ip_entry.get()
            
            # Save the updated config
            with open(self.app.config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
            # Give feedback to the user that save was successful
            self.save_ip_button.config(text="Saved!")
            self.app.root.after(1000, lambda: self.save_ip_button.config(text="Save IP"))
        except Exception as e:
            print(f"Error saving config: {e}")
            # Give feedback that save failed
            self.save_ip_button.config(text="Save Failed")
            self.app.root.after(1000, lambda: self.save_ip_button.config(text="Save IP"))
