from common.clock import kTicksPerQuarter, quantize_tick_up


class Arpeggiator(object):
    def __init__(self, sched, synth, channel=0, patch=(0, 40), callback = None):
        super(Arpeggiator, self).__init__()
        
        self.sched = sched
        self.synth = synth
        self.channel = channel
        self.patch = patch
        self.callback = callback
        
        self.notes = []
        self.is_playing = False
        self.note_grid = 480
        self.note_len_ratio = 1
        self.direction = ''

    # start the arpeggiator
    def start(self):
        self.is_playing = True
        self.play()
    
    # stop the arpeggiator
    def stop(self):
        self.is_playing = False
    
    # notes is a list of MIDI pitch values. For example [60 64 67 72]
    def set_notes(self, notes):
        self.notes = notes
    
    # note_grid is the speed of the notes. For example 240 is 1/8th notes.
    # note_len_ratio defines the duration of the note. For example 0.5 will 
    # make notes last a duration of note_grid/2
    def set_rhythm(self, note_grid, note_len_ratio):
        self.note_grid = note_grid
        self.note_len_ratio = note_len_ratio

    # dir is either 'up', 'down', or 'updown'
    def set_direction(self, direction):
        self.direction = direction 

    def play(self):
        if len(self.notes) == 0 or self.direction == '':
            raise Exception('Must set the notes and direction before playing')