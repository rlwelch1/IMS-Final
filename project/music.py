#pset6.py


import sys
sys.path.append('..')
from common.core import *
from common.audio import *
from common.mixer import *
from common.wavegen import *
from common.wavesrc import *
from common.gfxutil import *

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.clock import Clock as kivyClock

import random
import numpy as np
import bisect


class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()

        gem_data = SongData()
        gem_data.read_data("./beats.txt", "./tempo.txt")

        self.display = BeatMatchDisplay(gem_data)
        self.canvas.add(self.display)

        AUDIO_PATH = ["./UptownFunkBG.wav", "./UptownFunkSolo.wav"]
        self.audio_ctrl = AudioController(AUDIO_PATH)

        self.player = Player(gem_data, self.display, self.audio_ctrl)

        # debugging
        self.label = topleft_label()
        self.add_widget(self.label)

    def on_key_down(self, keycode, modifiers):
        # play / pause toggle
        if keycode[1] == 'p':
            self.player.toggle()

        # button down
        button_idx = lookup(keycode[1], 'cvbnm', (0,1,2,3,4))
        if button_idx != None:
            self.player.on_button_down(button_idx)

        if keycode[1] == 'spacebar':
            self.player.on_button_down(2)

    def on_key_up(self, keycode):
        # button up
        button_idx = lookup(keycode[1], 'cvbnm', (0,1,2,3,4))
        if button_idx != None:
            self.player.on_button_up(button_idx)

        if keycode[1] == 'spacebar':
            self.player.on_button_up(2)

    def on_update(self) :
        self.player.on_update()
        self.label.text = "Time: {0:.1f}\n".format(self.player.time)
        self.label.text += "Score: {}\n".format(self.player.score)
        self.label.text += "Combo: {}\n".format(self.player.combo)


# creates the Audio driver
# creates a song and loads it with solo and bg audio tracks
# creates snippets for audio sound fx
class AudioController(object):
    def __init__(self, song_path):
        super(AudioController, self).__init__()
        self.audio = Audio(2)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)

        self.bg = WaveGenerator(WaveFile(song_path[0]))
        self.mixer.add(self.bg)
        self.solo = WaveGenerator(WaveFile(song_path[1]))
        self.mixer.add(self.solo)

        self.bg.pause()
        self.solo.pause()

    # start / stop the song
    def toggle(self):
        self.bg.play_toggle()
        self.solo.play_toggle()

    # mute / unmute the solo track
    def set_mute(self, mute):
        if mute:
            self.solo.set_gain(0.0)
        else:
            self.solo.set_gain(1.0)

    # play a sound-fx (miss sound)
    def play_sfx(self):
        self.miss = WaveGenerator(WaveFile("./MissSFX.wav"))
        self.mixer.add(self.miss)

    # needed to update audio
    def on_update(self):
        self.audio.on_update()


# holds data for gems and barlines.
class SongData(object):
    def __init__(self):
        super(SongData, self).__init__()
        self.lanes = None

    # read the gems and song data. You may want to add a secondary filepath
    # argument if your barline data is stored in a different txt file.
    def read_data(self, filepath, tempopath):
        with open(filepath) as f:
            lines = f.read().splitlines()
            # Parsing the gem file
            timestamps = [
                [
                    float(l.split("\t")[0]),
                    [int(g) for g in l.split("\t")[-1].split(",")]
                ] for l in lines
            ]
            self.lanes = [
                [
                    t[0] for t in filter(lambda t: l in t[1], timestamps)
                ] for l in range(5)
            ]
        with open(tempopath) as f:
            lines = f.read().splitlines()
            self.start = float(lines[0].split("\t")[0])
            beat = float(lines[1].split("\t")[0])
            self.bar_len = (beat - self.start) * 2


PPS = 400 # pixels per second

# display for a single gem at a position with a color (if desired)
class GemDisplay(InstructionGroup):
    def __init__(self, pos, color, segments):
        super(GemDisplay, self).__init__()

        self.color = Color(rgb=color)
        self.color.a = 0.3
        self.add(self.color)

        self.circle = CEllipse(cpos = pos, size = (30, 30), segments = segments)
        self.add(self.circle)

    # change to display this gem being hit
    def on_hit(self):
        self.color.a = 1.0

    # change to display a passed gem
    def on_pass(self):
        self.color.a = 0.1

    # useful if gem is to animate
    def on_update(self, dt):
        pos = (self.circle.cpos[0], self.circle.cpos[1] - PPS * dt)
        self.circle.cpos = pos
        return pos[1] > 0


# Displays one button on the nowbar
class ButtonDisplay(InstructionGroup):
    def __init__(self, pos, color):
        super(ButtonDisplay, self).__init__()

        self.color = Color(rgb=color)
        self.add(self.color)

        self.circle = CEllipse(cpos = pos, size = (30, 30), segments = 4)
        self.add(self.circle)

    # displays when button is down (and if it hit a gem)
    def on_down(self, hit):
        if hit:
            self.color.a = 1
        else:
            self.color.a = 0.3

    # back to normal state
    def on_up(self):
        self.color.a = 0.7

    def on_update(self, dt):
        pass

# Displays one button on the nowbar
class BarlineDisplay(InstructionGroup):
    def __init__(self, ypos):
        super(BarlineDisplay, self).__init__()

        self.color = Color(1, 1, 1, 0.5)
        self.add(self.color)

        self.rect = CRectangle(
                cpos = (Window.width/2, ypos),
                size = (Window.width, 5))
        self.add(self.rect)

    # useful if gem is to animate
    def on_update(self, dt):
        pos = (self.rect.cpos[0], self.rect.cpos[1] - PPS * dt)
        self.rect.cpos = pos
        return pos[1] > 0


