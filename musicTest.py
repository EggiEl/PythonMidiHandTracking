import rtmidi
import time
import threading
import sys

midiout = rtmidi.MidiOut()
available_ports = midiout.get_ports()
# Finde deinen LoopMIDI-Port (der Name muss exakt sein)
port_name = "loopMIDI Port 1"  # Ersetze dies mit dem tatsächlichen Namen deines Ports
port_index = -1

# Shared pitch state (thread-safe-ish for integers)
pitch_lock = threading.Lock()
pitch = 60

def find_port_index():
    for i, name in enumerate(available_ports):
        if port_name in name:
            return i
    return -1


def midi_sender_loop(stop_event: threading.Event, note_length: float = 2.0):
    """Sendet fortlaufend Note On/Off messages. Pitch kann während des Spielens geändert werden."""
    global pitch
    idx = find_port_index()
    if idx == -1:
        print(f"Port '{port_name}' nicht gefunden. Verfügbare Ports:")
        for p in available_ports:
            print('  ', p)
        return

    try:
        midiout.open_port(idx)
    except Exception as e:
        print('Konnte Port nicht öffnen:', e)
        return

    try:
        while not stop_event.is_set():
            with pitch_lock:
                p = int(pitch)

            note_on = [0x90, p, 100]
            note_off = [0x80, p, 0]

            print(f"Sende Note {p} an Port {port_name}...")
            midiout.send_message(note_on)
            # Während die Note gehalten wird, können andere Threads pitch ändern
            elapsed = 0.0
            step = 0.05
            while elapsed < note_length and not stop_event.is_set():
                time.sleep(step)
                elapsed += step
            midiout.send_message(note_off)
            print("Note Off gesendet.")
            # Kurze Pause zwischen Noten
            time.sleep(0.1)
    finally:
        try:
            midiout.close_port()
        except Exception:
            pass


def input_loop(stop_event: threading.Event):
    """Liest Benutzer-Eingaben von der Konsole, um Pitch zu verändern.

    Befehle:
      - ganze Zahl: setze MIDI-Note (z.B. 60)
      - +    : erhöhe Pitch um 1
      - -    : verringere Pitch um 1
      - q    : beenden
    """
    global pitch
    print("Live-Pitch-Steuerung: Tippe eine Zahl, '+' oder '-' und Enter. 'q' zum Beenden.")
    while not stop_event.is_set():
        try:
            line = sys.stdin.readline()
            if not line:
                # EOF
                stop_event.set()
                break
            cmd = line.strip()
            if cmd == 'q':
                stop_event.set()
                break
            elif cmd == '+':
                with pitch_lock:
                    pitch += 1
                print('Pitch erhöht ->', pitch)
            elif cmd == '-':
                with pitch_lock:
                    pitch -= 1
                print('Pitch verringert ->', pitch)
            else:
                # try to parse a number
                try:
                    new_p = int(cmd)
                    if 0 <= new_p <= 127:
                        with pitch_lock:
                            pitch = new_p
                        print('Pitch gesetzt ->', pitch)
                    else:
                        print('Bitte eine Zahl zwischen 0 und 127 eingeben.')
                except ValueError:
                    print("Unbekannter Befehl. '+' '-' Zahl oder 'q' erwartet.")
        except Exception as e:
            print('Fehler bei Eingabe:', e)
            stop_event.set()
            break


if __name__ == '__main__':
    stop_event = threading.Event()

    sender_thread = threading.Thread(target=midi_sender_loop, args=(stop_event, 2.0), daemon=True)
    sender_thread.start()

    try:
        input_loop(stop_event)
    except KeyboardInterrupt:
        stop_event.set()

    sender_thread.join()
    print('Programm beendet.')