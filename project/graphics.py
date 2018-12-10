import sys
sys.path.append('..')
from common.gfxutil import *
from common.vecutil import *

from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Line, Rectangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate
from kivy.clock import Clock as kivyClock

import random
import numpy as np
from noise import pnoise1

class GemDisplay(InstructionGroup):
    BORDER = np.array((1., 1.))
    COLOR_LIST = [
        (.957, .133, .192),
        (.98, .494, .133),
        (.98, .686, .133),
        (.651, .914, .125),
        (.157, .282, .663),
        (.306, .157, .675)
    ]
    def __init__(self, spawn_time, hit_time, kill_time, pos, border_size, anticipate_len, color_idx):
        super(GemDisplay, self).__init__()
        self.pos = pos
        self.border_size = np.array((border_size, border_size))
        self.core_size = np.array((0.,0.))

        self.add(PushMatrix())

        self.border_color = Color(*self.COLOR_LIST[color_idx],0.0)
        self.add(self.border_color)
        self._pos = Translate(*self.pos)
        self.add(self._pos)
        self.add(CEllipse(cpos=(0,0), csize=self.border_size, segments=20))
        self.black_color = Color(0,0,0,0.0)
        self.add(self.black_color)
        self.add(CEllipse(cpos=(0,0),
            csize=self.border_size-self.BORDER, segments=20))
        self.core_color = Color(*self.COLOR_LIST[color_idx],0.3)
        self.add(self.core_color)
        self.core_circle = CEllipse(cpos=(0,0), csize=self.core_size, segments=20)
        self.add(self.core_circle)

        self.add(PopMatrix())

        self.anim = KFAnim(
            (0, self.core_size[0]),
            (anticipate_len, self.border_size[0]-self.BORDER[0])
        )
        self.spawn_time = spawn_time
        self.anticipate_len = anticipate_len
        self.hit_time = hit_time
        self.kill_time = kill_time

        self.time = spawn_time

    def on_hit(self):
        self.core_color.rgb = (1,1,1)

    def on_pass(self):
        self.core_color.rgb = (0.4,0.4,0.4)

    def on_update(self, dt):
        self.time += dt

        anim_start = self.hit_time - self.anticipate_len
        kill = True

        if self.time < anim_start:
            self.border_color.a = 0
            self.black_color.a = 0
            self.core_color.a = 0
        elif self.time >= anim_start and self.time < self.hit_time:
            radius = self.anim.eval(self.time-anim_start)
            self.border_color.a = 0.3
            self.black_color.a = 1.0
            self.core_color.a = 0.3
            self.core_circle.csize = (radius, radius)
        elif self.time >= self.hit_time and self.time < self.kill_time:
            self.core_color.a = 1
            self.black_color.a = 1
        else:
            kill = False

        return kill


class PlayerDisplay(InstructionGroup):
    def __init__(self):
        super(PlayerDisplay, self).__init__()
        self.VEL_MAX = 500.

        self.size = np.array((50., 40.))
        self.pos = np.array((0., 0.))
        self.dir = np.array((0., 0.))
        self.lvel = np.array((0., 0.))
        self.vel = np.array((0., 0.))
        self.vel_target = np.array((0., 0.))

        self.add(PushMatrix())

        self._pos = Translate(*self.pos)
        self.add(self._pos)

        self._rot = Rotate(angle=(dir2angle(self.dir)))
        self.add(self._rot)

        self.sprite = Triangle(cpos=self.pos, csize=self.size)
        self.add(self.sprite)

        self.add(PopMatrix())

        self.laser = None
        self.shooting = False

        self.explosions = AnimGroup()
        self.add(self.explosions)

        self.pos = np.array((Window.width/2, Window.height/2))
        self.time = 0
        self.on_update(0)

    def look_at(self, pos):
        self.dir = normalize(pos - self.pos)
        self._rot.angle = dir2angle(self.dir)

    def add_lvel(self, vel_dir):
        self.lvel += normalize(vel_dir) * self.VEL_MAX

    def shoot(self):
        if not self.shooting:
            self.shooting = True
            assert(self.laser == None)
            self.laser = LaserDisplay(self.pos, self.dir)
            self.add(self.laser)
            self.explosions.add(ExplosionDisplay(self.pos))
        return

    def release(self):
        if self.shooting:
            self.shooting = False
            assert(self.laser != None)
            self.remove(self.laser)
            self.laser = None
        return

    def on_update(self, dt):
        self.time += dt

        # set laser direction
        if self.laser != None:
            self.laser.pos = self.pos
            self.laser._pos.x, self.laser._pos.y = self.pos
            self.laser.angle = dir2angle(self.dir)
            self.laser._rot.angle = self.laser.angle

        self.explosions.on_update()

        # update velocity
        self.vel_target = self.lvel
        self.vel += (self.vel_target - self.vel) * 0.999 * dt 

        # update position
        self.pos = np.clip(self.pos+self.vel*dt, self.size/2,
                np.array((Window.width, Window.height))-self.size/2)
        self._pos.x, self._pos.y = self.pos

        return True

