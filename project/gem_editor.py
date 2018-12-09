# Lab3 - Graphics

import sys
sys.path.append('..')
from common.core import *
from common.gfxutil import *
from common.audio import *
from common.writer import *
from common.mixer import *
from common.note import *
from wavesrc import *

from kivy.core.window import Window
from kivy.graphics.instructions import InstructionGroup
from kivy.graphics import Color, Ellipse, Rectangle, Line
from kivy.graphics import PushMatrix, PopMatrix, Translate, Scale, Rotate

import numpy as np

# wave generator from pset 2
class WaveGenerator(object):
    def __init__(self, wave_source, loop=False):
        super(WaveGenerator, self).__init__()
        self.source = wave_source
        self.frame = 0
        self.paused = False
        self.release_flag = False
        self.loop = loop

    def reset(self):
        self.frame = 0
        self.release_flag = False

    def play_toggle(self):
        return self.play() if self.paused else self.pause()

    def play(self):
        self.paused = False
        return "Playing"
        
    def pause(self):
        self.paused = True
        return "Paused"
        
    # mark release flag so generate() will return False continue flag and empty output
    def release(self):
        if self.frame != 0:
            self.release_flag = True

    def generate(self, num_frames, num_channels) :
        assert(num_channels == self.source.get_num_channels())
        
        # initialize output to zero in case of pause
        # also look for release commands even while paused
        if self.paused:
            output = np.zeros(num_frames * num_channels)
            # reset if releasing
            if self.release_flag:
                self.reset()
            return (output, not self.release_flag)            
    
        # get data based on our position and requested # of frames
        output = self.source.get_frames(self.frame, self.frame + num_frames)

        # advance current-frame
        self.frame += num_frames

        # check for end-of-buffer condition:
        shortfall = num_frames * num_channels - len(output)
        continue_flag = shortfall == 0 and not self.release_flag
        if shortfall > 0:        
            
            # handle looping if necessary
            if self.loop:
                output = np.append(output, self.source.get_frames(0, shortfall//num_channels))
                self.frame = shortfall
                continue_flag = True and not self.release_flag
            else:
                output = np.append(output, np.zeros(shortfall))

        # reset if releasing or if non-looping gen finishes playing (so they can be reused)
        if self.release_flag or not continue_flag:
            self.reset()
        # return
        return (output, continue_flag)

def sec_to_frames(sec):
    return int(sec * 44100) # sampling rate is 44100 Hz

gem_timings = []
# return a list of WaveBuffers
def make_wave_buffers(regions_path, wave_path):
    
    buffers = []
    global gem_timings
    
    # extract lines, tokenize, and place in buffers dict
    f = open(regions_path)
    lines = f.readlines()
    f.close()
    
    # tokenize lines, create WaveBuffers, and map them to names in buffers dict
    previous_time = 0
    for line in lines:
        tokens = line.strip().split('\t')
        start = sec_to_frames(previous_time)
        num_frames = sec_to_frames(float(tokens[0])) - start
        buffers.append(WaveBuffer(wave_path, start, num_frames))
        previous_time = float(tokens[0])
        gem_timings.append(previous_time)
    
    return buffers

# gem class to keep track of positional data of gems in editor interface
class Gem(InstructionGroup):
    # colors of gems
    COLORS =    [Color(1,0,0), # red
                 Color(1,0.65,0), #orange
                 Color(1,1,0), # yellow
                 Color(0,1,0), # green
                 Color(0,0,1), # blue
                 Color(1,0,1) # purple
                 ]
    
    # sizes of gems
    SIZES =     [30,
                 50,
                 80]
    
    def __init__(self, callback, pos=(0,0), size=0, color=0):
        super(Gem, self).__init__()

        # make the dot white
        self.add(Gem.COLORS[color])
        
        x = pos[0] - pos[0] % 10
        y = pos[1] - pos[1] % 10
        self.pos = (x, y)
        self.size = size
        self.color = color

        self.dot = CEllipse(cpos=self.pos, segments = 20)
        self.dot.csize = (Gem.SIZES[size], Gem.SIZES[size])
        self.add(self.dot)
        
        self.visible = True 
        self.callback = callback

        self.on_update(0)
        
    # make the gem disappear, record positional data
    def complete(self, end_time):
        self.visible = False
        x, y = self.pos
        normalized_pos = (x/800, y/600)
        self.callback(end_time, normalized_pos, self.color, self.size)
        
    def adjust_pos(self, x, y):
        newx = np.clip(self.pos[0] + x, 0, 800)
        newy = np.clip(self.pos[1] + y, 0, 600)
        self.pos = (newx, newy)
        self.dot.set_cpos(self.pos)
        
    # delete the gem without recording positional data
    def delete(self):
        self.visible = False

    def on_update(self, dt):
        return self.visible


class MainWidget(BaseWidget):
    def __init__(self):
        super(MainWidget, self).__init__()
        self.anim_group = AnimGroup()
        self.canvas.add(self.anim_group)

        self.info = topleft_label()
        self.add_widget(self.info)
        
        # keeps track of gems and their positional data in editor
        self.gems = []
        self.gem_data = []
        
        self.writer = AudioWriter('data') # for debugging audio output
        self.audio = Audio(2, self.writer.add_audio)
        self.mixer = Mixer()
        self.audio.set_generator(self.mixer)
        
        # waveBuffer setup to create music segments that gems will encapsulate
        self.wave_buffer = make_wave_buffers("./TestAnnotation.txt", "./AloneStandard.wav")
        self.current_wave_buffer = 0
        # play the first segment of music in the editor, but do not record a gem for it
        self.mixer.add(WaveGenerator(self.wave_buffer[self.current_wave_buffer]))
        self.current_wave_buffer += 1
        
        self.completion_text = False
        self.current_gem = None
        self.increment = 10
        self.color = 0
        self.gem_size = 0
        
    def add_data(self, end_time, pos, color, size):
        self.gem_data.append((end_time, pos, color, size))
        
    # export the gem data stored from the editor into a .txt file to be used for the game
    def export_data(self):
        # write all data to the text file
        f = open("./level.txt", "w")
        assert(len(self.gem_data) == len(gem_timings))
        for i in range(len(self.gem_data)):
            timing = gem_timings[i]
            g = self.gem_data[i]
            end_time = g[0]
            gem_pos = g[1]
            color = g[2]
            gem_radius = Gem.SIZES[g[3]]
            gem_delay = 2
            
            # format:
            # timestamp endtime xpos,ypos radius delay color
            to_write =  str(timing) + ' ' + str(end_time) + ' ' + str(gem_pos[0]) + ',' + str(gem_pos[1]) + ' ' + \
                        str(gem_radius) + ' ' + str(gem_delay) + ' ' + str(color) + '\n'
            f.write(to_write)
        f.close()
            

    def on_update(self):
        self.audio.on_update()
        self.anim_group.on_update()
        self.update_info_label()

    # create the current gem in the editor, play the music segment that corresponds with the gem, increment to the next music segment
    def on_touch_down(self, touch):
        if self.completion_text:
            return
        gem = Gem(self.add_data, pos=touch.pos, color=self.color, size=self.gem_size)
        self.current_gem = gem
        self.gems.append(gem)
        self.anim_group.add(gem)
        # the final gem does not play the remainder of the song in the editor, so we display a completion message once it is placed
        if self.current_wave_buffer == len(self.wave_buffer):
            self.on_complete()
            self.current_wave_buffer += 1
            return
        self.mixer.add(WaveGenerator(self.wave_buffer[self.current_wave_buffer]))
        self.current_wave_buffer += 1
        
    def on_complete(self):
        self.completion_text = True
    
    def on_key_down(self, keycode, modifiers):
        # remove the gems on the screen in the editor (first in, first out) and record their data
        if keycode[1] == 'delete':
            if len(self.gems) == 0:
                return
            gem = self.gems.pop(0)
            if self.current_wave_buffer > len(gem_timings):
                gem.complete(199.575) # this time is the end of the song
            else:
                gem.complete(gem_timings[self.current_wave_buffer - 1])
            
        # undo the most recent gem placement, rewind to the previous music segment to redo gem placement
        if keycode[1] == 'backspace':
            if len(self.gems) == 0:
                return
            gem = self.gems.pop(-1)
            gem.delete()
            self.current_wave_buffer -= 1
            self.current_wave_buffer = np.clip(self.current_wave_buffer, 1, len(self.wave_buffer))
            self.completion_text = False
            self.current_gem = self.gems[-1] if len(self.gems) != 0 else None
            
        # print the gem data and length of the wave buffer for debugging
        if keycode[1] == 'p':
            print("length of wave buffer: " + str(len(self.wave_buffer)))
            print(self.gem_data)
            
        # toggle gem size
        if keycode[1] == 's':
            self.gem_size += 1
            self.gem_size = self.gem_size % len(Gem.SIZES)
            
        # toggle color
        if keycode[1] == 'c':
            self.color += 1
            self.color = self.color % len(Gem.COLORS)
            
        # replay current music segment that requires a gem assignment
        if keycode[1] == 'spacebar':
            if self.current_wave_buffer < len(self.wave_buffer):
                self.mixer.add(WaveGenerator(self.wave_buffer[self.current_wave_buffer]))
            
        # if all gems required have been placed, completes the editing process and exports all data to .txt file
        if keycode[1] == 'enter':
            if self.completion_text:
                for gem in self.gems:
                    gem.complete(199.575)
                self.export_data()
                
        # adjust increment to move gems by
        if keycode[1] == 'shift':
            self.increment = 10 if self.increment == 50 else 50
                
        # adjust current gem position
        vert_adjust = lookup(keycode[1], ('up', 'down'), (self.increment, -self.increment))
        if vert_adjust and self.current_gem:
            self.current_gem.adjust_pos(0, vert_adjust)
            
        horiz_adjust = lookup(keycode[1], ('left', 'right'), (-self.increment, self.increment))
        if horiz_adjust and self.current_gem:
            self.current_gem.adjust_pos(horiz_adjust, 0)
            
        if keycode[1] == 'numpad1':
            self.color = 0
        if keycode[1] == 'numpad2':
            self.color = 1
        if keycode[1] == 'numpad3':
            self.color = 2
        if keycode[1] == 'numpad4':
            self.color = 3
        if keycode[1] == 'numpad5':
            self.color = 4
        if keycode[1] == 'numpad6':
            self.color = 5
        if keycode[1] == 'numpad7':
            self.gem_size = 0
        if keycode[1] == 'numpad8':
            self.gem_size = 1
        if keycode[1] == 'numpad9':
            self.gem_size = 2
            
    def update_info_label(self):
        color_names = ["red", "orange", "yellow", "green", "blue", "purple"]
        sizes = ["50", "75", "30"]
        self.info.text = color_names[self.color] + ' ' + sizes[self.gem_size]
        if self.completion_text:
            self.info.text = 'press enter if done, or backspace to continue editing'



# TODO:
"""
1. annotate the soundtrack of AloneStandard in SonicVisualizer to segment gems
2. check if editor works with annotated .txt file and wave buffers
3. implement export_data functionality to create a .txt file to be used for the game with (timestamp xpos,ypos gemRadius gemDelay)
4. use editor to create level for AloneStandard
"""

run(MainWidget)