# Displays one button on the nowbar
class NowbarDisplay(InstructionGroup):
    def __init__(self, ypos):
        super(NowbarDisplay, self).__init__()

        self.color = Color(1, 1, 1, 0.5)
        self.add(self.color)

        self.rect = CRectangle(
                cpos = (Window.width/2, ypos),
                size = (Window.width, 5))
        self.add(self.rect)

    # displays when button is down (and if it hit a gem)
    def on_down(self, hit):
        self.rect.set_csize((Window.width, 10))
        if hit:
            self.color.rgba = (1, 1, 1, 0.7)
        else:
            self.color.rgba = (1, 1, 1, 0.3)

    # back to normal state
    def on_up(self):
        self.rect.set_csize((Window.width, 5))
        self.color.rgba = (1, 1, 1, 0.5)

    def on_update(self, dt):
        pass

# Displays and controls all game elements: Nowbar, Buttons, BarLines, Gems.
class BeatMatchDisplay(InstructionGroup):
    def __init__(self, gem_data):
        super(BeatMatchDisplay, self).__init__()

        self.animobj = AnimGroup()
        self.add(self.animobj)

        NOWBAR_Y = 100
        # Nowbar
        self.nowbar = NowbarDisplay(NOWBAR_Y)
        self.animobj.add(self.nowbar)

        # Buttons
        self.buttons = list()
        colors = [
                (0.98, 0.35, 0.13),
                (0.12, 0.43, 0.63),
                (0.98, 0.76, 0.13),
                (0.85, 0.12, 0.39),
                (0.61, 0.91, 0.13)
                ]
        for i in range(5):
            xpos = Window.width / 6 * (i+1)
            self.buttons.append(ButtonDisplay((xpos, NOWBAR_Y), colors[i]))
            self.animobj.add(self.buttons[-1])

        # Gems
        self.gem_data = gem_data
        self.gem_inst = list()
        for lane in range(len(gem_data.lanes)):
            self.gem_inst.append(list())
            for gem_time in gem_data.lanes[lane]:
                xpos = Window.width / 6 * (lane+1)
                ypos = NOWBAR_Y + gem_time * PPS
                gem = GemDisplay((xpos, ypos), colors[lane], 5+lane)
                self.gem_inst[lane].append(gem)
                self.animobj.add(gem)
        self.playing = False

        # Barlines
        self.barlines = list()
        for i in range(100):
            ypos = NOWBAR_Y + \
                    (self.gem_data.start + self.gem_data.bar_len*i) * PPS
            barline = BarlineDisplay(ypos)
            self.barlines.append(barline)
            self.animobj.add(barline)

    def toggle(self):
        self.playing = not self.playing
        
    # called by Player. Causes the right thing to happen
    def gem_hit(self, lane, gem_idx):
        self.gem_inst[lane][gem_idx].on_hit()

    # called by Player. Causes the right thing to happen
    def gem_pass(self, lane, gem_idx):
        self.gem_inst[lane][gem_idx].on_pass()

    # called by Player. Causes the right thing to happen
    def on_button_down(self, lane, hit):
        self.nowbar.on_down(hit)
        self.buttons[lane].on_down(hit)

    # called by Player. Causes the right thing to happen
    def on_button_up(self, lane):
        self.nowbar.on_up()
        self.buttons[lane].on_up()

    # call every frame to make gems and barlines flow down the screen
    def on_update(self):
        if self.playing:
            self.animobj.on_update()


# Handles game logic and keeps score.
# Controls the display and the audio
SLOP_MARGIN = 0.1
class Player(object):
    def __init__(self, gem_data, display, audio_ctrl):
        super(Player, self).__init__()
        self.gem_data = gem_data
        self.display = display
        self.audio_ctrl = audio_ctrl

        self.playing = False
        self.time = 0.0
        self.idx = [0, 0, 0, 0, 0]

        self.score = 0
        self.combo = 0

    def _get_multiplier(self):
        if self.combo < 10:
            return 1
        elif self.combo < 20:
            return 2
        elif self.combo < 30:
            return 3
        else:
            return 4

    def toggle(self):
        self.playing = not self.playing
        self.audio_ctrl.toggle()
        self.display.toggle()

    # called by MainWidget
    def on_button_down(self, lane):
        # corner case for no more gems in the given lane
        if len(self.gem_data.lanes[lane]) <= self.idx[lane]:
            self.display.on_button_down(lane, False)
            self.audio_ctrl.set_mute(True)
        # check if a gem was within the slop margin in the correct lane
        elif abs(self.time - self.gem_data.lanes[lane][self.idx[lane]]) < \
                SLOP_MARGIN:
            self.display.on_button_down(lane, True)
            self.display.gem_hit(lane, self.idx[lane])
            self.audio_ctrl.set_mute(False)
            self.idx[lane] += 1

            self.score += 50 * self._get_multiplier()
            self.combo += 1
        else:
            self.display.on_button_down(lane, False)
            self.audio_ctrl.set_mute(True)
            self.audio_ctrl.play_sfx()

            self.combo = 0

    # called by MainWidget
    def on_button_up(self, lane):
        self.display.on_button_up(lane)

    # needed to check if for pass gems (ie, went past the slop window)
    def on_update(self):
        if not self.playing:
            return

        self.time += kivyClock.frametime
        for l in range(5):
            if len(self.gem_data.lanes[l]) <= self.idx[l]:
                continue
            if self.time - self.gem_data.lanes[l][self.idx[l]] > \
                    SLOP_MARGIN:
                self.display.gem_pass(l, self.idx[l])
                self.audio_ctrl.set_mute(True)
                self.audio_ctrl.play_sfx()
                self.idx[l] += 1
                
                self.combo = 0

        self.display.on_update()
        self.audio_ctrl.on_update()

run(MainWidget)