class Camera(InstructionGroup):
    # Class constants
    MAX_ANGLE = 2
    MAX_OFFSET = 20
    TRAUMA_INCR = 0.2
    NOISE_MULT = 10

    def __init__(self, objects):
        super(Camera, self).__init__()
        self.add(PushMatrix())
        self.add(objects)
        self.offset = Translate(0, 0)
        self.add(self.offset)
        self.angle = Rotate(angle=0)
        self.add(self.angle)
        self.add(objects)
        self.add(PopMatrix())

        self.trauma = 1
        self.seed = [random.randint(0, 256) for _ in range(3)]

        self.time = 0
        self.on_update(0)

    def add_trauma(self):
        self.trauma = max(1, self.trauma + self.TRAUMA_INCR)
        return

    def on_update(self, dt):
        self.time += dt
        if self.trauma > 0:
            self.trauma -= dt

        shake = self.trauma**3

        seed = [
                ((self.seed[i]+self.time)%1024)*self.NOISE_MULT
                for i in range(3)
        ]

        self.angle.angle = self.MAX_ANGLE * shake * pnoise1(seed[0])
        self.offset.x = self.MAX_OFFSET * shake * pnoise1(seed[1])
        self.offset.y = self.MAX_OFFSET * shake * pnoise1(seed[2])

class ExplosionDisplay(InstructionGroup):
    def __init__(self, pos):
        super(ExplosionDisplay, self).__init__()

        self.add(PushMatrix())
        self.add(Translate(*pos))
        self.color = Color(1,1,1)
        self.add(self.color)
        self.circle = CEllipse(cpos=(0,0), csize=(0, 0), segments=40)
        self.add(self.circle)
        self.add(PopMatrix())

        self.anim = KFAnim(
                # time, radius, alpha
                (0, 80,  1),
                (.03, 120,  1),
                (.4, 120, 1),
                (.43, 120, 0))

        self.time = 0
        self.on_update(0)

    def on_update(self, dt):
        self.time += dt

        radius, alpha = self.anim.eval(self.time)
        self.circle.csize = (radius, radius)
        self.color.a = alpha

        return self.anim.is_active(self.time)


class LaserDisplay(InstructionGroup):
    def __init__(self, start, vec):
        super(LaserDisplay, self).__init__()

        self.pos = start
        self.angle = dir2angle(vec)

        self.add(PushMatrix())
        self.color = Color(1,1,1)
        self.add(self.color)
        self._pos = Translate(*self.pos)
        self.add(self._pos)
        self._rot = Rotate(angle=self.angle)
        self.add(self._rot)
        self.rect = Rectangle(pos=(0,0), size=(0,0))
        self.add(self.rect)
        self.add(PopMatrix())

        self.rect.size = (1000, 100)
        self.rect.pos = (0, -50)

        self.on_update(0)

    def on_update(self, dt):
        return True
