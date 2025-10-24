from scamp import Session


class MyInstrument:
    def __init__(self, session=None):
        # allow injecting a Session for testability; create one if none provided
        if session is None:
            self.session = Session(tempo=120)
        else:
            self.session = session
        # create two midi parts addressed to LoopMIDI (adjust port name as needed)
        self.instrument_1 = self.session.new_midi_part("piano", "loopMIDI Port", start_channel=1, num_channels=1)
        self.instrument_2 = self.session.new_midi_part("piano", "loopMIDI Port", start_channel=2, num_channels=1)

    def play_note_instrument_1(self, pitch, duration):
        self.instrument_1.play_note(pitch, duration)

    def play_note_instrument_2(self, pitch, duration):
        self.instrument_2.play_note(pitch, duration)

    def stop_note_instrument_1(self, pitch):
        self.instrument_1.stop_note(pitch)

    def stop_note_instrument_2(self, pitch):
        self.instrument_2.stop_note(pitch)

    def pitch_instrument(self, pitch, instrument_number):
        if instrument_number == 1:
            self.instrument_1.pitch(pitch)
        elif instrument_number == 2:
            self.instrument_2.pitch(pitch)
        else:
            raise ValueError("Invalid instrument number. Use 1 or 2.")

    # Non-blocking start/stop helpers (use start_note/stop_note which don't wait)
    def start_note_instrument_1(self, pitch, velocity=100):
        try:
            self.instrument_1.start_note(pitch, velocity)
        except Exception:
            # SCAMP accepts note names or MIDI numbers; try int conversion fallback
            try:
                self.instrument_1.start_note(int(pitch), velocity)
            except Exception:
                pass

    def start_note_instrument_2(self, pitch, velocity=100):
        try:
            self.instrument_2.start_note(pitch, velocity)
        except Exception:
            try:
                self.instrument_2.start_note(int(pitch), velocity)
            except Exception:
                pass

    def stop_note_instrument_1_nonblock(self, pitch):
        try:
            self.instrument_1.stop_note(pitch)
        except Exception:
            try:
                self.instrument_1.stop_note(int(pitch))
            except Exception:
                pass

    def stop_note_instrument_2_nonblock(self, pitch):
        try:
            self.instrument_2.end_note(pitch)
        except Exception:
            try:
                self.instrument_2.end_note(int(pitch))
            except Exception:
                pass

    # Non-blocking start/stop helpers so external controllers can start/stop notes
    def start_note_instrument_1(self, pitch, velocity=100):
        try:
            self.instrument_1.start_note(int(pitch), velocity)
        except Exception:
            # fallback: try passing note name
            self.instrument_1.start_note(pitch, velocity)

    def start_note_instrument_2(self, pitch, velocity=100):
        try:
            self.instrument_2.start_note(int(pitch), velocity)
        except Exception:
            self.instrument_2.start_note(pitch, velocity)

   