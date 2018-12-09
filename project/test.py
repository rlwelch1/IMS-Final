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
from collections import deque

def parse_file(filepath):
    w = np.array((Window.width, Window.height))
    with open(filepath) as f:
        lines = f.read().splitlines()
        tokens = [l.split(" ") for l in lines]
        return [
            [
                float(t[0]),                          # timestampe
                np.array((float(t[1].split(",")[0]),
                    float(t[1].split(",")[1])))*w,    # position
                float(t[2]),                          # radius
                float(t[3])                           # anticipation
            ] for t in tokens
        ]

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

    # needed to update audio
    def on_update(self):
        self.audio.on_update()

            
class Game(BaseWidget) :
    def __init__(self, game_over_cb):
        super(Game, self).__init__()
        # AUDIO
        AUDIO_PATH = ["./UptownFunkBG.wav", "./UptownFunkSolo.wav"]
        self.audio_ctrl = AudioController(AUDIO_PATH)

        # GRAPHICS
        self.objects = AnimGroup()

        self.player = PlayerDisplay()
        self.objects.add(self.player)

        self.gem_data = deque(parse_file("./new.txt"))
        self.rendered_gems = deque()

        self.ray = None

        self.camera = Camera(self.objects)
        self.canvas.add(self.camera)

        # GAME STATE
        self.score = 0
        self.time = 0
        self.playing = False

        self.game_over_cb = game_over_cb
        self.game_over_countdown = 5
        self.game_done = False

        # debugging
        self.label = topleft_label()
        self.add_widget(self.label)

    def toggle(self):
        self.playing = not self.playing

    def on_touch_down(self, touch):
        self.camera.add_trauma()
        self.ray = self.player.shoot()

    def on_key_down(self, keycode, modifiers):
        # play / pause toggle
        if keycode[1] == 'p':
            self.toggle()
            self.audio_ctrl.toggle()

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
        self.label.text = str(self.time)
        if not self.playing:
            return

        dt = kivyClock.frametime
        self.time += dt

        # Update game state
        self.player.look_at(Window.mouse_pos)
        self.camera.on_update(dt)
        self.audio_ctrl.on_update()
        self.objects.on_update()

        # Check game over state
        if self.game_done:
            self.game_over_countdown -= dt
            if self.game_over_countdown < 0:
                self.game_over_cb(self.score)
                return
        elif len(self.gem_data) == 0 and len(self.rendered_gems) == 0:
            self.game_done = True
            return

        # Render new gems
        if len(self.gem_data) > 0 and self.gem_data[0][0] - self.time <= 5:
            new_gem = GemDisplay(self.time, *self.gem_data.popleft())
            self.rendered_gems.append(new_gem)
            self.objects.add(new_gem)

        # Check hit gems
        if self.ray != None and len(self.rendered_gems) > 0:
            d = dist_from_ray(*self.ray, self.rendered_gems[0].pos)
            if d != False and d < 50. \
                    and abs(self.time-self.rendered_gems[0].hit_time) < 0.2:
                hit_gem = self.rendered_gems.popleft()
                hit_gem.on_hit()
                self.audio_ctrl.set_mute(False)

        # Check passed gems
        if len(self.rendered_gems) > 0:
            if self.time - self.rendered_gems[0].hit_time > 0.2:
                passed_gem = self.rendered_gems.popleft()
                passed_gem.on_pass()
                self.audio_ctrl.set_mute(True)


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
