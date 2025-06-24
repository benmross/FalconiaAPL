import tkinter as tk
import cv2
import requests
import numpy as np
from PIL import Image, ImageTk

url = 'http://172.20.10.2:7123/stream.mjpg'

class StreamViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("MJPEG Stream Viewer")
        
        self.label = tk.Label(root)
        self.label.pack()
        
        self.bytes_data = bytearray()
        self.capture = cv2.VideoCapture(url)
        self.update_frame()
        
    def update_frame(self):
        ret, frame = self.capture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame)
            image = ImageTk.PhotoImage(image)
            self.label.config(image=image)
            self.label.image = image
        
        self.root.after(10, self.update_frame)  # Higher refresh rate for better FPS

if __name__ == "__main__":
    root = tk.Tk()
    viewer = StreamViewer(root)
    root.mainloop()
