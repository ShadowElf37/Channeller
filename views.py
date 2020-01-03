import audio
import graphics
import cues

def hms(sec):
    sec = int(sec)
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    return f'{h:02d}:{m:02d}:{s:02d}'

def hmsm(sec, decimals=1):
    ms = round(sec - int(sec), decimals)
    return hms(sec) + '.' + str(int(ms*10**decimals))[-decimals:]


class ChannelView:
    FG_1 = '#07F'
    FG_2 = '#FC0'
    FG_3 = '#2F0'
    BG = '#111'
    BUTTONBG = '#aaa'
    SPACING = 0.205

    @property
    def stereo(self):
        return 'STEREO' if self.channel._channel_count > 1 else 'MONO'

    @property
    def gain(self):
        return str(self.channel.gain + self.current.gain)

    @property
    def compression(self):
        return 'ON' if self.channel.compression else 'OFF'

    @property
    def current(self):
        return self.channel.current or audio.Track(None)

    @property
    def elapsed(self):
        return hmsm(self.current.play_time / 1000)

    @property
    def end(self):
        return hms(self.current.length)

    @property
    def paused(self):
        return 'PAUSED' if self.current.paused else ''

    @property
    def next(self):
        if t := self.channel.get_next():
            return t.name
        return 'None'

    @property
    def prev(self):
        if t := self.channel.get_prev():
            return t.name
        return 'None'

    def __init__(self, app, channel: audio.Channel, y_off=0):
        self.app = app
        self.channel = channel
        self.channel.update()
        self.color = channel.color
        y_off *= self.SPACING
        self.y = y_off
        self.scroll_y = 0

        # DIVS
        self.channel_view = graphics.Canvas(app, 0.7, 0.2, 0.1, 0.0 + y_off, bg=self.BG, border_width=1,
                                            border_color=self.color,
                                            xoffset=-1, yoffset=0 + self.y, hoffset=-2)
        self.presets = graphics.Div(app, 0.1, 0.2, 0.0, 0.0 + y_off, bg=self.BG, border_width=1,
                                    border_color=self.color)
        self.buttons = graphics.Div(app, 0.2, 0.2, 0.8, 0.0 + y_off, bg=self.BG, border_width=1,
                                    border_color=self.color)

        # PRESETS
        #self.compression_label = graphics.Label(app, '', y=0.01 + y_off, fg=self.FG_1, bg=self.BG)
        #self.compression_label.define_pre_label('COMP ')
        #self.gain_label = graphics.Label(app, '', y=0.06 + y_off, fg=self.FG_1, bg=self.BG)
        #self.gain_label.define_pre_label('GAIN ')
        self.mono_label = graphics.Label(app, '', y=0.11 + y_off, fg=self.FG_1, bg=self.BG)

        # TRACK NAME
        self.track_name_label = graphics.Label(app, '', x=0.1, y=0.002 + y_off, fontscale=1.3, fg=self.FG_2, bg=self.BG)

        # TIME
        self.elapsed_label = graphics.Label(app, '', x=0.12, y=0.16 + y_off, yoffset=-10, fontscale=0.9, fg=self.FG_2,
                                            bg=self.BG)
        self.total_label = graphics.Label(app, '', x=0.7, y=0.16 + y_off, yoffset=-10, fontscale=0.9, fg=self.FG_2,
                                          bg=self.BG)

        # NEXT PREV
        self.prev_label = graphics.Label(app, '', x=0.13, y=0.067 + y_off, fontscale=1, fg=self.FG_1, bg=self.BG)
        self.prev_label.define_pre_label('Prev: ')
        self.next_label = graphics.Label(app, '', x=0.45, y=0.067 + y_off, fontscale=1, fg=self.FG_1, bg=self.BG)
        self.next_label.define_pre_label('Next: ')

        # BAR
        self.timebar = graphics.ProgressBar(app, self.channel_view, x=0.18, y=0.8, w=0.65, h=0.1, xoffset=10,
                                            yoffset=-5,
                                            fill_color=self.color, border_color=self.color)

        # CHANNEL
        self.channel_label = graphics.RightAlignLabel(app, self.channel.name, x=0.817, y=0.005 + y_off, fontscale=1.5,
                                                      fg=self.color, bg=self.BG)

        # PAUSED
        self.paused_label = graphics.Label(app, '', x=0.7, y=0.065 + y_off, fontscale=1.3, fg='white', bg=self.BG)

        # BUTTONS
        LINE1Y = 0.03
        LINE2Y = 0.11
        CENTERX = 0.8875
        SIZE = 0.02

        self.pause_button = graphics.Button(app, SIZE, SIZE, CENTERX + 0.0, LINE1Y + y_off,
                                            img_name=app.IMG + 'play.png',
                                            img_scale=0.9, background=self.BUTTONBG, cmd=self.cmd_play)
        self.next_button = graphics.Button(app, SIZE, SIZE, CENTERX + 0.03, LINE1Y + y_off,
                                           img_name=app.IMG + 'next.png',
                                           background=self.BUTTONBG, cmd=self.cmd_next)
        self.last_button = graphics.Button(app, SIZE, SIZE, CENTERX + 0.06, LINE1Y + y_off,
                                           img_name=app.IMG + 'last.png',
                                           background=self.BUTTONBG, cmd=self.cmd_last)
        self.prev_button = graphics.Button(app, SIZE, SIZE, CENTERX - 0.03, LINE1Y + y_off,
                                           img_name=app.IMG + 'prev.png',
                                           background=self.BUTTONBG, cmd=self.cmd_back)
        self.first_button = graphics.Button(app, SIZE, SIZE, CENTERX - 0.06, LINE1Y + y_off,
                                            img_name=app.IMG + 'first.png',
                                            background=self.BUTTONBG, cmd=self.cmd_first)

        self.stop_button = graphics.Button(app, SIZE, SIZE, CENTERX, LINE2Y + y_off, img_name=app.IMG + 'stop.png',
                                           img_scale=0.8,
                                           background=self.BUTTONBG, cmd=self.cmd_stop)

        self.ch_gain_label = graphics.Label(app, 'CH GAIN', x=0.9275, y=0.15 + y_off, fontscale=0.6, fg=self.FG_1,
                                            bg=self.BG)
        self.tr_gain_label = graphics.Label(app, 'TR GAIN', x=0.82, y=0.15 + y_off, fontscale=0.6, fg=self.FG_1,
                                            bg=self.BG)

        self.ch_gain_inc = graphics.Incrementor(app, min=-99.9, max=10, step=0.5, x=0.92, y=0.111 + y_off, w=5,
                                                yoffset=0,
                                                bg='#000', fg=self.color, buttonbg=self.BUTTONBG, fontscale=1)
        self.tr_gain_inc = graphics.Incrementor(app, min=-99.9, max=10, step=0.5, x=0.8125, y=0.111 + y_off, w=5,
                                                yoffset=0,
                                                bg='#000', fg=self.color, buttonbg=self.BUTTONBG, fontscale=1)

        self.parts = (
            self.channel_view, self.presets, self.buttons,
            self.mono_label,  # Removed gain and comp labels
            self.track_name_label, self.elapsed_label, self.total_label,
            self.next_label, self.prev_label, self.channel_label, self.paused_label, # no timebar
            self.pause_button, self.next_button, self.last_button, self.prev_button, self.first_button,
            self.stop_button, self.ch_gain_label, self.tr_gain_label, self.ch_gain_inc, self.tr_gain_inc
        )

        app.track(self)
        self.update_labels()
        self.update_times()
        self.ch_gain_inc.set(str(self.channel.gain))
        self.tr_gain_inc.set(str(self.current.gain))

    def cmd_next(self):
        self.channel.next()

    def cmd_back(self):
        self.channel.back()

    def cmd_first(self):
        self.channel.first()

    def cmd_last(self):
        self.channel.last()

    def cmd_play(self):
        if not self.current.playing:
            self.channel.play()
        elif self.current.paused:
            self.current.resume()
        else:
            self.current.pause()

    def cmd_stop(self):
        self.channel.stop()

    def update_labels(self):
        #self.compression_label.write(self.compression)
        #self.gain_label.write(self.gain)
        self.mono_label.write(self.stereo)

        self.track_name_label.write('%s - %s' % (self.current.name, self.channel.index))
        self.prev_label.write(self.prev)
        self.next_label.write(self.next)

        self.paused_label.write(self.paused)

    def update_times(self):
        self.timebar.percent = 0
        if self.current.length:
            self.timebar.percent = self.current.play_time / (self.current.length * 1000)
        self.elapsed_label.write(self.elapsed)
        self.total_label.write(self.end)

        if not self.current.playing or self.current.paused:
            self.pause_button.set_img(self.app.IMG + 'play.png')
        else:
            self.pause_button.set_img(self.app.IMG + 'pause.png')

    def update_gains(self):
        try:
            g = self.ch_gain_inc.get()
            self.channel.gain = float(g)
        except (ValueError,):
            pass
        try:
            g = self.tr_gain_inc.get()
            self.current.gain = float(g)
        except (ValueError,):
            pass

    def shifty(self, y):
        self.scroll_y += y
        for part in self.parts:
            part.yoffset += y
            part.need_update = True

    def reset_shifty(self):
        for part in self.parts:
            part.yoffset -= self.scroll_y
            part.need_update = True
        self.scroll_y = 0

    def draw(self):
        self.update_times()
        self.update_gains()
        self.update_labels()


