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
                float(t[0]),                          # hit_time
                float(t[1]),                          # kill_time
                np.array((float(t[2].split(",")[0]),
                    float(t[2].split(",")[1])))*w,    # position
                float(t[3]),                          # radius
                float(t[4]),                          # anticipation
                int(t[5])                           # color_idx
            ] for t in tokens
        ]

class AudioController(object):
    def __init__(self, audio, mixer, song_path):
        super(AudioController, self).__init__()
        self.audio = audio
        self.mixer = mixer
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
            self.bg.set_gain(0.6)
        else:
            self.solo.set_gain(1.0)
            self.bg.set_gain(0.0)

    # needed to update audio
    def on_update(self):
        self.audio.on_update()

            
class Game(BaseWidget) :
    def __init__(self, game_over_cb):
        super(Game, self).__init__()
        # AUDIO
        self.audio = Audio(2)
        self.mixer = Mixer()
        AUDIO_PATH = ["./AloneFilteredv3.wav", "./AloneStandard.wav"]
        self.audio_ctrl = AudioController(self.audio, self.mixer, AUDIO_PATH)

        # GRAPHICS
        self.objects = AnimGroup()

        self.player = PlayerDisplay()
        self.objects.add(self.player)

        self.gem_data = deque(parse_file("./LevelFinal.txt"))
        self.rendered_gems = deque()

        self.camera = Camera(self.objects)
        self.canvas.add(self.camera)

        # GAME STATE
        self.score = 0
        self.combo = 0
        self.time = 0.0
        self.playing = False
        self.healthbar = 10.0
        self.healthbar_sprite = HealthBar()
        self.objects.add(self.healthbar_sprite)

        self.game_over_cb = game_over_cb
        self.game_over_countdown = 5
        self.game_done = False

        # debugging
        self.label = topleft_label()
        self.add_widget(self.label)

        self.first = True

    def _get_multiplier(self):
        if self.combo < 5:
            return 1
        elif self.combo < 10:
            return 2
        elif self.combo < 15:
            return 3
        else:
            return 4

    def toggle(self):
        self.playing = not self.playing

    def on_touch_down(self, touch):
        if self.first:
            self.first = False
            self.toggle()
            self.audio_ctrl.toggle()
            return
        self.camera.add_trauma()
        self.player.shoot()

    def on_touch_up(self, touch):
        self.player.release()

    def on_key_down(self, keycode, modifiers):
        if self.game_done: # disable player controls if game over
            return
        
        # play / pause toggle
        if keycode[1] == 'p':
            self.first = False
            self.toggle()
            self.audio_ctrl.toggle()

        movement = lookup(keycode[1], 'wasd',
                ((0.,1.), (-1.,0.), (0.,-1.), (1.,0.)))
        if movement is not None:
            self.player.add_lvel(np.array(movement))

    def on_key_up(self, keycode):
        if self.game_done: # disable player controls if game over
            return

        movement = lookup(keycode[1], 'wasd',
                ((0.,-1.), (1.,0.), (0.,1.), (-1.,0.)))
        if movement is not None:
            self.player.add_lvel(np.array(movement))
            
    def apply_bullet_damage(self):
        self.healthbar = max(self.healthbar-1, 0)
        self.healthbar_sprite.set_health(self.healthbar)
        
    def spawn_bullets(self, pos):
        bul_speed = 50
        bullets = []
        for vel in [(bul_speed,bul_speed),(bul_speed,-bul_speed),(-bul_speed,-bul_speed),(-bul_speed,bul_speed)]:
            bullet = Bullet(pos, self.player_collision_check, self.apply_bullet_damage, vel)
            bullets.append(bullet)
            
        for bullet in bullets:
            self.objects.add(bullet)
            
    def player_collision_check(self, bullet_pos):
        x, y = self.player.get_pos()
        return (abs(bullet_pos[0] - x) < 20 and abs(bullet_pos[1] - y) < 20)

    def on_update(self):
        self.label.text = "Time: {:.1f}\nHealth: {}".format(
            self.time,
            "{:.0f}".format(
                self.healthbar
            ) if self.healthbar > 0 else "GAME OVER"
        )

        # Check paused state
        if not self.playing:
            return

        dt = kivyClock.frametime
        self.time += dt

        # Check laser usage
        if self.player.shooting:
            self.healthbar -= dt * 5
            self.healthbar_sprite.set_health(self.healthbar)

        # Render new gems
        if len(self.gem_data) > 0 and self.gem_data[0][0] - self.time <= 5:
            new_gem = GemDisplay(self.time, *self.gem_data.popleft(), self.spawn_bullets)
            self.rendered_gems.append(new_gem)
            self.objects.add(new_gem)

        # Check hit gems
        if self.player.shooting and len(self.rendered_gems) > 0:
            ray = (self.player.pos, self.player.dir)
            d = dist_from_ray(*ray, self.rendered_gems[0].pos)
            if d != False and d < 50. \
                    and abs(self.time-self.rendered_gems[0].hit_time) < 0.2:
                hit_gem = self.rendered_gems.popleft()
                hit_gem.on_hit()
                self.audio_ctrl.set_mute(False)
                self.healthbar = min(self.healthbar+1, 10)
                self.healthbar_sprite.set_health(self.healthbar)
                self.score += 50 * self._get_multiplier()
                self.combo += 1

        # Check passed gems
        if len(self.rendered_gems) > 0:
            if self.time - self.rendered_gems[0].hit_time > 0.2:
                passed_gem = self.rendered_gems.popleft()
                passed_gem.on_pass()
                self.audio_ctrl.set_mute(True)
                self.healthbar = max(self.healthbar-0.5, 0)
                self.healthbar_sprite.set_health(self.healthbar)
                self.combo = 0

        # Check initiate game over
        if self.healthbar <= 0:
            self.game_done = True
        if len(self.gem_data) == 0 and len(self.rendered_gems) == 0:
            self.game_done = True

        # Check game over state
        if self.game_done:
            self.game_over_countdown -= dt
            if self.game_over_countdown < 0:
                self.game_over_cb(self.score)
                return

        # Update game state
        if not self.game_done: # disable player controls if game over
            self.player.look_at(Window.mouse_pos)
            self.objects.on_update()
        self.camera.on_update(dt)
        self.audio_ctrl.on_update()



class Menu(BaseWidget):
    def __init__(self, start_cb):
        super(Menu, self).__init__()
        self.label = Label(
                text="SPACE GEM",
                color=(1.00, .996, .463, 0.7),
                font_name="./fonts/SourceCodePro-Semibold.ttf",
                font_size=72,
                halign='center',
                valign='center',
                pos=(Window.width/2-50, Window.height/2+100))

        self.start_btn = Button(
                text="START",
                color=(1.00, .996, .463, 0.7),
                font_name="./fonts/SourceCodePro-Semibold.ttf",
                font_size=60,
                background_color=(.137, .047, .447, 1.0),
                pos=(Window.width/2-200, Window.height/2-150),
                size=(400, 100))
        self.start_btn.bind(on_press=start_cb)

        self.add_widget(self.label)
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
