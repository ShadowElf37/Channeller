import tkinter as tk
from PIL import Image, ImageTk, ImageTransform, ImageColor
import os
from extras import Path, sizemb
from time import sleep
from copy import deepcopy
import traceback

def in_box(x, y, x1, y1, x2, y2):
    return x2 >= x >= x1 and y2 >= y >= y1


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
        self.need_update = True
        app.track(self)

    def check_resize(self):
        return self.app.check_resize()

    def register(self, e):
        self.tk_elements.append(e)
        return e

    def draw(self):
        if self.check_resize() or self.need_update:  # Check for updates before we waste cycles on this
            self.need_update = False
            for elem in self.tk_elements:
                elem.configure(width=int(self.w * self.app.w + self.woffset),
                               height=int(self.h * self.app.h + self.hoffset))
                elem.place_forget()
                elem.place(x=int(self.x * self.app.w + self.xoffset),
                           y=int(self.y * self.app.h + self.yoffset))
            return True
        return False


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

    def draw(self):
        super().draw()
        self.canvas.update()
        self.canvas.update_idletasks()

class Div(Element):
    # This class is not capable of aligning things within itself because I'm too lazy to implement that – it's literally just a box
    def __init__(self, app, w=1.0, h=1.0, x=0, y=0, bg='black', border_color='black', border_width=0, xoffset=0, yoffset=0, woffset=0, hoffset=0, **kwargs):
        super().__init__(app, w, h, x, y, xoffset, yoffset, woffset, hoffset)
        self.bg = bg
        self.bdc = border_color
        self.bdw = border_width

        self.box = self.register(tk.Frame(self.root, width=w*app.w, height=h*app.h, background=bg, highlightthickness=self.bdw, highlightbackground=self.bdc, **kwargs))

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

        self.label = self.register(tk.Label(self.root, padx=0, pady=0, textvar=self.text, width=int(w*app.w), height=int(h*app.h), background=bg, fg=fg, highlightthickness=self.bdw, highlightbackground=self.bdc, font=(self.app.FONT, int(self.app.FONTSCALE*fontscale)), anchor=anchor, **kwargs))

    @property
    def fontsize(self):
        return int(self.app.FONTSCALE * self.fontscale * self.app.w / self.app.W)

    def draw(self):
        if len(self.read()) == 0:
            self.label.place_forget()
        if super().draw():
            for elem in self.tk_elements:
                elem.configure(font=(self.app.FONT, self.fontsize))

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
        if len(self.read()) == 0:
            self.label.place_forget()
        # Some manual scaling was required to keep them aligned; the longer the text, the further off to the left it was
        self.x = self.X - (((self.fontsize*0.8)*(len(self.read())+2)) / self.app.w)
        super().draw()


class Button(Element):
    def __init__(self, app, w, h, x, y, text='', img_name=None, img_scale=0.85, cmd=lambda: None, bg='black', fg='white', bdc='white', xoffset=0, yoffset=0, woffset=0, hoffset=0, square=True, **kwargs):
        super().__init__(app, w, h, x, y, xoffset, yoffset, woffset, hoffset)
        self.bdc = bdc
        self.fg = fg
        self.bg = bg
        self.square = square
        self.text = tk.StringVar()
        self.text.set(text)
        self.img: Image.Image = None
        self.img_path = img_name
        self.img_scale = img_scale
        self.img_cache = {}
        self.img_update = False
        if img_name:
            self.img = Image.open(self.img_path).convert('RGBA')  # gotta do RGBA explicitly for some reason or else transparency will fail  # self.app.DIR+'\\'+
            self.img_cache[self.img_path] = deepcopy(self.img)
            # Resize img to fit in button
            self.img.thumbnail(size=(int(w*app.w*self.img_scale + woffset), int(h*app.h*self.img_scale if not square else w*app.w*self.img_scale + hoffset)), resample=Image.ANTIALIAS)
            self.tkimg = ImageTk.PhotoImage(self.img)
            kwargs['image'] = self.tkimg
        self.cmd = cmd
        self.button = self.register(tk.Button(self.root, textvar=self.text, command=cmd, width=w*app.w, height=h*app.h if not self.square else w*app.w, relief='raised', compound='center', **kwargs))

    def set_img(self, path):
        self.img_path = path
        self.img_update = True

    def invoke(self):
        return self.button.invoke()

    def draw(self):
        if super().draw() or self.img_update:
            self.img_update = False
            if img := self.img_cache.get(self.img_path):
                self.img = deepcopy(img)
            else:
                self.img = Image.open(self.img_path).convert('RGBA')
            self.img.thumbnail(size=(int(self.img_scale*self.w * self.app.w + self.woffset), int(self.img_scale*self.h * self.app.h if not self.square else self.w * self.app.w * self.img_scale + self.hoffset)), resample=Image.ANTIALIAS)
            self.tkimg = ImageTk.PhotoImage(self.img)
            self.button.configure(image=self.tkimg)
            self.button.configure(height=int(self.h * self.app.h) if not self.square else int(self.w * self.app.w))  # overloads draw's window-shaped rectangle


