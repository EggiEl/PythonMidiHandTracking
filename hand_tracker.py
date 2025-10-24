import cv2
import mediapipe as mp
import numpy as np
import math
from scamptest import MyInstrument 
# --- KONFIGURATION ---
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=2, # Erlaubt zwei Hände
    min_detection_confidence=0.6) # Etwas höhere Konfidenz für Stabilität

mp_drawing = mp.solutions.drawing_utils

# Instrument manager: zwei Instrumente via scamptest
inst_manager = MyInstrument()
active_instrument = 1  # 1 or 2
prev_left_open = False
current_playing_note = None
current_playing_instrument = None

# Kamera starten
cap = cv2.VideoCapture(0)
print("Vollständige Gestensteuerung gestartet. Drücken Sie 'q' zum Beenden.")

# --- Hilfsfunktion zur Gesten-Erkennung (Offen/Geschlossen) ---
def check_hand_open(hand_landmarks):
    """Prüft, ob die Hand offen oder geschlossen ist."""
    
    # Indizes der Fingerspitzen (ausgenommen Daumen für Vereinfachung)
    finger_tips = [mp_hands.HandLandmark.INDEX_FINGER_TIP,
                   mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
                   mp_hands.HandLandmark.RING_FINGER_TIP,
                   mp_hands.HandLandmark.PINKY_TIP]
    
    open_fingers_count = 0
    
    # Iteriere durch die 4 Hauptfinger
    for tip_idx in finger_tips:
        tip_y = hand_landmarks.landmark[tip_idx].y
        
        # Die Basis des Fingers (z.B. Index_PIP für den Zeigefinger)
        # Für einen einfachen Vergleich nutzen wir das nächst-niedrigere Gelenk (Y-Wert)
        pip_y = hand_landmarks.landmark[tip_idx - 2].y 
        
        # Wenn die Spitze (kleinerer Y-Wert) deutlich über dem Gelenk liegt, ist der Finger gestreckt
        if tip_y < pip_y:
             open_fingers_count += 1
             
    # Geste definieren:
    if open_fingers_count >= 3:
        return "OFFEN (Synth/Lead)"
    elif open_fingers_count <= 1:
        return "GESCHLOSSEN (Drums/Faust)"
    else:
        return "Unbestimmt"

# --- Hilfsfunktion zur Distanzberechnung ---
def calculate_distance(p1, p2):
    """Berechnet die euklidische Distanz zwischen zwei normalisierten Landmarken."""
    return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)


def midi_note_from_norm(y_norm: float, low: int = 48, high: int = 84) -> int:
    """Map normalized Y (0=top,1=bottom) to MIDI note number.
    Invert y so raised hand -> higher pitch.
    """
    v = 1.0 - float(y_norm)
    v = max(0.0, min(1.0, v))
    note = int(round(low + v * (high - low)))
    return note

