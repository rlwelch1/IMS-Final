import sys
import random
sys.path.append('..')
from common.core import *
from common.audio import *
from common.synth import *
from common.gfxutil import *
from common.clock import *
from common.metro import *
from arpeggiator import *

# part 1: create Arpeggiator (in pset4_arpeg.py) and test it here
class MainWidget1(BaseWidget) :
    def __init__(self):
        super(MainWidget1, self).__init__()

        self.audio = Audio(2)
        self.synth = Synth('../data/FluidR3_GM.sf2')

        # create TempoMap, AudioScheduler
        self.tempo_map  = SimpleTempoMap(120)
        self.sched = AudioScheduler(self.tempo_map)

        # connect scheduler into audio system
        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)

        # create the metronome:
        self.metro = Metronome(self.sched, self.synth)

        # create the arpeggiator:
        self.arpeg = Arpeggiator(self.sched, self.synth, channel = 1, patch = (0,0) )

        # and text to display our status
        self.label = topleft_label()
        self.add_widget(self.label)

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 'm':
            self.metro.toggle()

        if keycode[1] == 'a':
            self.arpeg.start()

        notes = lookup(keycode[1], 'qwe', ((60, 64, 67, 72), (55, 59, 62, 65, 67, 71), (60, 65, 69)))
        if notes:
            self.arpeg.set_notes(notes)

        rhythm = lookup(keycode[1], 'uiop', ((120, 1), (160, 1), (240, 0.75), (480, 0.25)))
        if rhythm:
            self.arpeg.set_rhythm(*rhythm)

        direction = lookup(keycode[1], '123', ('up', 'down', 'updown'))
        if direction:
            self.arpeg.set_direction(direction)

    def on_key_up(self, keycode):
        if keycode[1] == 'a':
            self.arpeg.stop()

    def on_update(self) :
        self.audio.on_update()
        self.label.text = self.sched.now_str() + '\n'
        self.label.text += 'tempo:%d\n' % self.tempo_map.get_tempo()
        self.label.text += 'm: toggle Metronome\n'
        self.label.text += 'a: Enable Arpeggiator\n'
        self.label.text += 'q w e: Changes notes\n'
        self.label.text += 'u i o p: Change Rhythm\n'
        self.label.text += '1 2 3: Change Direction\n'

C7 = [60, 64, 67, 70]
C7MAJ = [60, 64, 67, 71]
C7MIN = [60, 63, 67, 70]
CHORD_BASES = [C7.copy(), C7MAJ.copy(), C7MIN.copy()]
C7_BEBOP = [60, 62, 64, 65, 67, 69, 70, 71]

def AUGMENT(base, aug):
    return [p+aug for p in base]

def ARPEGIATE(base, aug, octva, length):
    return [p-12*(octva-o) for o in range(length) for p in AUGMENT(base, aug)]

def ALLOCATE(base, aug, octva, length, skip):
    return [ARPEGIATE(base, aug, octva, length)[i*skip:i*skip+len(base)] for i in range(12)]

def GET_CHORDS_LIST(aug, ctype):
    return ARPEGIATE(CHORD_BASES[ctype], aug, 3, 2)

def GET_NOTES_LIST(aug):
    return ALLOCATE(C7_BEBOP, aug, 2, 6, 2)

# Chord Progression for Dolphin Shoals
CHORD_PROGRESSION = [
    (0, 1, 4), # augmentation, chord type, num beats
    (2, 2, 4),
    (4, 2, 4),
    (7, 0, 4),
    # repeat
    (0, 1, 4),
    (2, 2, 4),
    (4, 2, 4),
    (7, 0, 4),
    # A'
    (2, 2, 4),
    (7, 0, 4),
    (3, 2, 4),
    (8, 0, 4),
    # end
    (2, 2, 2),
    (4, 2, 2),
    (7, 0, 4),
    (2, 2, 2),
    (4, 2, 2),
    (7, 0, 4),
    # B
    (0, 1, 8),
    (5, 1, 8),
    (0, 1, 8),
    (5, 1, 8),
]

BASS_RHYTHM = (480, 1)
RHYTHMS_LIST = [(120*2**(5-i), 1) for i in range(6)]

DIRECTION_LIST = ["up", "down"]
SWITCH_CHANCE = 0.01

