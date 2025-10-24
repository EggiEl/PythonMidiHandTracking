import cv2
import mediapipe as mp
import numpy as np
import math
import time


class HandTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.cap = cv2.VideoCapture(0)

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=2,  # Erlaubt zwei Hände
            min_detection_confidence=0.6)  # Etwas höhere Konfidenz für Stabilität
        
        # Gesten-Tracking über Zeit
        self.left_gesture_start_time = None
        self.left_current_gesture = None
        self.left_locked_gesture = None
        
        self.right_gesture_start_time = None
        self.right_current_gesture = None
        self.right_locked_gesture = None

        self.gesture_hold_duration = 2.0  # Sekunden, die eine Geste gehalten werden muss
    
    def init(self):
        # Kamera starten
        self.cap = cv2.VideoCapture(0)
        print("Vollständige Gestensteuerung gestartet. Drücken Sie 'q' zum Beenden.")
    
    # --- Hilfsfunktion zur Gesten-Erkennung (Offen/Geschlossen) ---
    def check_hand_open(self, hand_landmarks):
        """Prüft, ob die Hand offen oder geschlossen ist."""
        
        # Indizes der Fingerspitzen (ausgenommen Daumen für Vereinfachung)
        finger_tips = [self.mp_hands.HandLandmark.INDEX_FINGER_TIP,
                       self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP,
                       self.mp_hands.HandLandmark.RING_FINGER_TIP,
                       self.mp_hands.HandLandmark.PINKY_TIP]
        
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
    
    # --- Gesten-Erkennung für Daumen hoch/runter ---
    def check_thumbs_gesture(self, hand_landmarks):
        """Prüft, ob die Hand Daumen hoch oder runter zeigt."""
        
        # Landmarks für Daumen
        thumb_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_TIP]
        thumb_ip = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_IP]
        thumb_mcp = hand_landmarks.landmark[self.mp_hands.HandLandmark.THUMB_MCP]
        
        # Landmarks für andere Finger (zum Prüfen ob sie geschlossen sind)
        index_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        index_pip = hand_landmarks.landmark[self.mp_hands.HandLandmark.INDEX_FINGER_PIP]
        middle_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        middle_pip = hand_landmarks.landmark[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
        ring_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.RING_FINGER_TIP]
        ring_pip = hand_landmarks.landmark[self.mp_hands.HandLandmark.RING_FINGER_PIP]
        pinky_tip = hand_landmarks.landmark[self.mp_hands.HandLandmark.PINKY_TIP]
        pinky_pip = hand_landmarks.landmark[self.mp_hands.HandLandmark.PINKY_PIP]
        
        # Handgelenk als Referenz
        wrist = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
        
        # Prüfe ob die anderen 4 Finger eingeklappt sind (Spitzen unter den PIPs)
        fingers_closed_count = 0
        if index_tip.y > index_pip.y:
            fingers_closed_count += 1
        if middle_tip.y > middle_pip.y:
            fingers_closed_count += 1
        if ring_tip.y > ring_pip.y:
            fingers_closed_count += 1
        if pinky_tip.y > pinky_pip.y:
            fingers_closed_count += 1
        
        # Mindestens 3 Finger müssen geschlossen sein
        if fingers_closed_count < 3:
            return None  # Keine Daumen-Geste
        
        # Prüfe ob Daumen ausgestreckt ist (Distanz zwischen Tip und MCP)
        thumb_distance = abs(thumb_tip.y - thumb_mcp.y)
        
        # Daumen muss deutlich ausgestreckt sein (nicht eingeklappt wie bei Faust)
        if thumb_distance < 0.06:
            return None  # Daumen nicht ausgestreckt genug
        
        # Prüfe Daumen-Richtung: Daumen hoch = Tip über MCP, Daumen runter = Tip unter MCP
        if thumb_tip.y < thumb_mcp.y - 0.08:  # Daumen zeigt nach oben
            return "DAUMEN_HOCH"
        elif thumb_tip.y > thumb_mcp.y + 0.08:  # Daumen zeigt nach unten
            return "DAUMEN_RUNTER"
        
        return None
    
    # --- Hilfsfunktion zur Distanzberechnung ---
    def calculate_distance(self, p1, p2):
        """Berechnet die euklidische Distanz zwischen zwei normalisierten Landmarken."""
        return math.sqrt((p2.x - p1.x)**2 + (p2.y - p1.y)**2)
    
    def midi_note_from_norm(self, y_norm: float, low: int = 48, high: int = 84) -> int:
        """Map normalized Y (0=top,1=bottom) to MIDI note number.
        Invert y so raised hand -> higher pitch.
        """
        v = 1.0 - float(y_norm)
        v = max(0.0, min(1.0, v))
        note = int(round(low + v * (high - low)))
        return note
    
    # --- Gesten-Tracking über Zeit ---
    def update_gesture_tracking(self, label, gesture):
        """Aktualisiert das Gesten-Tracking für eine Hand und gibt zurück ob eine Geste gelockt wurde."""
        current_time = time.time()
        
        if label == 'Left':
            # Wenn die aktuelle Geste sich von der gelockten unterscheidet, unlock durchführen
            if self.left_locked_gesture is not None and gesture != self.left_locked_gesture:
                print(f"🔓 LINKE HAND GESTE ENTSPERRT: {self.left_locked_gesture}")
                self.left_locked_gesture = None
            
            # Wenn die Geste sich geändert hat, Timer zurücksetzen
            if gesture != self.left_current_gesture:
                self.left_current_gesture = gesture
                self.left_gesture_start_time = current_time
                return False
            
            # Wenn die Geste lange genug gehalten wurde
            if self.left_gesture_start_time is not None:
                elapsed = current_time - self.left_gesture_start_time
                if elapsed >= self.gesture_hold_duration and self.left_locked_gesture != gesture:
                    self.left_locked_gesture = gesture
                    print(f"🔒 LINKE HAND GESTE GELOCKT: {gesture}")
                    return True
        
        elif label == 'Right':
            # Wenn die aktuelle Geste sich von der gelockten unterscheidet, unlock durchführen
            if self.right_locked_gesture is not None and gesture != self.right_locked_gesture:
                print(f"🔓 RECHTE HAND GESTE ENTSPERRT: {self.right_locked_gesture}")
                self.right_locked_gesture = None
            
            # Wenn die Geste sich geändert hat, Timer zurücksetzen
            if gesture != self.right_current_gesture:
                self.right_current_gesture = gesture
                self.right_gesture_start_time = current_time
                return False
            
            # Wenn die Geste lange genug gehalten wurde
            if self.right_gesture_start_time is not None:
                elapsed = current_time - self.right_gesture_start_time
                if elapsed >= self.gesture_hold_duration and self.right_locked_gesture != gesture:
                    self.right_locked_gesture = gesture
                    print(f"🔒 RECHTE HAND GESTE GELOCKT: {gesture}")
                    return True
        
        return False
    
    def get_gesture_progress(self, label):
        """Gibt den Fortschritt (0.0 bis 1.0) zurück, wie lange die aktuelle Geste gehalten wird."""
        current_time = time.time()
        
        if label == 'Left' and self.left_gesture_start_time is not None:
            elapsed = current_time - self.left_gesture_start_time
            return min(elapsed / self.gesture_hold_duration, 1.0)
        elif label == 'Right' and self.right_gesture_start_time is not None:
            elapsed = current_time - self.right_gesture_start_time
            return min(elapsed / self.gesture_hold_duration, 1.0)
        
        return 0.0
    
    # --- Verarbeitet einen einzelnen Frame ---
    def run(self, image):
        """Verarbeitet einen einzelnen Frame und gibt das annotierte Bild zurück."""
        # Bild spiegeln und Dimensionen abrufen
        image = cv2.flip(image, 1) 
        H, W, _ = image.shape
        
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = self.hands.process(image_rgb)
        image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
        

        wrist_positions = {}
        hand_gestures = {}
        
        if results.multi_hand_landmarks:
            for hand_index, hand_landmarks in enumerate(results.multi_hand_landmarks):
                
                # --- FEATURE 1 & 2: Geste & Position Tracking ---
                label = results.multi_handedness[hand_index].classification[0].label
                wrist_landmark = hand_landmarks.landmark[self.mp_hands.HandLandmark.WRIST]
                
                # Geste bestimmen
                gesture_status = self.check_hand_open(hand_landmarks)
                
                # Für linke Hand: zusätzlich auf Daumen-Gesten prüfen
                if label == 'Left':
                    thumbs_gesture = self.check_thumbs_gesture(hand_landmarks)
                    if thumbs_gesture:
                        gesture_status = thumbs_gesture
                
                hand_gestures[label] = gesture_status
                
                # Gesten-Tracking über Zeit aktualisieren
                self.update_gesture_tracking(label, gesture_status)
                progress = self.get_gesture_progress(label)
                
                # Speichern der Position
                wrist_positions[label] = wrist_landmark
                
                # Position in Pixeln
                x_pixel = int(wrist_landmark.x * W)
                y_pixel = int(wrist_landmark.y * H)
                
                # Zeichnen und Text-Feedback für Geste/Position
                self.mp_drawing.draw_landmarks(image_bgr, hand_landmarks, self.mp_hands.HAND_CONNECTIONS)
                
                # Farbe abhängig von der Geste
                if "DAUMEN_HOCH" in gesture_status:
                    text_color = (0, 255, 255)  # Gelb
                elif "DAUMEN_RUNTER" in gesture_status:
                    text_color = (255, 0, 255)  # Magenta
                elif "OFFEN" in gesture_status:
                    text_color = (0, 255, 0)  # Grün
                else:
                    text_color = (0, 0, 255)  # Rot
                    
                cv2.putText(image_bgr, f"{label}: {gesture_status}", (x_pixel - 100, y_pixel - 30), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
                
                # Fortschrittsbalken für Gesten-Tracking anzeigen
                if progress > 0:
                    bar_width = 100
                    bar_height = 10
                    bar_x = x_pixel - 50
                    bar_y = y_pixel + 20
                    
                    # Hintergrund (grau)
                    cv2.rectangle(image_bgr, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height), (100, 100, 100), -1)
                    
                    # Fortschritt (grün wenn komplett, sonst gelb)
                    progress_width = int(bar_width * progress)
                    progress_color = (0, 255, 0) if progress >= 1.0 else (0, 255, 255)
                    cv2.rectangle(image_bgr, (bar_x, bar_y), (bar_x + progress_width, bar_y + bar_height), progress_color, -1)
                
                # Zeige gelockte Geste an
                locked_gesture = self.left_locked_gesture if label == 'Left' else self.right_locked_gesture
                if locked_gesture:
                    cv2.putText(image_bgr, f"LOCKED: {locked_gesture}", (x_pixel - 100, y_pixel + 50), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                
                if label == 'Right':
                    # Spezifische Positionsausgabe für die rechte Hand (z.B. für Pitch)
                    pitch_value = wrist_landmark.y
                    note = self.midi_note_from_norm(pitch_value, low=48, high=84)
                    cv2.putText(image_bgr, f"PITCH: {note}", (x_pixel - 20, y_pixel - 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 0), 2)
                    
        # --- FEATURE 3: Relativer Distanz-Tracker ---
        if 'Left' in wrist_positions and 'Right' in wrist_positions:
            
            wrist_left = wrist_positions['Left']
            wrist_right = wrist_positions['Right']
            
            # 1. Distanz berechnen
            normalized_distance = self.calculate_distance(wrist_left, wrist_right)
            
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
            right_gesture = hand_gestures.get('Right', 'Unbestimmt')
            print("\n--- GESTENERKENNUNG DATEN ---")
            print(f"Distanz zwischen Händen: {normalized_distance:.3f}")
            print(f"Rechte Hand Y-Position: {wrist_positions['Right'].y:.3f}")
            print(f"Rechte Hand Geste: {right_gesture}")
            print(f"Linke Hand Geste: {left_gesture}")
            print("-------------------------------")

        # Gebe das annotierte Bild zurück
        return image_bgr
            
           
           

