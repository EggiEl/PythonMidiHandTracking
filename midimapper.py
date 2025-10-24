import mido, time
out = mido.open_output('PythonMIDI')

# CC 10, 11, 12 steuern verschiedene Slots
out.send(mido.Message('control_change', control=10, value=127))  # z. B. Clip 1 starten
time.sleep(0.5)
out.send(mido.Message('control_change', control=11, value=127))  # Clip 2 starten
