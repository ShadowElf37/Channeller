import tkinter as tk
from PIL import Image, ImageTk, ImageTransform, ImageColor
import os
from time import sleep

def in_box(x, y, x1, y1, x2, y2):
    return x2 > x > x1 and y2 > y > y1

def htrgb(hex):
    hex = hex.strip('#')
    l = len(hex)
    scalar = 6//l
    if scalar == 0:
        raise ArithmeticError('Can\'t solve > 24-bit RGB values')
    elif scalar == 6:
        return (int(hex*2, 16),)*3
    return int(hex[:l//3]*scalar, 16), int(hex[l//3:2*l//3]*scalar, 16), int(hex[2*l//3:]*scalar, 16)


class Element:
    def __init__(self, app, w, h, x, y, xoffset=0, yoffset=0, woffset=0, hoffset=0):
        self.app: App = app
        self.root: tk.Tk = app.root
        self.w = w
        self.h = h
        self.x = x
        self.y = y
        self.xoffset = xoffset
        self.yoffset = yoffset
        self.woffset = woffset
        self.hoffset = hoffset
        self.tk_elements: [tk.Widget] = []

    def register(self, e):
        self.tk_elements.append(e)
        return e

    def draw(self):
        for elem in self.tk_elements:
            elem.configure(width=int(self.w * self.app.w + self.woffset),
                           height=int(self.h * self.app.h + self.hoffset))
            elem.place_forget()
            elem.place(x=int(self.x * self.app.w + self.xoffset),
                       y=int(self.y * self.app.h + self.yoffset))


class Canvas(Element):
    def __init__(self, app, w=1.0, h=1.0, x=0, y=0, bg='black', border_color='black', border_width=0, xoffset=0, yoffset=0, woffset=0, hoffset=0, **kwargs):
        """
        give w,h,x,y in fraction of screen
        """
        super().__init__(app, w, h, x, y, xoffset, yoffset, woffset, hoffset)
        self.bg = bg
        self.bdc = border_color
        self.bdw = border_width

        self.canvas = self.register(tk.Canvas(self.root, width=w*app.w, height=h*app.h, background=bg, highlightthickness=self.bdw, highlightbackground=self.bdc, **kwargs))
        self.canvas.place(x=x*app.w, y=y*app.h)

    def draw(self):
        super().draw()
        self.canvas.update()
        self.canvas.update_idletasks()

class Div(Element):
    def __init__(self, app, w=1.0, h=1.0, x=0, y=0, bg='black', border_color='black', border_width=0, xoffset=0, yoffset=0, woffset=0, hoffset=0, **kwargs):
        super().__init__(app, w, h, x, y, xoffset, yoffset, woffset, hoffset)
        self.bg = bg
        self.bdc = border_color
        self.bdw = border_width

        self.box = self.register(tk.Frame(self.root, width=w*app.w, height=h*app.h, background=bg, highlightthickness=self.bdw, highlightbackground=self.bdc, **kwargs))
        self.box.place(x=x*app.w, y=y*app.h)

    def draw(self):
        super().draw()


class Label(Element):
    def __init__(self, app, text='', w=0, h=0, x=0, y=0, bg='black', fg='white', border_color='black', border_width=0, xoffset=1, yoffset=1, woffset=0, hoffset=0, fontscale=1.0, anchor='center', **kwargs):
        super().__init__(app, w, h, x, y, xoffset, yoffset, woffset, hoffset)
        self.bg = bg
        self.fg = fg
        self.bdc = border_color
        self.bdw = border_width
        self.text = tk.StringVar()
        self.text.set(text)
        self.pre = ''
        self.fontscale = fontscale
        self.w /= 10
        self.h /= 10

        self.label = self.register(tk.Label(self.root, textvar=self.text, width=int(w*app.w), height=int(h*app.h), background=bg, fg=fg, highlightthickness=self.bdw, highlightbackground=self.bdc, font=(self.app.FONT, int(self.app.FONTSCALE*fontscale)), anchor=anchor, **kwargs))
        self.label.place(x=x*app.w, y=y*app.h)

    @property
    def fontsize(self):
        return int(self.app.FONTSCALE * self.fontscale * self.app.w / self.app.W)

    def draw(self):
        for elem in self.tk_elements:
            elem.configure(font=(self.app.FONT, self.fontsize))
        super().draw()

    def define_pre_label(self, text):
        self.pre = text

    def write(self, text):
        self.text.set(self.pre + text)
    def clear(self):
        self.text.set('')
    def read(self):
        return self.text.get()

class RightAlignLabel(Label):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.X = kwargs['x']
    def draw(self):
        self.x = self.X - (self.fontsize*len(self.read()) / self.app.w)
        super().draw()


class Button(Element):
    def __init__(self, app, w, h, x, y, text='', imgpath=None, cmd=lambda: None, bg='black', fg='white', bdc='white', xoffset=0, yoffset=0, woffset=0, hoffset=0, square=True):
        super().__init__(app, w, h, x, y, xoffset, yoffset, woffset, hoffset)
        self.bdc = bdc
        self.fg = fg
        self.bg = bg
        self.square = square
        self.text = tk.StringVar()
        self.text.set(text)
        self.img = imgpath and Image.open(imgpath)  # returns first falsey value
        self.tkimg = imgpath and ImageTk.PhotoImage(self.img)

        self.button = self.register(tk.Button(self.root, text=self.text, command=cmd, image=self.tkimg, width=int(w*app.w), height=int(h*app.h) if not self.square else int(w*app.w), background=bg, fg=fg,))
        self.button.place(x=x*app.w, y=y*app.h)

    def draw(self):
        super().draw()
        self.button.configure(width=int(self.w*self.app.w), height=int(self.h*self.app.h) if not self.square else int(self.w*self.app.w))


class ProgressBar(Element):
    def __init__(self, app, canvas, w=1.0, h=1.0, x=0, y=0, bg='black', fill_color='green', border_color='black', border_width=0, xoffset=0, yoffset=0, woffset=0, hoffset=0, initial_pct=0, **kwargs):
        super().__init__(app, w, h, x, y, xoffset, yoffset, woffset, hoffset)
        self.bg = bg
        self.bdc = border_color
        self.bdw = border_width
        self.fc = fill_color
        self.canvas: Canvas = canvas
        self.tk_canvas: tk.Canvas = canvas.canvas
        self.percent = initial_pct

        self.outer = self.tk_canvas.create_rectangle(self.x * self.canvas.w*self.app.w + self.xoffset - self.woffset,
                                                     self.y * self.canvas.h*self.app.h + self.yoffset - self.hoffset,
                                                     self.x * self.canvas.w*self.app.w + self.w * self.canvas.w*self.app.w + self.xoffset + self.woffset,
                                                     self.y * self.canvas.h*self.app.h + self.h * self.canvas.h*self.app.h + self.yoffset + self.hoffset,
                                                     outline=self.bdc)
        self.inner = self.tk_canvas.create_rectangle(self.x * self.canvas.w*self.app.w + self.xoffset - self.woffset + 1,
                                                     self.y * self.canvas.h*self.app.h + self.yoffset - self.hoffset + 1,
                                                     self.x * self.canvas.w * self.app.w + self.xoffset + (self.w * self.canvas.w * self.app.w + self.woffset) * self.percent / 100,
                                                     self.y * self.canvas.h*self.app.h + self.h * self.canvas.h*self.app.h + self.yoffset + self.hoffset - 1,
                                                     outline=None, fill=self.fc)

    def draw(self):
        self.tk_canvas.delete(self.outer)
        self.tk_canvas.delete(self.inner)
        coords = self.x * self.canvas.w*self.app.w + self.xoffset - self.woffset,\
                 self.y * self.canvas.h*self.app.h + self.yoffset - self.hoffset,\
                 self.x * self.canvas.w*self.app.w + self.w * self.canvas.w*self.app.w + self.xoffset + self.woffset,\
                 self.y * self.canvas.h*self.app.h + self.h * self.canvas.h*self.app.h + self.yoffset + self.hoffset
        self.outer = self.tk_canvas.create_rectangle(*coords, outline=self.bdc)
        self.inner = self.tk_canvas.create_rectangle(coords[0] + 1,
                                                     coords[1] + 1,
                                                     self.x * self.canvas.w * self.app.w + self.xoffset + (self.w * self.canvas.w * self.app.w  + self.woffset)*self.percent/100,
                                                     coords[3] - 1,
                                                     outline=None, fill=self.fc)


class App:
    def __init__(self, width, height, bg='black', **kwargs):
        self.DIR = os.getcwd()
        self.FONT = 'Lucida Console'
        self.FONTSCALE = 9
        self.ICON = self.DIR + '\\favicon.ico'
        self.CFG = self.DIR + '\\config\\'
        self.W = self.w = width  # w and h are current width and height; W and H are original
        self.H = self.h = height
        self.framerate = 60

        self.fullscreen = False
        self.alt_tabbed = False

        self.root = tk.Tk()
        self.root.title('Channeller')
        self.root.iconbitmap(self.ICON)
        self.root.geometry('%sx%s' % (self.W, self.H))
        self.root.configure(background=bg, **kwargs)
        self.root.focus_force()

        self.old_window_pos = self.root.winfo_x(), self.root.winfo_y()
        self.elements = []

        self.running = True

    def update_size(self):
        self.w = self.root.winfo_width()
        self.h = self.root.winfo_height()

    def alt_tab(self, *args):
        global alt_tabbed, fullscreen
        if fullscreen:
            self.toggle_fullscreen()
            alt_tabbed = True

    def toggle_fullscreen(self, *args):
        if not self.fullscreen:
            self.old_window_pos = self.root.winfo_x(), self.root.winfo_y()
            self.root.geometry('{}x{}+0+0'.format(self.root.winfo_screenwidth(), self.root.winfo_screenheight()))
            self.root.overrideredirect(1)  # borderless
            self.fullscreen = True
        elif self.alt_tabbed:
            self.root.overrideredirect(0)
            self.alt_tabbed = False
        else:
            self.root.geometry('{}x{}+{}+{}'.format(self.W, self.H, *self.old_window_pos))
            self.root.overrideredirect(0)
            self.root.focus_force()
            self.fullscreen = False

    def draw_elements(self):
        for elem in self.elements:
            elem.draw()

    def track(self, *elems):
        self.elements += elems

    def quit(self):
        self.running = False
        self.root.quit()

    def run(self):
        try:
            while self.running:
                self.update_size()
                self.draw_elements()
                self.root.update()
                self.root.update_idletasks()
                sleep(1/self.framerate)
        except (KeyboardInterrupt, SystemExit, tk.TclError) as e:
            print('Application destroyed: %s' % e)
            self.quit()
