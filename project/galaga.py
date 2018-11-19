# pset3.py

import sys
sys.path.append('..')
from common.core import *
from common.gfxutil import *
from common.audio import *
from common.mixer import *
from common.note import *
from common.wavegen import *
from common.wavesrc import *

from kivy.core.window import Window
from kivy.clock import Clock as kivyClock
from kivy.uix.label import Label
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate

from random import random, randint, choice
import numpy as np


class Enemy(InstructionGroup):
    def __init__(self, pos, r, color, collision_check, health = 3, death_anim_func = None, velocity = (0,-50)):
        super(Enemy, self).__init__()

        self.color = Color(*color)
        self.add(self.color)

        self.velocity = velocity

        self.collision_check = collision_check
        self.death_anim_func = death_anim_func
        self.circle = CEllipse(cpos = pos, size = (2*r, 2*r), segments = 40)
        self.add(self.circle)
        
        self.health = health

        self.time = 0
        self.dead = False
        self.on_update(0)
        
    # cause the enemy to get hit and be destroyed
    def kill(self):
        self.dead = True
        
    # cause enemy to be damaged when hit by a bullet, but not completely destroyed
    def damage(self):
        self.health -= 1
        if self.health <= 0:
            self.kill()
        
    def on_update(self, dt):
        # advance time
        self.time += dt
        
        # update position of enemy based on velocity
        cur_pos = self.circle.get_cpos()
        x, y = cur_pos
        new_x = x
        new_y = y + (self.velocity[1] * dt)
        
        self.circle.set_cpos((new_x, new_y))
        
        self.collision_check(self)

        # destroy enemy if the enemy is hit by the spaceship
        # callback function to cause particle effects at death location
        if self.dead and self.death_anim_func != None:
            self.death_anim_func(self.circle.get_cpos())
        return not self.dead
    
    
class Bullet(InstructionGroup):
    def __init__(self, pos, color, velocity = (0,500)):
        super(Bullet, self).__init__()

        self.color = Color(*color)
        self.add(self.color)

        self.velocity = velocity

        self.circle = CEllipse(cpos = pos, size = (2, 10), segments = 20)
        self.add(self.circle)

        self.time = 0
        self.dead = False
        self.on_update(0)
        
    # cause the bullet to get destroyed upon a collision
    def kill(self):
        self.dead = True
        
    def on_update(self, dt):
        # advance time
        self.time += dt
        
        # update position of bullet based on velocity
        cur_pos = self.circle.get_cpos()
        x, y = cur_pos
        new_x = x
        new_y = y + (self.velocity[1] * dt)
        
        self.circle.set_cpos((new_x, new_y))
        
        # destroy bullet if off screen
        if self.circle.get_cpos()[1] > 650:
            self.kill()

        # destroy bullet if the bullet hits enemy
        return not self.dead

class Spaceship(InstructionGroup):
    def __init__(self, pos, color, health = 5):
        super(Spaceship, self).__init__()

        self.color = Color(*color)
        self.add(self.color)

        self.pos = pos
        self.triangle = Triangle(points = [pos[0],pos[1],pos[0]+40,pos[1],pos[0]+20,pos[1]+35])
        self.cpos = (pos[0] + 20, pos[1] + 35/2)
        self.hit_radius = 35/3
        self.add(self.triangle)
        
        self.velocity = (0,0)
        
        self.health = health
        self.dead = False

        self.time = 0
        self.on_update(0)
        
    # these functions are used to manipulate the spaceship via player controls
    def set_x_velocity(self, vel):
        self.velocity = (vel, self.velocity[1])
        
    def set_y_velocity(self, vel):
        self.velocity = (self.velocity[0], vel)
        
    def kill(self):
        self.dead = True
    
    def damage(self):
        self.health -= 1
        if self.health <= 0:
            self.kill()
        
    def on_update(self, dt):
        # advance time
        self.time += dt
        
        # update position of spaceship based on velocity
        new_x = np.clip(self.pos[0] + self.velocity[0] * dt, 0, 800 - 40)
        new_y = np.clip(self.pos[1] + self.velocity[1] * dt, 0, 600 - 35)
        self.pos = (new_x, new_y)
        self.cpos = (self.pos[0] + 20, self.pos[1] + 35/2)
        new_points = [new_x, new_y, new_x + 40, new_y, new_x + 20, new_y + 35]
        self.triangle.points = new_points
        return not self.dead


