from common.clock import kTicksPerQuarter, quantize_tick_up


class Arpeggiator(object):
    def __init__(self, sched, synth, channel=0, patch=(0, 40), callback = None):
        super(Arpeggiator, self).__init__()

    # start the arpeggiator
    def start(self):
        pass
    
    # stop the arpeggiator
    def stop(self):
        pass
    
    # notes is a list of MIDI pitch values. For example [60 64 67 72]
    def set_notes(self, notes):
        pass
    
    # note_grid is the speed of the notes. For example 240 is 1/8th notes.
    # note_len_ratio defines the duration of the note. For example 0.5 will 
    # make notes last a duration of note_grid/2
    def set_rhythm(self, note_grid, note_len_ratio):
        pass

    # dir is either 'up', 'down', or 'updown'
    def set_direction(self, direction):
        pass 
