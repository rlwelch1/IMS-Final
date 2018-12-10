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

class Bullet(InstructionGroup):
    def __init__(self, pos, collision_check_callback, damage_player_callback, velocity, color=(1,1,1)):
        super(Bullet, self).__init__()

        self.color = Color(*color)
        self.add(self.color)
        
        self.collision_check = collision_check_callback
        self.damage_player = damage_player_callback

        self.velocity = velocity
        
        self.pos = pos
        
        self.add(PushMatrix())
        
        self._pos = Translate(*self.pos)
        self.add(self._pos)
        self.circle = CEllipse(cpos = (0.,0.), size = (10, 10), segments = 10)
        self.add(self.circle)
        
        self.add(PopMatrix())

        self.time = 0
        self.lifetime = 5
        self.dead = False
        
    # cause the bullet to get destroyed upon a collision
    def kill(self):
        self.dead = True
        
    def on_update(self, dt):
        # advance time
        self.time += dt
        
        # update position of bullet based on velocity
        cur_pos = self.pos
        x, y = cur_pos
        new_x = x + (self.velocity[0] * dt)
        new_y = y + (self.velocity[1] * dt)
        self.pos = (new_x, new_y)
        self._pos.x, self._pos.y = self.pos
        self.circle.set_cpos((0,0))
        
        # check for collision with player with callback
        if self.collision_check(self.pos):
            self.damage_player()        
            self.kill()
        
        # destroy bullet if lifetime is up
        if self.time > self.lifetime:
            self.kill()

        # destroy bullet if the bullet hits enemy
        return not self.dead
    
# healthbar class
class HealthBar(InstructionGroup):
    def __init__(self):
        super(HealthBar, self).__init__()
        
        self.color = Color(0,1,0.1)
        
        self.pos = (175,550)
        
        self.add(PushMatrix())
        self.add(Translate(*self.pos))
        self.add(Color(0.4,0.4,0.4))
        self.add(Rectangle(pos=(0,0), size=(450,25)))
        self.add(self.color)
        self.rect = Rectangle(pos=(0,0), size=(450,25))
        self.add(self.rect)
        self.add(Color(1,1,1))
        self.add(PopMatrix())
        
    def set_health(self, health):
        h = np.clip(health, 0.00001, 10)
        h_percent = float(h)/10.
        r, g, b = np.clip(1/h_percent-0.5,0,1), np.clip(h_percent+0.25,0,1), 0.1
        self.color.rgb = (r,g,b)
        self.rect.size = (450 * h_percent, 25)
        
    def on_update(self, dt):
        return True

class GemDisplay(InstructionGroup):
    BORDER = np.array((1., 1.))
    COLOR_LIST = [
        (1, 0, 0),
        (1, .65, 0),
        (1, 1, 0),
        (0, 1, 0),
        (0, 0, 1),
        (1, 0, 1)
    ]
    def __init__(self, spawn_time, hit_time, kill_time, pos, border_size, anticipate_len, color_idx, produce_bullets_callback):
        super(GemDisplay, self).__init__()
        self.pos = pos
        self.border_size = np.array((border_size, border_size))
        self.core_size = np.array((0.,0.))
        
        self.produce_bullets = produce_bullets_callback

        self.add(PushMatrix())
        self.color = color_idx

        self.border_color = Color(*self.COLOR_LIST[color_idx],0.0)
        self.add(self.border_color)
        self._pos = Translate(*self.pos)
        self.add(self._pos)
        self.border_circle = CEllipse(cpos=(0,0), csize=self.border_size, segments=20)
        self.add(self.border_circle)
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
        self.miss = True

        self.time = spawn_time

    def on_hit(self):
        self.core_color.rgb = self.COLOR_LIST[self.color]
        self.miss = False

    def on_pass(self):
        self.core_color.rgb = (0.4,0.4,0.4)
        self.miss = True
        
    def spawn_bullets(self):
        # use callback to game control script
        self.produce_bullets(self.pos)

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
            self.black_color.a = 0.7
            self.core_color.a = (self.time - anim_start)/self.anticipate_len
            self.core_circle.csize = (radius, radius)
        elif self.time >= self.hit_time and self.time < self.kill_time:
            self.core_color.a = 1
            self.black_color.a = 1
            if not self.miss:
                self.border_color.rgb = (0.1,1,0.1)
                self.border_color.a = np.clip(1-(self.time - self.hit_time)**0.5,0,1)
                self.border_circle.set_csize(self.border_size + np.clip(50*(1-(self.time - self.hit_time)**2),0,50))
            else:
                self.border_color.rgb = (1,0,0)
                self.border_color.a = np.clip(1-(self.time - self.hit_time)**0.5,0,1)
                self.border_circle.set_csize(self.border_size + np.clip(50*(1/(self.time - self.hit_time)**2),0,50))
        else:
            kill = False
        
        if not kill:
            self.spawn_bullets()

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
        
    def get_pos(self):
        return (self.pos[0],self.pos[1])

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