class MainWidget(BaseWidget) :
    def __init__(self):
        super(MainWidget, self).__init__()
        
        # draw background
        self.canvas.add(Color(rgb=(0,0.2,0.55)))
        self.canvas.add(Rectangle(pos = (0,0), size = (800,600)))
        
        self.info = topleft_label()
        self.add_widget(self.info)

        # AnimGroup handles drawing, animation, and object lifetime management
        self.objects = AnimGroup()
        self.canvas.add(self.objects)
        
        self.paused = False
        
        self.enemies = []
        
        self.spaceship = Spaceship((400 - 20, 40), (0, 0.5, 0.5))
        self.bullets = []
        
        self.objects.add(self.spaceship)
        self.spaceship_velocity = 100
    
    def enemy_collision_check(self, enemy):
        circle = enemy.circle
        # check for collision with spaceship
        p = np.array(self.spaceship.cpos)
        enemy_to_ship = p - np.array(circle.get_cpos())
        
        # hit detection to the player is based on the inscribed circle of the spaceship
        if np.sqrt(enemy_to_ship.dot(enemy_to_ship)) < (circle.get_csize()[0]/2 + self.spaceship.hit_radius):
            # damage the player
            self.spaceship.damage()
            enemy.kill()
            self.enemies.remove(enemy)
        
        # check for collision with bullet
        remove = []
        for bullet in self.bullets:
            p = np.array(bullet.circle.get_cpos())
            enemy_to_bullet = p - np.array(circle.get_cpos())
            if np.sqrt(enemy_to_bullet.dot(enemy_to_bullet)) < (circle.get_csize()[0]/2):
                bullet.kill()
                remove.append(bullet)
                enemy.damage()
        for bullet in remove:
            self.bullets.remove(bullet)
        
    # initialize an enemy to drop on mouseclick
    def on_touch_down(self, touch):
        p = touch.pos
        r = 20
        c = (0.9, 0.1, 0.1)
        enemy = Enemy(p, r, c, self.enemy_collision_check)
        self.objects.add(enemy)
        self.enemies.append(enemy)

    def on_key_down(self, keycode, modifiers):
        
        # pause and unpause the game
        if keycode[1] == 'p':
            self.paused = False if self.paused else True
            
        # move the spaceship up
        if keycode[1] == 'w':
            self.spaceship.set_y_velocity(self.spaceship_velocity)
            
        # move the spaceship left
        if keycode[1] == 'a':
            self.spaceship.set_x_velocity(-self.spaceship_velocity * 1.5)            
        
        # move the spaceship down
        if keycode[1] == 's':
            self.spaceship.set_y_velocity(-self.spaceship_velocity)
            
        # move the spaceship right
        if keycode[1] == 'd':
            self.spaceship.set_x_velocity(self.spaceship_velocity * 1.5)
            
        # fire bullets
        if keycode[1] == 'spacebar':
            bullet = Bullet(self.spaceship.cpos, (1,1,1))
            self.objects.add(bullet)
            self.bullets.append(bullet)
            
    def on_key_up(self, keycode):
        
        # stop moving the spaceship up
        if keycode[1] == 'w':
            self.spaceship.set_y_velocity(0)
            
        # stop moving the spaceship left
        if keycode[1] == 'a':
            self.spaceship.set_x_velocity(0)
        
        # stop moving the spaceship down
        if keycode[1] == 's':
            self.spaceship.set_y_velocity(0)
        
        # stop moving the spaceship right
        if keycode[1] == 'd':
            self.spaceship.set_x_velocity(0)         

    def on_update(self):
        if not self.paused:
            self.objects.on_update()
            
        if self.spaceship.dead:
            self.info.text = "GAME OVER"
            return

        self.info.text = str(Window.mouse_pos)
        self.info.text += '\nfps:%d' % kivyClock.get_fps()
        self.info.text += '\nobjects:%d' % (self.objects.size())
        self.info.text += '\npaused:%s' % self.paused
        self.info.text += '\nhealth:%s' % self.spaceship.health


run(eval('MainWidget'))