import tkinter as tk

class AprilTagPanel:
    def __init__(self, parent, app):
        self.app = app
        
        # AprilTag Info Frame
        self.tags_frame = tk.LabelFrame(parent, text="AprilTag Detection", padx=5, pady=5)
        self.tags_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a scrollable list for tag IDs
        self.tags_list_frame = tk.Frame(self.tags_frame)
        self.tags_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar for the list
        self.scrollbar = tk.Scrollbar(self.tags_list_frame)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Listbox to display tag IDs
        self.tags_listbox = tk.Listbox(self.tags_list_frame, yscrollcommand=self.scrollbar.set,
                                      font=("Courier", 10), height=6)
        self.tags_listbox.pack(fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.tags_listbox.yview)
        
        # Status label
        self.status_label = tk.Label(self.tags_frame, text="No tags detected")
        self.status_label.pack(fill=tk.X)
        
        # Dictionary to keep track of detected tags
        self.detected_tags_dict = {}
    
    def update_tags_display(self, tags):
        """Update the tags display with the list of detected AprilTags"""
        if not tags:
            self.status_label.config(text="No tags detected")
            return
            
        # Update our dictionary of detected tags
        for tag in tags:
            tag_id = tag.tag_id
            distance = None
            
            # Get distance if available
            if hasattr(tag, 'pose_t'):
                distance = float(round(float(tag.pose_t[2]), 2))  # Z-distance
                
            tag_info = f"ID: {tag_id}"
            if distance is not None:
                tag_info += f" - Distance: {distance}m"
                
            self.detected_tags_dict[tag_id] = tag_info
            
        # Update listbox with all detected tags
        self.tags_listbox.delete(0, tk.END)
        for tag_id, info in sorted(self.detected_tags_dict.items()):
            self.tags_listbox.insert(tk.END, info)
            
        # Update status
        self.status_label.config(text=f"{len(self.detected_tags_dict)} unique tags detected")