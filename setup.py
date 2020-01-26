import sys
import os
from cx_Freeze import setup, Executable

"""
NOTE:
For some reason this generates the tkinter library with the name Tkinter, breaking imports.
This needs to be renamed manually in lib/
"""

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    "packages": ["tkinter", "pydub"],
    "excludes": ["userfunctions"],
    "include_files": ["images/", "logs/", "guide.txt", "ffprobe.exe", "ffmpeg.exe", "yt_cache/", "wave_cache/", "config/", "userfunctions.py"],
    "replace_paths": [ ("Tkinter", "tkinter") ],
    "silent": True
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
    version="2.1",
    description="Mr. Fairs\' new audio software. Made by Yovel Key-Cohen '21. QLab is better. SFX is worse.",
    options={"build_exe": build_exe_options},
    executables=[Executable("main.py", base=base, icon='images/favicon.ico', targetName="Channeller.exe")],
)