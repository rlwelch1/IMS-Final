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
        for gem_meta in gem_data.timestamps:
            self.gems.append(GemDisplay(*gem_meta))
            self.objects.add(self.gems[-1])

        self.playing = False

    def toggle(self):
        self.playing = not self.playing

    def on_update(self, dt):
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

            
class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()

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


    def on_touch_up(self, touch):
        pass

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


run(MainWidget)
