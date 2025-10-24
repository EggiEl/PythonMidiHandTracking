from midimapper import MidiController
from handTracking import HandTracker
import cv2

midiController = MidiController('loopMIDI Port 1', channel=0)  # channel ggf. anpassen!

handTracker = HandTracker()
handTracker.init()
activeDrumTrack = -1

# Track welche Geste zuletzt verarbeitet wurde
last_processed_left_gesture = None
last_processed_right_gesture = None

#main Loop
while handTracker.cap.isOpened():
    success, image = handTracker.cap.read()
    if not success:
        print("Kamera kann nicht gelesen werden.")
        break

    # Frame verarbeiten und annotiertes Bild zurückbekommen
    annotated_image = handTracker.run(image)
    # Anzeige des Kamerabildes
    cv2.imshow('Hand Gesture Tracking', annotated_image)
    
    # Nur senden wenn sich die gelockte Geste geändert hat
    last_processed_left_gesture, activeDrumTrack = midiController.drums_up_down(activeDrumTrack, handTracker.left_locked_gesture, last_processed_left_gesture)
    
    # Beenden bei Tastendruck 'q'
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

handTracker.cap.release()
cv2.destroyAllWindows()