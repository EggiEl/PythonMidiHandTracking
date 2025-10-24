import mido
import time

class MidiController:
    def __init__(self, midi_port: str, channel: int = 0, press_ms: int = 30):
        # Prüfe, ob Port existiert (optional, aber hilfreich beim Debuggen)
        available = mido.get_output_names()
        if midi_port not in available:
            raise RuntimeError(f"MIDI-Port '{midi_port}' nicht gefunden. Verfügbar: {available}")

        self.out = mido.open_output(midi_port)
        self.channel = channel
        self.press_delay = max(1, press_ms) / 1000.0  # Sekunden
        # CC-Nummern (so wie du gemappt hast)
        self.drums = [10, 11, 12, 13, 14, 15]
        # z.B. 20 = Overdub, 21 = (optional etwas anderes)
        self.automation = [20, 21]

    # ---- intern: kurzer Button-"Klick" per CC ----
    def _cc_pulse(self, cc: int, value_on: int = 127, value_off: int = 0):
        self.out.send(mido.Message('control_change', control=cc, value=value_on, channel=self.channel))
        time.sleep(self.press_delay)
        self.out.send(mido.Message('control_change', control=cc, value=value_off, channel=self.channel))

    # ---- optional: nur "halten" (momentary) ----
    def _cc_hold(self, cc: int, hold_seconds: float = 0.2, value_on: int = 127, value_off: int = 0):
        self.out.send(mido.Message('control_change', control=cc, value=value_on, channel=self.channel))
        time.sleep(max(0, hold_seconds))
        self.out.send(mido.Message('control_change', control=cc, value=value_off, channel=self.channel))

    # ---- deine "Konfigurations"-Helfer (wenn du beim Mappen was schicken willst) ----
    def configure_drums(self, wait_each_sec: float = 0.0):
        for cc in self.drums:
            self.out.send(mido.Message('control_change', control=cc, value=0, channel=self.channel))
            if wait_each_sec > 0:
                time.sleep(wait_each_sec)

    def configure_automation(self, wait_each_sec: float = 0.0):
        for cc in self.automation:
            self.out.send(mido.Message('control_change', control=cc, value=0, channel=self.channel))
            if wait_each_sec > 0:
                time.sleep(wait_each_sec)

    # ---- Overdub (auf CC 20 gemappt) ----
    def toggle_overdub(self):
        # entspricht kurzem Tastendruck → Ableton toggelt den Button
        self._cc_pulse(20)

    # Falls du Overdub explizit "gedrückt halten" willst:
    def overdub_for(self, seconds: float):
        self._cc_hold(20, hold_seconds=seconds)

    # ---- Recording (falls du Record-Button ebenfalls auf CC 20/21 gemappt hast) ----
    # Start (Button drücken)
    def start_recording(self):
        self._cc_pulse(20)

    # Stop (falls eigener CC z.B. 21 gemappt ist)
    def stop_recording(self):
        self._cc_pulse(21)

    # ---- Drum-Trigger (je Slot ein CC aus self.drums) ----
    def send_drum_up(self, drum_track: int):
        if 0 <= drum_track < len(self.drums):
            cc = self.drums[drum_track]
            self._cc_pulse(cc)   # kurzer Klick: 127 → 0
        else:
            raise IndexError(f"drum_track {drum_track} außerhalb des Bereichs 0..{len(self.drums)-1}")

    def send_drum_down(self, drum_track: int):
        # Falls du "Down" getrennt gemappt hast (eigener CC), trage ihn hier ein.
        # Wenn "Up" und "Down" der gleiche Button sind (toggle), kannst du auch einfach wieder _cc_pulse(cc) senden.
        if 0 <= drum_track < len(self.drums):
            cc = self.drums[drum_track]
            self._cc_pulse(cc)   # bei toggle-Buttons genauso
        else:
            raise IndexError(f"drum_track {drum_track} außerhalb des Bereichs 0..{len(self.drums)-1}")

    def drums_up_down(self, activeDrumTrack, lockedGesture, last_processed): 
        """Sendet MIDI-Signal wenn eine neue Geste gelockt wurde (auch wenn es dieselbe Geste ist)."""
        # Prüfen ob die gelockte Geste None ist (entsperrt wurde)
        if lockedGesture is None:
            # Wenn die Geste entsperrt wurde, setze last_processed zurück
            if last_processed is not None:
                print("🔄 Gestenverarbeitung zurückgesetzt - bereit für neue Geste")
            return None, activeDrumTrack

        # Nur senden wenn die Geste sich geändert hat (neu gelockt wurde)
        if lockedGesture != last_processed:
            print("Drum up/down Funktion aufgerufen")
            print(f"Neue gelockte Geste: {lockedGesture}")

            if lockedGesture == "DAUMEN_HOCH":
                activeDrumTrack += 1
                # Begrenze den Wert
                if activeDrumTrack > len(self.drums) - 1:
                    activeDrumTrack = len(self.drums) - 1

                print(f"🎵 Drum Up gesendet - Track {activeDrumTrack}, CC {self.drums[activeDrumTrack]}")
                self.send_drum_up(activeDrumTrack)

            elif lockedGesture == "DAUMEN_RUNTER":
                activeDrumTrack -= 1
                # Begrenze den Wert
                if activeDrumTrack < 0:
                    activeDrumTrack = 0

                print(f"🎵 Drum Down gesendet - Track {activeDrumTrack}, CC {self.drums[activeDrumTrack]}")
                self.send_drum_down(activeDrumTrack)

            return lockedGesture, activeDrumTrack  # Gebe beide Werte zurück

        return last_processed, activeDrumTrack  # Keine Änderung 

