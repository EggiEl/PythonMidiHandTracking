import mido, time
class MidiController:
    def __init__(self, midiPort: str):
        self.out = mido.open_output(midiPort)
        #Drum Ports up and down
        self.drums = [10,11,12,13,14,15]
        #Recording Start, Stop Automation
        self.automation = [20,21]

    # CC 10, 11, 12 steuern verschiedene Slots
    def configure_drums(self):
        for i in self.drums:
            time.sleep(2)
            self.out.send(mido.Message('control_change', control=i, value=0))

    def configure_automation(self): 
        for i in self.automation:
            time.sleep(2)
            self.out.send(mido.Message('control_change', control=i, value=0))

    def start_overdub(self):
        self.out.send(mido.Message('start', control=20, value=0))

    def start_recording(self):  
        self.out.send(mido.Message('control_change', control=20, value=127))

    def stop_recording(self):
        self.out.send(mido.Message('control_change', control=20, value=0))