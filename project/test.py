import sys
sys.path.append('..')
from common.core import *
from common.audio import *
from common.mixer import *
from common.wavegen import *
from common.wavesrc import *
from common.gfxutil import *
from common.vecutil import *
from project.graphics import *

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.clock import Clock as kivyClock

from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.stacklayout import StackLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

import numpy as np

class SongData(object):
    def __init__(self):
        super(SongData, self).__init__()
        self.timestamps = 0

    def read_data(self, filepath):
        w = np.array((Window.width, Window.height))
        with open(filepath) as f:
            lines = f.read().splitlines()
            tokens = [l.split(" ") for l in lines]
            self.timestamps = [
                [
                    float(t[0]),
                    np.array((float(t[1].split(",")[0]),
                        float(t[1].split(",")[1])))*w,
                    float(t[2]),
                    float(t[3])
                ] for t in tokens
            ]

class BeatMatchDisplay(InstructionGroup):
    def __init__(self, gem_data):
        super(BeatMatchDisplay, self).__init__()

        self.objects = AnimGroup()
        self.add(self.objects)

        self.gems = list()
        self.gem_data = gem_data
        self.latest_gem_idx = 0

        self.playing = False

        self.time = 0
        self.on_update(0)

    def toggle(self):
        self.playing = not self.playing

    def on_update(self, dt):
        self.time += dt
        if self.latest_gem_idx >= len(self.gem_data.timestamps):
            return
        gem_candidate = self.gem_data.timestamps[self.latest_gem_idx]
        if gem_candidate[0] - self.time < 5:
            self.gems.append(GemDisplay(self.time, *gem_candidate))
            self.objects.add(self.gems[-1])
            self.latest_gem_idx += 1

        if self.playing:
            self.objects.on_update()

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
        pass

    # needed to update audio
    def on_update(self):
        self.audio.on_update()

            
class Game(BaseWidget) :
    def __init__(self, game_over_cb):
        super(Game, self).__init__()

        self.objects = AnimGroup()

        self.player = PlayerDisplay()
        self.objects.add(self.player)

        self.song_data = SongData()
        self.song_data.read_data("./new.txt")
        self.gems = BeatMatchDisplay(self.song_data)
        self.objects.add(self.gems)

        self.camera = Camera(self.objects)
        self.canvas.add(self.camera)

        AUDIO_PATH = ["./UptownFunkBG.wav", "./UptownFunkSolo.wav"]
        self.audio_ctrl = AudioController(AUDIO_PATH)

        self.time = 0
        self.playing = False
        self.gem_idx = 0

        self.game_over_cb = game_over_cb
        self.score = 0

        # debugging
        self.label = topleft_label()
        self.add_widget(self.label)

    def toggle(self):
        self.playing = not self.playing

    def on_touch_down(self, touch):
        self.camera.add_trauma()
        ray = self.player.shoot()

        for gem in self.gems.gems:
           d = dist_from_ray(*ray, gem.pos)
           if d != False and d < 50. and abs(self.time-gem.hit_time) < 0.2:
               gem.on_hit()
               self.gem_idx += 1
               self.audio_ctrl.set_mute(False)


    def on_key_down(self, keycode, modifiers):
        # play / pause toggle
        if keycode[1] == 'p':
            self.audio_ctrl.toggle()
            self.gems.toggle()
            self.toggle()

        movement = lookup(keycode[1], 'wasd',
                ((0.,1.), (-1.,0.), (0.,-1.), (1.,0.)))
        if movement is not None:
            self.player.add_lvel(np.array(movement))

    def on_key_up(self, keycode):
        movement = lookup(keycode[1], 'wasd',
                ((0.,-1.), (1.,0.), (0.,1.), (-1.,0.)))
        if movement is not None:
            self.player.add_lvel(np.array(movement))

    def on_update(self):
        dt = kivyClock.frametime

        self.label.text = str(self.time)

        if self.playing:
            self.time += dt
            if self.time > self.gems.gems[self.gem_idx].hit_time + 0.2:
                self.gems.gems[self.gem_idx].on_pass()
                self.gem_idx += 1
                self.audio_ctrl.set_mute(True)

            #for i in range(len(self.gems.gems)):
            #    if np.linalg.norm(
            #            self.gems.gems[i].pos - self.player.pos) < 100:
            #        self.gems.gems[i].on_pass()
            #        self.gems.gems.remove(i)
            #        self.audio_ctrl.set_mute(True)

            self.player.look_at(Window.mouse_pos)
            self.audio_ctrl.on_update()
            self.objects.on_update()
            self.camera.on_update(dt)

        #if self.time >= 5:
        #    self.playing = False
        #    self.game_over_cb(self.score)


class Menu(BaseWidget):
    def __init__(self, start_cb):
        super(Menu, self).__init__()

        self.start_btn = Button(
                text="START",
                color=(1.00, .996, .463, 0.7),
                font_name="./fonts/SourceCodePro-Semibold.ttf",
                font_size=60,
                background_color=(.137, .047, .447, 1.0),
                pos=(Window.width/2-200, Window.height/2-50),
                size=(400, 100))
        self.start_btn.bind(on_press=start_cb)
        self.add_widget(self.start_btn)

class ScoreScreen(BaseWidget):
    def __init__(self, score, start_cb):
        super(ScoreScreen, self).__init__()
        self.label = Label(
                text="GAME OVER\nFinal Score: {}".format(score),
                color=(1.00, .996, .463, 0.7),
                font_name="./fonts/SourceCodePro-Semibold.ttf",
                font_size=36,
                halign='center',
                valign='center',
                pos=(Window.width/2-50, Window.height/2+100))

        self.start_btn = Button(
                text="PLAY AGAIN",
                color=(1.00, .996, .463, 0.7),
                font_name="./fonts/SourceCodePro-Semibold.ttf",
                font_size=60,
                background_color=(.137, .047, .447, 1.0),
                pos=(Window.width/2-200, Window.height/2-150),
                size=(400, 100))
        self.start_btn.bind(on_press=start_cb)

        self.add_widget(self.label)
        self.add_widget(self.start_btn)

class MainWidget(BaseWidget):
    def __init__(self):
        super(MainWidget, self).__init__()
        self.initialize()

    def initialize(self):
        self.state = Menu(self.start_game)
        self.add_widget(self.state)

    def start_game(self, inst):
        self.remove_widget(self.state)
        self.state = Game(self.game_over)
        self.add_widget(self.state)

    def game_over(self, score):
        self.remove_widget(self.state)
        self.state = ScoreScreen(score, self.start_game)
        self.add_widget(self.state)

run(MainWidget)