class Incrementor(Element):
    def __init__(self, app, step=1, min=0, max=100, w=0, x=0, y=0, bg='white', fg='black', border_color='black', border_width=0,
                 xoffset=1, yoffset=1, woffset=0, hoffset=0, fontscale=1.0, buttonbg='white', **kwargs):
        super().__init__(app, w, 0, x, y, xoffset, yoffset, woffset, hoffset)
        self.bg = bg
        self.fg = fg
        self.bdc = border_color
        self.bdw = border_width
        self.pre = ''
        self.fontscale = fontscale
        self.step = step
        self.min = min
        self.max = max
        self.buttonbg = buttonbg

        self.RELIEF = 'raised'
        self.inc = self.register(tk.Spinbox(self.root, from_=min, to=max, increment=step, width=int(w), buttonbackground=buttonbg, buttonuprelief=self.RELIEF, buttondownrelief=self.RELIEF, highlightthickness=0, relief=self.RELIEF, bg=bg, fg=fg, bd=self.bdw, font=(self.app.FONT, self.fontsize), **kwargs))

    @property
    def fontsize(self):
        return int(self.app.FONTSCALE * self.fontscale * self.app.w / self.app.W)

    def set(self, val):
        self.inc.delete(0, 'end')
        self.inc.insert(0, str(val))
    def get(self):
        return self.inc.get()

    def draw(self):
        # Same as parent but without height because you can't specify height for this
        if self.check_resize() or self.need_update:  # Check for updates before we waste cycles on this
            self.need_update = False
            for elem in self.tk_elements:
                elem.configure(width=int(self.w), font=(self.app.FONT, self.fontsize), buttonuprelief=self.RELIEF, buttondownrelief=self.RELIEF )
                elem.place_forget()
                elem.place(x=int(self.x * self.app.w + self.xoffset),
                           y=int(self.y * self.app.h + self.yoffset))
            return True
        return False

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

        # Executive decision: these will be created in draw
        self.outer = None
        self.inner = None

    def draw(self):
        self.tk_canvas.delete(self.outer)
        self.tk_canvas.delete(self.inner)
        self.coords = self.x * self.canvas.w*self.app.w + self.xoffset - self.woffset - 2,\
                 self.y * self.canvas.h*self.app.h + self.yoffset - self.hoffset,\
                 self.x * self.canvas.w*self.app.w + self.w * self.canvas.w*self.app.w + self.xoffset + self.woffset,\
                 self.y * self.canvas.h*self.app.h + self.h * self.canvas.h*self.app.h + self.yoffset + self.hoffset
        self.outer = self.tk_canvas.create_rectangle(*self.coords, outline=self.bdc)
        self.inner = self.tk_canvas.create_rectangle(self.coords[0] + 1,
                                                     self.coords[1] + 1,
                                                     self.x * self.canvas.w * self.app.w + self.xoffset + (self.w * self.canvas.w * self.app.w  + self.woffset)*self.percent,
                                                     self.coords[3] - 1,
                                                     outline=self.bg, fill=self.fc)


class App:
    def __init__(self, width, height, bg='black', fps=60, **kwargs):
        self.DIR = os.getcwd()
        self.FONT = 'Lucida Console'
        self.FONTSCALE = 9
        self.ICON = Path(self.DIR, 'images', 'favicon.ico')
        self.CFG = Path(self.DIR, 'config')
        self.IMG = Path(self.DIR, 'images')
        self.W = self.w = self.ow = width  # w and h are current width and height; W and H are original
        self.H = self.h = self.oh = height
        self.framerate = fps

        self.fullscreen = False
        self.alt_tabbed = False

        self.root = tk.Tk()
        self.root.title('Channeller')
        self.root.iconbitmap(self.ICON)
        self.root.geometry('%sx%s' % (self.W, self.H))
        self.root.configure(background=bg, **kwargs)
        self.root.focus_force()

        self.on_resize = lambda: None

        # self.root.wm_attributes('-alpha', 0.9)

        self.old_window_pos = self.root.winfo_x(), self.root.winfo_y()
        self.elements = []

        self.running = True

    def bind(self, key, f):
        self.root.bind('<%s>'%key, f)
    def bind_all(self, key, f):
        self.root.bind_all('<%s>'%key, f)

    def resize(self, w, h):
        self.root.geometry(f'{w}x{h}')
        self.update_size()

    def check_resize(self):
        return self.ow != self.w or self.oh != self.h
    def update_size(self):
        self.w = self.root.winfo_width()
        self.h = self.root.winfo_height()

    def alt_tab(self, *args):
        if self.fullscreen:
            self.toggle_fullscreen()
            self.alt_tabbed = True

    def toggle_fullscreen(self, *args):
        if not self.fullscreen:
            self.old_window_pos = self.root.winfo_x(), self.root.winfo_y()
            self.root.geometry('{}x{}+0+0'.format(self.root.winfo_screenwidth(), self.root.winfo_screenheight()))
            self.root.overrideredirect(1)  # borderless
            self.fullscreen = True
        elif self.alt_tabbed:
            self.root.geometry('{}x{}+{}+{}'.format(self.W, self.H, *self.old_window_pos))
            self.root.overrideredirect(0)
            self.root.focus()
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
        while self.running:
            try:
                self.update_size()
                if self.check_resize():
                    self.on_resize()
                self.draw_elements()
                self.root.update()
                self.root.update_idletasks()
                self.ow = self.w
                self.oh = self.h
                sleep(1/self.framerate)
            except (KeyboardInterrupt, SystemExit, tk.TclError) as e:
                print('Application destroyed – %s' % e)
                self.quit()
            except:
                traceback.print_exc()
