import sys
sys.path.append('..')
from common.core import *
from common.audio import *
from common.synth import *
from common.gfxutil import *
from common.clock import *
from common.metro import *
from arpeggiator import *

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


# Part 2, 3, and 4
class MainWidget2(BaseWidget) :
    def __init__(self):
        super(MainWidget2, self).__init__()

        self.audio = Audio(2)
        self.synth = Synth('../data/FluidR3_GM.sf2')

        # create TempoMap, AudioScheduler
        self.tempo_map  = SimpleTempoMap(120)
        self.sched = AudioScheduler(self.tempo_map)

        # connect scheduler into audio system
        self.audio.set_generator(self.sched)
        self.sched.set_generator(self.synth)

        # and text to display our status
        self.label = topleft_label()
        self.add_widget(self.label)

    def on_key_down(self, keycode, modifiers):
        pass

    def on_key_up(self, keycode):
        pass

    def on_touch_down(self, touch):
        pass

    def on_touch_up(self, touch):
        pass

    def on_touch_move(self, touch):
        pass

    def on_update(self) :
        self.audio.on_update()
        self.label.text = self.sched.now_str() + '\n'


# pass in which MainWidget to run as a command-line arg
#run(eval('MainWidget' + sys.argv[1]))
run(eval('MainWidget' + '1'))