class Bubble(InstructionGroup):
    def __init__(self, pos, r, color):
        super(Bubble, self).__init__()

        self.radius_anim = KFAnim((0, 0), (.1, 5*r), (.9, r))

        self.color = Color(hsv=color)
        self.add(self.color)

        self.circle = CEllipse(cpos = pos, size = (2*r, 2*r), segments = 40)
        self.add(self.circle)

        self.time = 0
        self.on_update(0)

    def on_update(self, dt):
        # advance time
        self.time += dt

        rad = self.radius_anim.eval(self.time)
        self.circle.csize = (2*rad, 2*rad)

        v = Window.size[1] / 3
        pos = (self.circle.cpos[0], self.circle.cpos[1] + v * dt)
        self.circle.cpos = pos
        return pos[1] > 0

# Part 2, 3, and 4
class MainWidget2(BaseWidget) :
    def __init__(self):
        super(MainWidget2, self).__init__()
        # Graphics
        self.objects = AnimGroup()
        self.canvas.add(self.objects)

        # Audio
        self.audio = Audio(2)
        self.synth = Synth('../data/FluidR3_GM.sf2')

        # create TempoMap, AudioScheduler
        self.tempo_map  = SimpleTempoMap(120)
        self.sched = AudioScheduler(self.tempo_map)

        # connect scheduler into audio system
        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)

        self.beat = 0
        self.chord_idx = 0
        self.chord_list = GET_CHORDS_LIST(*CHORD_PROGRESSION[self.chord_idx][:-1])
        self.notes_list = GET_NOTES_LIST(CHORD_PROGRESSION[self.chord_idx][0])

        # create a drumkit
        self.drums = Arpeggiator(self.sched, self.synth, channel = 0, patch = (128, 0))
        self.drums.set_notes([35, 42, 38, 42])
        self.drums.set_rhythm(*BASS_RHYTHM)

        # create the bass:
        self.bass = Arpeggiator(self.sched, self.synth, channel = 1, patch = (0,32), callback = self._add_beat)
        self.bass.set_notes(self.chord_list)
        self.bass.note_idx = 15
        self.bass.set_rhythm(*BASS_RHYTHM) 

        # create the arpeggiator:
        self.arpeg = JazzArpeggiator(self.sched, self.synth, channel = 2, patch = (0,65), callback = self._gen)

        # and text to display our status
        self.label = topleft_label()
        self.add_widget(self.label)

    def _add_beat(self):
        self.beat += 1
        if CHORD_PROGRESSION[self.chord_idx][2] == self.beat - 1:
            self.chord_idx = (self.chord_idx+1) % len(CHORD_PROGRESSION)
            self.chord_list = GET_CHORDS_LIST(*CHORD_PROGRESSION[self.chord_idx][:-1])
            self.bass.set_notes(self.chord_list)
            self.notes_list = GET_NOTES_LIST(CHORD_PROGRESSION[self.chord_idx][0])
            self.beat = 0

    def _gen(self, pitch, length):
        # Graphics
        p = ((pitch - 35) / 50) * Window.width, max(Window.height - length / 3, 0)
        r = 10
        c = ((pitch - 35) / 50,1,1)
        self.objects.add(Bubble(p, r, c))

    def on_key_down(self, keycode, modifiers):
        if keycode[1] == 's':
            self.drums.toggle()
            self.bass.toggle()

    def on_key_up(self, keycode):
        pass

    def on_touch_down(self, touch):
        notes_idx = int(touch.pos[0] / (Window.width / len(self.notes_list)))
        rhythms_idx = int(touch.pos[1] / (Window.height / len(RHYTHMS_LIST)))

        self.arpeg.set_notes(self.notes_list[notes_idx])
        self.arpeg.set_rhythm(*RHYTHMS_LIST[rhythms_idx])

        self.arpeg.start()

    def on_touch_up(self, touch):
        self.arpeg.stop()
        pass

    def on_touch_move(self, touch):
        notes_idx = int(touch.pos[0] / (Window.width / len(self.notes_list)))
        rhythms_idx = int(touch.pos[1] / (Window.height / len(RHYTHMS_LIST)))

        self.arpeg.set_notes(self.notes_list[notes_idx])
        self.arpeg.set_rhythm(*RHYTHMS_LIST[rhythms_idx])

    def on_update(self) :
        self.objects.on_update()
        self.audio.on_update()
        self.label.text = self.sched.now_str() + '\n'

        if random.uniform(0,1) < SWITCH_CHANCE:
            direction = random.choice(DIRECTION_LIST)
            self.arpeg.set_direction(direction)
        if random.uniform(0,1) < SWITCH_CHANCE:
            direction = random.choice(DIRECTION_LIST)
            self.bass.set_direction(direction)

# pass in which MainWidget to run as a command-line arg
run(eval('MainWidget' + sys.argv[1]))