class CueViewer:
    FG_1 = '#eee'
    FG_2 = '#0c0'
    FG_3 = '#dc0'
    BG = '#3f3f3f'
    BD = '#aaa'
    BBG_1 = '#f33'
    ABBG_1 = '#f88'
    BBG_2 = '#048'
    ABBG_2 = '#688'

    def __init__(self, app, cue_manager):
        self.cm: cues.CueManager = cue_manager
        self.app = app

        self.box = graphics.Div(app, w=0.8, h=0.1, x=0.1, y=0.9, bg=self.BG, border_color=self.BD, border_width=1, yoffset=1, hoffset=2)

        self.prev_label = graphics.Label(app, x=0.105, y=0.915, fg=self.FG_1, bg=self.BG, fontscale=0.8)
        self.prev_label.define_pre_label('Last: ')
        self.next_label = graphics.Label(app, x=0.105, y=0.955, fg=self.FG_1, bg=self.BG, fontscale=0.8)
        self.next_label.define_pre_label('Next: ')

        self.current_label = graphics.Label(app, x=0.35, y=0.905, yoffset=1, fg=self.FG_2, bg=self.BG, fontscale=1.4)
        self.current_label.define_pre_label('Now: ')
        self.next_cmd = graphics.Label(app, x=0.35, y=0.945, yoffset=7, fg=self.FG_3, bg=self.BG, fontscale=0.7, h=0.01, anchor='n')


        self.prev_button = graphics.Button(app, w=0.02, h=0.06, x=0.065, y=0.92, img_name=self.app.IMG + 'first.png', background=self.BBG_1, activebackground=self.ABBG_1, cmd=self.cm.back)
        self.next_button = graphics.Button(app, w=0.02, h=0.06, x=0.915, y=0.92, xoffset=-4, img_name=self.app.IMG + 'last.png', background=self.BBG_1, activebackground=self.ABBG_1, cmd=self.cm.next)

        self.stop_all_button = graphics.Button(app, w=0.02, h=0.06, x=0.029, y=0.92, img_name=self.app.IMG + 'stop2.png', background=self.BBG_2, activebackground=self.ABBG_2, cmd=self.cm.m.stop_all,
                                               img_scale=0.98)
        self.go_button = graphics.Button(app, w=0.02, h=0.06, x=0.95, y=0.92, xoffset=-4, img_name=self.app.IMG + 'go.png', background=self.BBG_2, activebackground=self.ABBG_2, cmd=self.cm.do,
                                         img_scale=1.05)

        app.track(self)

    def draw(self):
        i = self.cm.i
        self.prev_label.write(self.cm.get(i - 1).desc[:25])
        self.next_label.write(self.cm.get(i + 1).desc[:25])
        self.current_label.write('Cue {} - '.format(i+1) + self.cm.get(i).desc[:31])
        self.next_cmd.write(self.cm.get(i).code)
