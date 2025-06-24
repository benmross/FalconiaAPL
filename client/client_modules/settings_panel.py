import tkinter as tk
from tkinter import ttk
import json
import os

class SettingsPanel:
    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a scrollable container for settings
        self.canvas = tk.Canvas(self.frame)
        scrollbar = ttk.Scrollbar(self.frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add mouse wheel scrolling
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)           # Windows and MacOS
        self.canvas.bind("<Button-4>", self._on_mousewheel)             # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_mousewheel)             # Linux scroll down
        
        # Initialize settings
        self.key_bindings = {
            "Forward": "w",
            "Backward": "s",
            "Left": "a",
            "Right": "d",
            "Spectral": "e",
            "Humiture": "q",
            "Stop": "x"
        }
        
        self.mqtt_port = tk.StringVar(value="1883")
        self.camera_port = tk.StringVar(value="7123")
        self.camera_refresh_rate = tk.StringVar(value="10")
        self.sensor_refresh_rate = tk.StringVar(value="100")
        
        # Load settings if exist
        self.load_settings()
        
        # Create the settings UI
        self.create_settings_ui()
        
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        if event.num == 4 or event.delta > 0:
            # Scroll up (Linux uses event.num, Windows/Mac uses event.delta)
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            # Scroll down
            self.canvas.yview_scroll(1, "units")
    
    def create_settings_ui(self):
        """Create the settings user interface"""
        # Title label
        title_label = ttk.Label(self.scrollable_frame, text="Rover Control Settings", font=("Arial", 14, "bold"))
        title_label.grid(row=0, column=0, columnspan=4, pady=(10, 20), sticky="w")
        
        # Create sections
        row = 1
        
        # Section: Port Settings
        self.create_section_header("Connection Settings", row)
        row += 1
        
        # MQTT Port
        ttk.Label(self.scrollable_frame, text="MQTT Port:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        ttk.Entry(self.scrollable_frame, textvariable=self.mqtt_port, width=10).grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1
        
        # Camera Port
        ttk.Label(self.scrollable_frame, text="Camera Port:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        ttk.Entry(self.scrollable_frame, textvariable=self.camera_port, width=10).grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1
        
        # Section: Refresh Rates
        self.create_section_header("Refresh Rates (Requires Reboot)", row)
        row += 1
        
        # Camera Refresh Rate (ms)
        ttk.Label(self.scrollable_frame, text="Camera Refresh Rate (ms):").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        ttk.Entry(self.scrollable_frame, textvariable=self.camera_refresh_rate, width=10).grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1
        
        # Sensor Refresh Rate (ms)
        ttk.Label(self.scrollable_frame, text="Sensor Refresh Rate (ms):").grid(row=row, column=0, padx=10, pady=5, sticky="w")
        ttk.Entry(self.scrollable_frame, textvariable=self.sensor_refresh_rate, width=10).grid(row=row, column=1, padx=10, pady=5, sticky="w")
        row += 1
        
        # Section: Key Bindings
        self.create_section_header("Control Key Bindings", row)
        row += 1
        
        # Create key binding entries
        self.key_binding_entries = {}
        
        for i, (action, key) in enumerate(self.key_bindings.items()):
            ttk.Label(self.scrollable_frame, text=f"{action}:").grid(row=row+i, column=0, padx=10, pady=5, sticky="w")
            entry = ttk.Entry(self.scrollable_frame, width=5)
            entry.insert(0, key)
            entry.grid(row=row+i, column=1, padx=10, pady=5, sticky="w")
            entry.bind("<KeyRelease>", lambda e, action=action: self.on_key_change(e, action))
            self.key_binding_entries[action] = entry
            
            # Add label explaining the action
            action_desc = self.get_action_description(action)
            ttk.Label(self.scrollable_frame, text=action_desc).grid(row=row+i, column=2, padx=10, pady=5, sticky="w")
        
        row += len(self.key_bindings)
        row += 1
        
        # Save and Reset buttons
        button_frame = ttk.Frame(self.scrollable_frame)
        button_frame.grid(row=row, column=0, columnspan=4, pady=20)
        
        ttk.Button(button_frame, text="Save Settings", command=self.save_settings).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_to_defaults).pack(side=tk.LEFT, padx=10)
    
    def create_section_header(self, text, row):
        """Create a section header"""
        header = ttk.Label(self.scrollable_frame, text=text, font=("Arial", 12, "bold"))
        header.grid(row=row, column=0, columnspan=4, padx=5, pady=(15, 5), sticky="w")
        
        # Add a separator
        separator = ttk.Separator(self.scrollable_frame, orient="horizontal")
        separator.grid(row=row+1, column=0, columnspan=4, sticky="ew", padx=5)
    
    def get_action_description(self, action):
        """Return description for each action"""
        descriptions = {
            "Forward": "Move rover forward",
            "Backward": "Move rover backward",
            "Left": "Turn rover left",
            "Right": "Turn rover right",
            "Spectral": "Take spectral reading",
            "Humiture": "Take humiture reading",
            "Stop": "Stop all motion"
        }
        return descriptions.get(action, "")
    
    def on_key_change(self, event, action):
        """Handle key entry change event"""
        if event.keysym:
            key = event.keysym.lower()
            # Only allow single character keys
            if len(key) == 1:
                self.key_binding_entries[action].delete(0, tk.END)
                self.key_binding_entries[action].insert(0, key)
                self.key_bindings[action] = key
            else:
                # Reset to the previous value
                self.key_binding_entries[action].delete(0, tk.END)
                self.key_binding_entries[action].insert(0, self.key_bindings[action])
    
    def load_settings(self):
        """Load settings from config file"""
        try:
            if os.path.exists(self.app.config_file):
                with open(self.app.config_file, 'r') as f:
                    settings = json.load(f)
                
                # Load key bindings if present
                if 'key_bindings' in settings:
                    self.key_bindings.update(settings['key_bindings'])
                
                # Load port settings if present
                if 'mqtt_port' in settings:
                    self.mqtt_port.set(str(settings['mqtt_port']))
                if 'camera_port' in settings:
                    self.camera_port.set(str(settings['camera_port']))
                
                # Load refresh rates if present
                if 'camera_refresh_rate' in settings:
                    self.camera_refresh_rate.set(str(settings['camera_refresh_rate']))
                if 'sensor_refresh_rate' in settings:
                    self.sensor_refresh_rate.set(str(settings['sensor_refresh_rate']))
        except Exception as e:
            print(f"Error loading settings: {e}")
    
    def save_settings(self):
        """Save settings to config file"""
        # Get current key bindings from entries
        for action, entry in self.key_binding_entries.items():
            value = entry.get()
            if value:
                self.key_bindings[action] = value
        
        # Prepare settings dictionary
        settings = {
            'key_bindings': self.key_bindings,
            'mqtt_port': int(self.mqtt_port.get()),
            'camera_port': int(self.camera_port.get()),
            'camera_refresh_rate': int(self.camera_refresh_rate.get()),
            'sensor_refresh_rate': int(self.sensor_refresh_rate.get())
        }
        
        try:
            # Save to file
            with open(self.app.config_file, 'w') as f:
                json.dump(settings, f, indent=4)
            
            # Update app settings
            self.app.MQTT_PORT = int(self.mqtt_port.get())
            
            # Apply key bindings
            self.apply_key_bindings()
            
            # Show success message
            self.show_status_message("Settings saved successfully!")
        except Exception as e:
            self.show_status_message(f"Error saving settings: {str(e)}", error=True)
    
    def reset_to_defaults(self):
        """Reset all settings to default values"""
        # Reset key bindings
        default_bindings = {
            "Forward": "w",
            "Backward": "s",
            "Left": "a",
            "Right": "d",
            "Spectral": "e",
            "Humiture": "q",
            "Stop": "x"
        }
        
        self.key_bindings = default_bindings.copy()
        
        # Update entry fields
        for action, key in default_bindings.items():
            self.key_binding_entries[action].delete(0, tk.END)
            self.key_binding_entries[action].insert(0, key)
        
        # Reset port values
        self.mqtt_port.set("1883")
        self.camera_port.set("7123")
        
        # Reset refresh rates
        self.camera_refresh_rate.set("10")
        self.sensor_refresh_rate.set("100")
        
        self.show_status_message("Settings reset to defaults")
    
    def apply_key_bindings(self):
        """Apply the current key bindings to the controls panel"""
        # Find the grid frame in the controls panel
        controls_panel = self.app.controls_panel
        for widget in controls_panel.frame.winfo_children():
            if isinstance(widget, tk.Frame) and len(widget.winfo_children()) > 0:
                grid_frame = widget
                
                # Remove all existing key bindings
                for key in "wasdeqx":
                    try:
                        grid_frame.unbind(key)
                    except:
                        pass
                
                # Add new key bindings
                for action, key in self.key_bindings.items():
                    if action == "Forward":
                        grid_frame.bind(key, lambda e, btn="Forward (W)": self.app.key_press_handler(btn))
                    elif action == "Backward":
                        grid_frame.bind(key, lambda e, btn="Backward (S)": self.app.key_press_handler(btn))
                    elif action == "Left":
                        grid_frame.bind(key, lambda e, btn="Left (A)": self.app.key_press_handler(btn))
                    elif action == "Right":
                        grid_frame.bind(key, lambda e, btn="Right (D)": self.app.key_press_handler(btn))
                    elif action == "spectral":
                        grid_frame.bind(key, lambda e, btn="Spectral (E)": self.app.key_press_handler(btn))
                    elif action == "humiture":
                        grid_frame.bind(key, lambda e, btn="Humiture (Q)": self.app.key_press_handler(btn))
                    elif action == "Stop":
                        grid_frame.bind(key, lambda e, btn="Stop (X)": self.app.key_press_handler(btn))
                
                break
    
    def show_status_message(self, message, error=False):
        """Show a status message in a small popup"""
        popup = tk.Toplevel(self.app.root)
        popup.title("Settings")
        popup.geometry("300x100")
        popup.resizable(False, False)
        
        # Make it a modal dialog
        popup.grab_set()
        popup.transient(self.app.root)
        
        # Message
        color = "red" if error else "green"
        tk.Label(popup, text=message, fg=color, wraplength=280).pack(pady=20)
        
        # Close button
        tk.Button(popup, text="OK", command=popup.destroy).pack(pady=10)
        
        # Center the popup
        popup.update_idletasks()
        x = self.app.root.winfo_rootx() + (self.app.root.winfo_width() - popup.winfo_width()) // 2
        y = self.app.root.winfo_rooty() + (self.app.root.winfo_height() - popup.winfo_height()) // 2
        popup.geometry(f"+{x}+{y}")