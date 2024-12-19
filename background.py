import tkinter as tk
import customtkinter as ctk
import os
import cv2
from PIL import Image, ImageTk
import threading
from pathlib import Path
import time
from tkinter import filedialog
import shutil
import win32gui
import win32con
import win32api
import pygame
from ctypes import windll, wintypes, byref, c_int
import pystray
from PIL import Image
import sys

class WallpaperEngine:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Python Wallpaper Engine")
        self.root.geometry("1200x700")
        
        self.icon = None
        self.create_tray_icon()
        
        self.videos_dir = "wallpapers/Videos"
        os.makedirs(self.videos_dir, exist_ok=True)
        
        self.processed_files = set()
        self.videos = set([
            "wallpapers/Videos/cozy-camp.3840x2160.mp4",
            "wallpapers/Videos/moonlit-bloom-cherry.3840x2160.mp4"
        ])
        
        for file in os.listdir(self.videos_dir):
            if file.endswith(('.mp4', '.mkv', '.avi', '.mov')):
                video_path = os.path.join(self.videos_dir, file)
                self.videos.add(video_path)
        
        self.playing = False
        self.current_wallpaper = None
        
        pygame.init()
        
        self.progman = win32gui.FindWindow("Progman", None)
        win32gui.SendMessageTimeout(self.progman, 0x052C, 0, 0, 0x0, 1000)
        self.workerw = 0
        
        def enumWindowsProc(hwnd, lParam):
            p = win32gui.FindWindowEx(hwnd, 0, "SHELLDLL_DefView", None)
            if p:
                self.workerw = win32gui.FindWindowEx(0, hwnd, "WorkerW", None)
            return True
        
        win32gui.EnumWindows(enumWindowsProc, 0)
        
        self.screen_width = win32api.GetSystemMetrics(0)
        self.screen_height = win32api.GetSystemMetrics(1)
        
        self.create_gui()

    def create_tray_icon(self):
        icon_image = Image.new('RGB', (64, 64), color='blue')
        menu = (
            pystray.MenuItem('Show', self.show_window),
            pystray.MenuItem('Exit', self.quit_app)
        )
        self.icon = pystray.Icon("WallpaperEngine", icon_image, "Wallpaper Engine", menu)

    def show_window(self, icon, item):
        self.root.deiconify()
        self.root.lift()
        self.root.state('normal')
        
    def hide_window(self):
        self.root.withdraw()
        if self.icon and not self.icon.visible:
            self.icon.run()
            
    def quit_app(self, icon, item):
        self.playing = False
        time.sleep(0.2)
        icon.stop()
        self.root.quit()
        sys.exit()

    def play_video(self):
        try:
            os.environ['SDL_WINDOWID'] = str(self.workerw)
            screen = pygame.display.set_mode((self.screen_width, self.screen_height))
            pygame.display.init()
            
            cap = cv2.VideoCapture(self.current_wallpaper)
            fps = cap.get(cv2.CAP_PROP_FPS)
            clock = pygame.time.Clock()
            
            while self.playing:
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                
                frame = cv2.resize(frame, (self.screen_width, self.screen_height))
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                frame = pygame.surfarray.make_surface(frame.swapaxes(0, 1))
                
                # Draw frame
                screen.blit(frame, (0, 0))
                pygame.display.flip()
                
                clock.tick(fps)
                
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self.playing = False
            
            cap.release()
            pygame.quit()
            pygame.init()
            
        except Exception as e:
            print(f"Video playback error: {e}")

    def apply_wallpaper(self, path):
        if self.playing:
            self.playing = False
            time.sleep(0.2)
        
        if not os.path.exists(path):
            print(f"Error: File not found - {path}")
            return
        
        self.current_wallpaper = path
        self.playing = True
        
        threading.Thread(target=self.play_video, daemon=True).start()

    def create_gui(self):
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        
        self.main_container = ctk.CTkFrame(self.root)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.add_button = ctk.CTkButton(
            self.main_container,
            text="+ Add Your Own Video",
            command=self.add_video,
            width=200
        )
        self.add_button.pack(pady=10)
        
        self.scrollable_frame = ctk.CTkScrollableFrame(self.main_container)
        self.scrollable_frame.pack(fill="both", expand=True, padx=5)
        
        self.scrollable_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        self.refresh_wallpapers()

    def refresh_wallpapers(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.processed_files.clear()
        
        row, col = 0, 0
        for video in sorted(self.videos):
            if video not in self.processed_files:
                self.create_wallpaper_card(video, row, col)
                self.processed_files.add(video)
                col += 1
                if col >= 3:
                    col = 0
                    row += 1

    def create_wallpaper_card(self, video_path, row, col):
        card = ctk.CTkFrame(self.scrollable_frame)
        card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")
        
        try:
            cap = cv2.VideoCapture(video_path)
            ret, frame = cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (280, 157))
                img = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(img)
                
                thumbnail = ctk.CTkLabel(card, image=photo, text="")
                thumbnail.image = photo
                thumbnail.pack(padx=5, pady=5)
            cap.release()
        except Exception as e:
            print(f"Thumbnail error: {e}")
            placeholder = ctk.CTkLabel(card, text="No Preview", 
                                     width=280, height=157)
            placeholder.pack(padx=5, pady=5)
        
        controls = ctk.CTkFrame(card, fg_color="transparent")
        controls.pack(fill="x", padx=5, pady=5)
        
        name = os.path.basename(video_path)
        name = os.path.splitext(name)[0]
        name_label = ctk.CTkLabel(controls, text=name, 
                                font=("Arial", 12))
        name_label.pack(side="left", padx=5)
        
        if video_path not in [
            "wallpapers/Videos/cozy-camp.3840x2160.mp4",
            "wallpapers/Videos/moonlit-bloom-cherry.3840x2160.mp4"
        ]:
            delete_btn = ctk.CTkButton(controls, text="×", 
                                     command=lambda: self.delete_video(video_path),
                                     width=30,
                                     fg_color="red",
                                     hover_color="darkred")
            delete_btn.pack(side="right", padx=5)
        
        apply_btn = ctk.CTkButton(card, text="Apply", 
                                command=lambda: self.apply_wallpaper(video_path),
                                width=120)
        apply_btn.pack(pady=5)

    def delete_video(self, video_path):
        try:
            if self.current_wallpaper == video_path:
                self.playing = False
                time.sleep(0.1)
            
            os.remove(video_path)
            self.videos.remove(video_path)
            self.refresh_wallpapers()
        except Exception as e:
            print(f"Delete video error: {e}")

    def add_video(self):
        file_path = filedialog.askopenfilename(
            title="Select a Video File",
            filetypes=[
                ("Video files", "*.mp4 *.mkv *.avi *.mov"),
                ("All files", "*.*")
            ]
        )
        
        if file_path:
            filename = os.path.basename(file_path)
            destination = os.path.join(self.videos_dir, filename)
            
            try:
                shutil.copy2(file_path, destination)
                self.videos.add(destination)
                self.refresh_wallpapers()
            except Exception as e:
                error_window = ctk.CTkToplevel(self.root)
                error_window.title("Error")
                error_window.geometry("300x100")
                label = ctk.CTkLabel(error_window, text=f"Error adding video:\n{str(e)}")
                label.pack(pady=20)

    def run(self):
        threading.Thread(target=self.icon.run, daemon=True).start()
        self.root.mainloop()

if __name__ == "__main__":
    app = WallpaperEngine()
    app.run()
    
    
