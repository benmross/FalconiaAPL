import tkinter as tk

class ControlsPanel:
    def __init__(self, parent, app):
        self.app = app
        self.frame = tk.LabelFrame(parent, text="Controls", padx=5, pady=5)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Make the controls frame focusable
        self.frame.configure(takefocus=1)
        
        # Create a grid for the keyboard-like layout
        # Define control commands for each button
        self.control_commands = {
            "Spectral (E)": "spectral",
            "Humiture (Q)": "humiture",
            "Left (A)": "left",
            "Right (D)": "right", 
            "Forward (W)": "forward",
            "Backward (S)": "backward",
            "Stop (X)": "stop",
            "Calibrate MPU6050": "calibrate"
        }
        
        self.control_buttons = {}
        
        # Create a 3x3 grid layout to match keyboard layout
        # Empty frame for grid layout
        self.grid_frame = tk.Frame(self.frame)
        self.grid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=10)
        
        # Store original button colors for reset
        self.original_bg = None
        
        # Row 0 (Top row): Q - W - E
        btn_command = lambda cmd=self.control_commands["Humiture (Q)"]: self.app.send_command(cmd)
        self.control_buttons["Humiture (Q)"] = tk.Button(
            self.grid_frame, text="Q\nHumiture", command=btn_command, height=2, width=8, state=tk.DISABLED
        )
        self.control_buttons["Humiture (Q)"].grid(row=0, column=0, padx=2, pady=2)
        
        btn_command = lambda cmd=self.control_commands["Forward (W)"]: self.app.send_command(cmd)
        self.control_buttons["Forward (W)"] = tk.Button(
            self.grid_frame, text="W\nForward", command=btn_command, height=2, width=8, state=tk.DISABLED
        )
        self.control_buttons["Forward (W)"].grid(row=0, column=1, padx=2, pady=2)
        
        btn_command = lambda cmd=self.control_commands["Spectral (E)"]: self.app.send_command(cmd)
        self.control_buttons["Spectral (E)"] = tk.Button(
            self.grid_frame, text="E\nSpectral", command=btn_command, height=2, width=8, state=tk.DISABLED
        )
        self.control_buttons["Spectral (E)"].grid(row=0, column=2, padx=2, pady=2)
        
        # Row 1 (Middle row): A - S - D
        btn_command = lambda cmd=self.control_commands["Left (A)"]: self.app.send_command(cmd)
        self.control_buttons["Left (A)"] = tk.Button(
            self.grid_frame, text="A\nLeft", command=btn_command, height=2, width=8, state=tk.DISABLED
        )
        self.control_buttons["Left (A)"].grid(row=1, column=0, padx=2, pady=2)
        
        btn_command = lambda cmd=self.control_commands["Backward (S)"]: self.app.send_command(cmd)
        self.control_buttons["Backward (S)"] = tk.Button(
            self.grid_frame, text="S\nBackward", command=btn_command, height=2, width=8, state=tk.DISABLED
        )
        self.control_buttons["Backward (S)"].grid(row=1, column=1, padx=2, pady=2)
        
        btn_command = lambda cmd=self.control_commands["Right (D)"]: self.app.send_command(cmd)
        self.control_buttons["Right (D)"] = tk.Button(
            self.grid_frame, text="D\nRight", command=btn_command, height=2, width=8, state=tk.DISABLED
        )
        self.control_buttons["Right (D)"].grid(row=1, column=2, padx=2, pady=2)
        
        # Row 2 (Bottom row): Other controls
        stop_command = lambda: self._handle_stop()
        self.control_buttons["Stop (X)"] = tk.Button(
            self.grid_frame, text="X\nStop", command=stop_command, height=2, width=8, state=tk.DISABLED
        )
        self.control_buttons["Stop (X)"].grid(row=2, column=1, padx=2, pady=10)
        
        # Calibration button below the main controls
        btn_command = lambda cmd=self.control_commands["Calibrate MPU6050"]: self.app.send_command(cmd)
        self.control_buttons["Calibrate MPU6050"] = tk.Button(
            self.frame, text="Calibrate", command=btn_command, state=tk.DISABLED
        )
        self.control_buttons["Calibrate MPU6050"].pack(fill=tk.X, padx=2, pady=2)
        
        # Add instruction label for keyboard controls
        instructions = "Click here to enable keyboard controls.\nW,A,S,D,Q,E keys work when this panel is selected."
        self.instruction_label = tk.Label(self.frame, text=instructions, fg="blue")
        self.instruction_label.pack(pady=5)
        
        # Create a "Deselect Controls" button to allow explicit deselection
        self.deselect_button = tk.Button(
            self.frame, 
            text="Deselect Controls", 
            command=self._deselect_controls
        )
        self.deselect_button.pack(fill=tk.X, padx=2, pady=2)
        
        # Visual indicator for focus state
        self.focus_indicator = tk.Frame(self.frame, height=10, bg="gray")
        self.focus_indicator.pack(fill=tk.X, padx=2, pady=(5, 0))
        
        # Add keyboard bindings for the controls frame
        self.grid_frame.bind("<FocusIn>", self._on_focus_in)
        self.grid_frame.bind("<FocusOut>", self._on_focus_out)
        
        # Make the grid frame focusable and clickable
        self.grid_frame.configure(takefocus=1)
        self.grid_frame.bind("<Button-1>", lambda e: self.grid_frame.focus_set())
        
        # Add key bindings to the grid frame
        self.grid_frame.bind("w", lambda e: self.app.key_press_handler("Forward (W)"))
        self.grid_frame.bind("a", lambda e: self.app.key_press_handler("Left (A)"))
        self.grid_frame.bind("s", lambda e: self.app.key_press_handler("Backward (S)"))
        self.grid_frame.bind("d", lambda e: self.app.key_press_handler("Right (D)"))
        self.grid_frame.bind("q", lambda e: self.app.key_press_handler("Humiture (Q)"))
        self.grid_frame.bind("e", lambda e: self.app.key_press_handler("Spectral (E)"))
        self.grid_frame.bind("x", lambda e: self._handle_stop())
        
        # Store original background color when initialized
        if not self.original_bg and len(self.control_buttons) > 0:
            first_button = next(iter(self.control_buttons.values()))
            self.original_bg = first_button.cget('background')
    
    def _on_focus_in(self, event):
        """Handle focus in event"""
        self.instruction_label.config(text="Keyboard controls ACTIVE", fg="green")
        self.focus_indicator.config(bg="green")
        self.frame.config(relief=tk.RAISED)
    
    def _on_focus_out(self, event):
        """Handle focus out event"""
        instructions = "Click here to enable keyboard controls.\nW,A,S,D,Q,E keys work when this panel is selected."
        self.instruction_label.config(text=instructions, fg="blue")
        self.focus_indicator.config(bg="gray")
        self.frame.config(relief=tk.GROOVE)
        # Reset button states when focus is lost
        self._reset_button_states()
    
    def _deselect_controls(self):
        """Explicitly deselect the control panel"""
        # Move focus to the parent window
        self.frame.master.focus_set()
    
    def _handle_stop(self):
        """Handle stop button press - send command and reset button states"""
        # First send the stop command
        self.app.send_command(self.control_commands["Stop (X)"])
        # Then reset all button visual states
        self._reset_button_states()
    
    def _reset_button_states(self):
        """Reset all button visual states to default"""
        if self.original_bg is None:
            # Get the original background color from the first button if not set
            if len(self.control_buttons) > 0:
                first_button = next(iter(self.control_buttons.values()))
                self.original_bg = first_button.cget('background')
            else:
                return
        
        # Reset all buttons except Stop and Calibrate to original state
        for button_name, button in self.control_buttons.items():
            if button_name != "Stop (X)" and button_name != "Calibrate MPU6050":
                button.config(relief=tk.RAISED, bg=self.original_bg)
    
    def update_control_buttons(self, enabled):
        """Enable or disable control buttons based on connection status"""
        state = tk.NORMAL if enabled else tk.DISABLED
        for button in self.control_buttons.values():
            button.config(state=state)
        self.deselect_button.config(state=tk.NORMAL)  # Always keep deselect button enabled