# --- HAUPT-LOOP ---
while cap.isOpened():
    success, image = cap.read()
    if not success:
        print("Kamera kann nicht gelesen werden.")
        break
        
    # Bild spiegeln und Dimensionen abrufen
    image = cv2.flip(image, 1) 
    H, W, _ = image.shape
    
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = hands.process(image_rgb)
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    

    wrist_positions = {}
    hand_gestures = {}
    
    if results.multi_hand_landmarks:
        for hand_index, hand_landmarks in enumerate(results.multi_hand_landmarks):
            
            # --- FEATURE 1 & 2: Geste & Position Tracking ---
            label = results.multi_handedness[hand_index].classification[0].label
            wrist_landmark = hand_landmarks.landmark[mp_hands.HandLandmark.WRIST]
            
            # Geste bestimmen
            gesture_status = check_hand_open(hand_landmarks)
            hand_gestures[label] = gesture_status
            
            # Speichern der Position
            wrist_positions[label] = wrist_landmark
            
            # Position in Pixeln
            x_pixel = int(wrist_landmark.x * W)
            y_pixel = int(wrist_landmark.y * H)
            
            # Zeichnen und Text-Feedback für Geste/Position
            mp_drawing.draw_landmarks(image_bgr, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            
            text_color = (0, 255, 0) if "OFFEN" in gesture_status else (0, 0, 255)
            cv2.putText(image_bgr, f"{label}: {gesture_status}", (x_pixel - 100, y_pixel - 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
            
            if label == 'Right':
                # Spezifische Positionsausgabe für die rechte Hand (z.B. für Pitch)
                pitch_value = wrist_landmark.y
                note = midi_note_from_norm(pitch_value, low=48, high=84)
                cv2.putText(image_bgr, f"PITCH: {note}", (x_pixel - 20, y_pixel - 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)

                # Play/stop based on right-hand open/closed
                if "OFFEN" in gesture_status:
                    # start note on active instrument if not already playing this note
                    if current_playing_note != note or current_playing_instrument != active_instrument:
                        # stop previous
                        if current_playing_note is not None:
                            if current_playing_instrument == 1:
                                inst_manager.stop_note_instrument_1_nonblock(current_playing_note)
                            else:
                                inst_manager.stop_note_instrument_2_nonblock(current_playing_note)
                        # start new
                        if active_instrument == 1:
                            inst_manager.start_note_instrument_1(note, velocity=100)
                            current_playing_instrument = 1
                        else:
                            inst_manager.start_note_instrument_2(note, velocity=100)
                            current_playing_instrument = 2
                        current_playing_note = note
                else:
                    # stop any currently playing note
                    if current_playing_note is not None:
                        if current_playing_instrument == 1:
                            inst_manager.stop_note_instrument_1_nonblock(current_playing_note)
                        else:
                            inst_manager.stop_note_instrument_2_nonblock(current_playing_note)
                        current_playing_note = None
                        current_playing_instrument = None
                
    # --- FEATURE 3: Relativer Distanz-Tracker ---
    if 'Left' in wrist_positions and 'Right' in wrist_positions:
        
        wrist_left = wrist_positions['Left']
        wrist_right = wrist_positions['Right']
        
        # 1. Distanz berechnen
        normalized_distance = calculate_distance(wrist_left, wrist_right)
        
        # 2. Distanz in Pixeln (zum Zeichnen)
        p1 = (int(wrist_left.x * W), int(wrist_left.y * H))
        p2 = (int(wrist_right.x * W), int(wrist_right.y * H))
        
        # 3. Linie zeichnen (weiß)
        cv2.line(image_bgr, p1, p2, (255, 255, 255), 4)
        
        # 4. Text-Feedback für die Länge (Lautstärke/Tempo)
        distance_text = f"VOLUME/TEMPO: {normalized_distance:.3f}"
        text_pos = (int((p1[0] + p2[0]) / 2) - 150, int((p1[1] + p2[1]) / 2) - 20)
        
        # Grüner Balken/Text, wenn die Distanz für Looping (Faust) genutzt wird
        display_color = (0, 255, 255) 

        cv2.putText(image_bgr, distance_text, text_pos, 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, display_color, 2)

        # --- KONSOLEN-AUSGABE DER WICHTIGSTEN STEUERDATEN ---
        left_gesture = hand_gestures.get('Left', 'Unbestimmt')
        print("\n--- STEUERDATEN (READY FOR MIDI/OSC) ---")
        print(f"Distanz (Volume): {normalized_distance:.3f}")
        print(f"Rechte Hand (Pitch Y): {wrist_positions['Right'].y:.3f}")
        print(f"Linke Geste (Instrument): {left_gesture}")
        print(f"Aktives Instrument: {active_instrument}")
        print("------------------------------------------")

        # Toggle active instrument on left-hand rising edge (closed -> open)
        left_open = ('OFFEN' in left_gesture)
        if left_open and not prev_left_open:
            active_instrument = 2 if active_instrument == 1 else 1
            print(f'Instrument gewechselt: {active_instrument}')

        prev_left_open = left_open


    # Anzeige des Kamerabildes
    cv2.imshow('FULL GENERATIVE MUSIC CONTROLLER', image_bgr)
    
    # Beenden bei Tastendruck 'q'
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()