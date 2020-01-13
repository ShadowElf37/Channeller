import sys
import os
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": ["tkinter", "pyaudio"],
                     "include_files": ["images/", "logs/", "guide.txt", "ffmpeg.exe", "yt_cache/", "wave_cache/"]}
os.environ['TCL_LIBRARY'] = r'C:\Users\Key Cohen Office\AppData\Local\Programs\Python\Python38\DLLs'
os.environ['TK_LIBRARY'] = r'C:\Users\Key Cohen Office\AppData\Local\Programs\Python\Python38\DLLs'

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="Channeller",
    version="1.0",
    description="Mr. Fairs\' new audio software. Made by Yovel Key-Cohen '21. QLab is better. SFX is worse.",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base, icon='images/favicon.ico')])