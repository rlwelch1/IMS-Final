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
    def __init__(self, hit_time, pos, msize, lifetime):
        super(GemDisplay, self).__init__()
        self.pos = pos
        self.msize = np.array((msize, msize))
        self.bsize = np.array((0.,0.))

        self.add(PushMatrix())

        self.mcolor = Color(1,1,0,0.0)
        self.add(self.mcolor)
        self._pos = Translate(*self.pos)
        self.add(self._pos)
        self.add(CEllipse(cpos=(0,0), csize=self.msize, segments=20))
        self.tcolor = Color(0,0,0,0.0)
        self.add(self.tcolor)
        self.add(CEllipse(cpos=(0,0),
            csize=self.msize-self.BORDER, segments=20))
        self.bcolor = Color(1,1,0,0.3)
        self.add(self.bcolor)
        self.bcircle = CEllipse(cpos=(0,0), csize=self.bsize, segments=20)
        self.add(self.bcircle)

        self.add(PopMatrix())

        self.anim = KFAnim(
            # time,                  radius, b_alpha, m_alpha, 
            (0,                      self.bsize[0], 0., 0.),
            (hit_time-lifetime-0.01, self.bsize[0], 0.0, 0.),
            (hit_time-lifetime,      self.bsize[0], 0.3, 1.),
            (hit_time-0.01,          self.msize[0], 0.3, 1.),
            (hit_time,               self.msize[0], 1, 1.),
            (hit_time+0.5,           self.msize[0], 1., 1.)
        )
        self.hit_time = hit_time

        self.time = 0
        self.on_update(self.time)

    def on_hit(self):
        self.bcolor.rgb = (0,1,0)

    def on_pass(self):
        self.bcolor.rgb = (1,0,0)

    def on_update(self, dt):
        self.time += dt

        radius, b_alpha, m_alpha = self.anim.eval(self.time)
        self.bcircle.csize = (radius, radius)
        self.bcolor.a = b_alpha
        self.mcolor.a = m_alpha
        self.tcolor.a = m_alpha

        return self.anim.is_active(self.time)


class PlayerDisplay(InstructionGroup):
    VEL_MAX = 500.
    def __init__(self):
        super(PlayerDisplay, self).__init__()
        self.size = np.array((50., 50.))
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

        self.addons = list()

        self.time = 0
        self.on_update(0)

    def look_at(self, pos):
        self.dir = normalize(pos - self.pos)
        self._rot.angle = dir2angle(self.dir)

    def add_lvel(self, vel_dir):
        self.lvel += normalize(vel_dir) * self.VEL_MAX

    def shoot(self):
        self.addons.append(ExplosionDisplay(self.pos))
        self.add(self.addons[-1])
        self.addons.append(LaserDisplay(self.pos,self.dir))
        self.add(self.addons[-1])

        return(self.pos, self.dir)

    def on_update(self, dt):
        self.time += dt

        for addon in self.addons:
            addon.on_update(dt)

        # update velocity
        self.vel_target = self.dir * self.lvel[1] + \
                          tangent(self.dir) * self.lvel[0]
        self.vel += (self.vel_target - self.vel) * 0.999 * dt 
        # update possition
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
        self.on_update(self.time)

    def add_trauma(self):
        self.trauma = max(1, self.trauma + self.TRAUMA_INCR)
        return

    def on_update(self, dt):
        self.time += dt
        if self.trauma > 0:
            self.trauma -= dt

        shake = self.trauma**3

        seed = [((self.seed[i]+self.time)%1024)*self.NOISE_MULT for i in range(3)]

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
                (.2, 120, 1),
                (.23, 120, 0))

        self.time = 0
        self.on_update(self.time)

    def on_update(self, dt):
        self.time += dt

        radius, alpha = self.anim.eval(self.time)
        self.circle.csize = (radius, radius)
        self.color.a = alpha

        return self.anim.is_active(self.time)


class LaserDisplay(InstructionGroup):
    def __init__(self, start, vec):
        super(LaserDisplay, self).__init__()

        pos = start
        angle = dir2angle(vec)

        self.add(PushMatrix())
        self.color = Color(1,1,1)
        self.add(self.color)
        self.add(Translate(*pos))
        self.add(Rotate(angle=angle))
        self.rect = Rectangle(pos=(0,0), size=(0,0))
        self.add(self.rect)
        self.add(PopMatrix())

        self.anim = KFAnim(
                # time, width, length, alpha
                (0, 100, 0, 1),
                (.03, 100, 1000, 1),
                (.2, 100, 1000., 1),
                (.23, 100, 1000, 0))

        self.time = 0
        self.on_update(self.time)

    def on_update(self, dt):
        self.time += dt

        width, length, alpha = self.anim.eval(self.time)
        self.rect.size = (length, width)
        self.rect.pos = (0, -width/2)
        self.color.a = alpha

        return self.anim.is_active(self.time)
