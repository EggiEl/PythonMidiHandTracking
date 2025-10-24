from midimapper import MidiController
from handTracking import HandTracker
import cv2
import time 

midiController = MidiController('loopMIDI Port 1', channel=0)  # channel ggf. anpassen!

handTracker = HandTracker()
handTracker.init()
activeDrumTrack = -1

# Track welche Geste zuletzt verarbeitet wurde
last_processed_left_gesture = None
last_processed_right_gesture = None

def drums_up_down(activeDrumTrack, lockedGesture, last_processed): 
    """Sendet MIDI-Signal nur wenn sich die gelockte Geste geändert hat."""
    # Nur senden wenn die Geste sich geändert hat (neu gelockt wurde)
    if lockedGesture != last_processed and lockedGesture is not None:
        print("Drum up/down Funktion aufgerufen")
        print(f"Neue gelockte Geste: {lockedGesture}")
        
        if lockedGesture == "DAUMEN_HOCH":
            activeDrumTrack += 1
            # Begrenze den Wert
            if activeDrumTrack > len(midiController.drums) - 1:
                activeDrumTrack = len(midiController.drums) - 1
            
            print(f"🎵 Drum Up gesendet - Track {activeDrumTrack}, CC {midiController.drums[activeDrumTrack]}")
            midiController.send_drum_up(activeDrumTrack)

        elif lockedGesture == "DAUMEN_RUNTER":
            activeDrumTrack -= 1
            # Begrenze den Wert
            if activeDrumTrack < 0:
                activeDrumTrack = 0
            
            print(f"🎵 Drum Down gesendet - Track {activeDrumTrack}, CC {midiController.drums[activeDrumTrack]}")
            midiController.send_drum_down(activeDrumTrack)
        
        return lockedGesture, activeDrumTrack  # Gebe beide Werte zurück
    
    return last_processed, activeDrumTrack  # Keine Änderung 

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
    last_processed_left_gesture, activeDrumTrack = drums_up_down(activeDrumTrack, handTracker.left_locked_gesture, last_processed_left_gesture)
    
    # Beenden bei Tastendruck 'q'
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

handTracker.cap.release()
cv2.destroyAllWindows()