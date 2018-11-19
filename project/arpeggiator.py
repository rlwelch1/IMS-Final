import random
from common.clock import kTicksPerQuarter, quantize_tick_up


class Arpeggiator(object):
    def __init__(self, sched, synth, channel=0, patch=(0, 40), callback = None):
        super(Arpeggiator, self).__init__()
        self.sched = sched
        self.synth = synth
        self.channel = channel
        self.patch = patch
        self.callback = callback

        self.notes = None
        self.note_len = 0
        self.incr = 1
        self.reflect = False

        # run-time variables
        self.note_idx = 0
        self.on_cmd = None
        self.off_cmd = None
        self.playing = False

    # start the arpeggiator
    def start(self):
        if self.playing:
            return

        self.note_idx = 0
        self.playing = True

        # set up the correct sound (program change)
        self.synth.program(self.channel, self.patch[0], self.patch[1])

        # find the tick of the next beat, and make it "beat aligned"
        now = self.sched.get_tick()
        next_beat = quantize_tick_up(now, kTicksPerQuarter)

        # now, post the _noteon function (and remember this command)
        self.on_cmd = self.sched.post_at_tick(self._noteon, next_beat)
    
    # stop the arpeggiator
    def stop(self):
        if not self.playing:
            return 
            
        self.playing = False

        # in case there is a note on hanging, turn it off immediately
        if self.off_cmd:
            self.off_cmd.execute()

        # cancel anything pending in the future.
        self.sched.remove(self.on_cmd)
        self.sched.remove(self.off_cmd)

        # reset these so we don't have a reference to old commands.
        self.on_cmd = None
        self.off_cmd = None

    def toggle(self):
        if self.playing:
            self.stop()
        else:
            self.start()
    
    # notes is a list of MIDI pitch values. For example [60 64 67 72]
    def set_notes(self, notes):
        self.notes = notes
    
    # note_grid is the speed of the notes. For example 240 is 1/8th notes.
    # note_len_ratio defines the duration of the note. For example 0.5 will 
    # make notes last a duration of note_grid/2
    def set_rhythm(self, note_grid, note_len_ratio):
        self.note_len = note_grid * note_len_ratio

    # dir is either 'up', 'down', or 'updown'
    def set_direction(self, direction):
        self.incr = 1 if direction != 'down' else -1
        self.reflect = True if direction == 'updown' else False

    def _noteon(self, tick, ignore):
        # avoid race condition bug
        self.note_idx = min(self.note_idx, len(self.notes)-1)

        # pick pitch
        note_pitch = self.notes[self.note_idx]
        if self.reflect:
            if self.note_idx == 0 or self.note_idx == (len(self.notes) - 1):
                self.incr *= -1
        self.note_idx = (self.note_idx + self.incr) % len(self.notes)

        # play the note right now:
        self.synth.noteon(self.channel, note_pitch, 100)

        # post the note off for half a beat later:
        self.off_cmd = self.sched.post_at_tick(self._noteoff, tick + self.note_len, note_pitch)

        # schedule the next noteon for one beat later
        next_beat = tick + self.note_len
        self.on_cmd = self.sched.post_at_tick(self._noteon, next_beat)

        # callback for note_event
        if self.callback is not None:
            self.callback()

    def _noteoff(self, tick, pitch):
        # just turn off the currently sounding note.
        self.synth.noteoff(self.channel, pitch)

class JazzArpeggiator(object):
    def __init__(self, sched, synth, channel=0, patch=(0, 40), callback = None):
        super(JazzArpeggiator, self).__init__()
        self.sched = sched
        self.synth = synth
        self.channel = channel
        self.patch = patch
        self.callback = callback

        self.notes = None
        self.note_len = 0
        self.incr = 1

        # run-time variables
        self.note_idx = 0
        self.on_cmd = None
        self.off_cmd = None
        self.playing = False

        self.beat = 0

    # start the arpeggiator
    def start(self):
        if self.playing:
            return

        self.note_idx = 0
        self.playing = True

        # set up the correct sound (program change)
        self.synth.program(self.channel, self.patch[0], self.patch[1])

        # find the tick of the next beat, and make it "beat aligned"
        now = self.sched.get_tick()
        next_beat = quantize_tick_up(now, kTicksPerQuarter)

        # now, post the _noteon function (and remember this command)
        self.on_cmd = self.sched.post_at_tick(self._noteon, next_beat)
    
    # stop the arpeggiator
    def stop(self):
        if not self.playing:
            return 
            
        self.playing = False

        # in case there is a note on hanging, turn it off immediately
        if self.off_cmd:
            self.off_cmd.execute()

        # cancel anything pending in the future.
        self.sched.remove(self.on_cmd)
        self.sched.remove(self.off_cmd)

        # reset these so we don't have a reference to old commands.
        self.on_cmd = None
        self.off_cmd = None

    def toggle(self):
        if self.playing:
            self.stop()
        else:
            self.start()
    
    # notes is a list of MIDI pitch values. For example [60 64 67 72]
    def set_notes(self, notes):
        self.notes = notes
    
    # note_grid is the speed of the notes. For example 240 is 1/8th notes.
    # note_len_ratio defines the duration of the note. For example 0.5 will 
    # make notes last a duration of note_grid/2
    def set_rhythm(self, note_grid, note_len_ratio):
        self.note_len = note_grid * note_len_ratio

    # dir is either 'up', 'down', or 'updown'
    def set_direction(self, direction):
        self.incr = 1 if direction != 'down' else -1

    def _noteon(self, tick, ignore):
        # avoid race condition bug
        self.note_idx = min(self.note_idx, len(self.notes)-1)

        # pick pitch, length and velocity
        note_pitch = self.notes[self.note_idx]
        note_len = self.note_len
        velocity = 100
        incr = self.incr

        # probablistic changes
        if self.beat == 0:
            if random.uniform(0,1) < 0.3: # accented downbeat
                velocity *= 1.5
        if self.beat % 2 == 0:
            if random.uniform(0,1) < 0.3: # chromatic approach
                note_len /= 2
                note_pitch -= incr
                self.note_idx -= incr
            if random.uniform(0,1) < 0.4: # hold strong beat
                note_len *= 2
        if random.uniform(0,1) < 0.2:
            self.note_idx = (self.note_idx - incr * random.randint(1,5)) % len(self.notes)

        self.note_idx = (self.note_idx + incr) % len(self.notes)

        # play the note right now:
        self.synth.noteon(self.channel, note_pitch, velocity)

        # post the note off for half a beat later:
        self.off_cmd = self.sched.post_at_tick(self._noteoff, tick + note_len, note_pitch)

        # schedule the next noteon for one beat later
        next_beat = tick + note_len
        self.on_cmd = self.sched.post_at_tick(self._noteon, next_beat)

        # callback for note_event
        if self.callback is not None:
            self.callback(note_pitch, note_len)

        self.beat = (self.beat + 1) % 4

    def _noteoff(self, tick, pitch):
        # just turn off the currently sounding note.
        self.synth.noteoff(self.channel, pitch)
