import sys
import os
from cx_Freeze import setup, Executable

print('Compiling channeller.py')
import py_compile
py_compile.compile('channeller.py', 'channeller.pyc')

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    "packages": ["tkinter", "pyaudio"],
    "excludes": ["userfunctions", "Tkinter", "channeller", "extensions", "numpy", "scipy", "curses", "psutil"],
    "include_files": ["images/", "logs/", "guide.txt", "ffmpeg.exe", "ffprobe.exe", "yt_cache/", "wave_cache/", "config/", "userfunctions.py", "extensions.py", "channeller.pyc"],
    "silent": True,
    "path": sys.path,
}
os.environ['TCL_LIBRARY'] = r'C:\Users\Key Cohen Office\AppData\Local\Programs\Python\Python38\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\Key Cohen Office\AppData\Local\Programs\Python\Python38\tcl\tk8.6'

# GUI applications require a different base on Windows (the default is for a
# console application).
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="Channeller",
    version="2.4",
    description="Mr. Fairs\' new audio software. Made by Yovel Key-Cohen '21. QLab is better. SFX is worse.",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base, icon='images/favicon.ico', targetName="Channeller.exe")],
)