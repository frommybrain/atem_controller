import rtmidi
import time
import asyncio
import signal
from PyATEMMax.ATEMMax import ATEMMax as PyATEM
from datetime import datetime

# Configuration
ATEM_4K_IP = "192.168.0.31"   # Your 4K ATEM IP
MAX_RECONNECT_ATTEMPTS = 3     # Maximum number of reconnection attempts
DEBUG = True                   # Enable detailed debug logging

atem = None
midi_inputs = []  # List to store multiple MIDI inputs

def debug_print(message):
    if DEBUG:
        print(f"[DEBUG] {message}")

async def set_program_input(atem, input_num):
    try:
        current_input = atem.programInput[0].videoSource
        debug_print(f"Current program input: {current_input}")
        
        debug_print(f"Attempting to set program to input {input_num}")
        atem.setProgramInputVideoSource(0, input_num)
        await asyncio.sleep(0.1)  # Small delay to allow the switcher to respond
        
        new_input = atem.programInput[0].videoSource
        debug_print(f"New program input: {new_input}")
        
        if str(new_input) == f"input{input_num}":
            print(f"Successfully switched to input {input_num}")
        else:
            print(f"Failed to switch to input {input_num}. Switcher reports input {new_input}")
    except Exception as e:
        print(f"Error setting input: {e}")
        print(f"Switcher state: connected={atem.connected}, model={atem.atemModel}")

def onConnectAttempt(params):
    debug_print(f"Trying to connect to switcher at {params['switcher'].ip}")

def onConnect(params):
    print(f"Connected to switcher at {params['switcher'].ip}")

def onDisconnect(params):
    print(f"DISCONNECTED from switcher at {params['switcher'].ip}")

def log_midi_event(message, time_stamp, port_name="Unknown"):
    # Handle message if it's a list/array
    if isinstance(message[0], list):
        status_byte = message[0][0]
        note = message[0][1] if len(message[0]) > 1 else None
        velocity = message[0][2] if len(message[0]) > 2 else None
    else:
        status_byte = message[0]
        note = message[1] if len(message) > 1 else None
        velocity = message[2] if len(message) > 2 else None
    
    status_type = "Unknown"
    if status_byte in [144, 153]:  # Note On messages (channel 1 and 10)
        status_type = "Note On" if velocity > 0 else "Note Off"
    elif status_byte in [128, 137]:  # Note Off messages (channel 1 and 10)
        status_type = "Note Off"
    
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"\n[MIDI EVENT] {timestamp} on {port_name}")
    print(f"Status: {status_type} (byte: {status_byte})")
    print(f"Note: {note}")
    print(f"Velocity: {velocity}")
    print("-" * 40)

async def midi_callback(queue):
    while True:
        message_data = await queue.get()
        if message_data is None:
            break

        midi_message, time_stamp, port_name = message_data
        
        # Log all MIDI events
        log_midi_event(midi_message, time_stamp, port_name)
        
        # Get the actual message data
        if isinstance(midi_message[0], list):
            midi_message = midi_message[0]
        
        # Modified to handle both status bytes 144/153 for Note On
        if midi_message[0] in [144, 153] and midi_message[2] > 0:  # Note On message with velocity > 0
            note = midi_message[1]
            print(f"Processing Note On: {note}")
            
            # Mapping padKontrol notes to programs
            if note == 40:  # E2
                print("Switching to Program 1")
                await set_program_input(atem, 1)
            elif note == 41:  # F2
                print("Switching to Program 2")
                await set_program_input(atem, 2)
            elif note == 42:  # F#2
                print("Switching to Program 3")
                await set_program_input(atem, 3)
            elif note == 43:  # G2
                print("Switching to Program 4")
                await set_program_input(atem, 4)
            elif note == 44:  # G#2
                print("Switching to Program 5")
                await set_program_input(atem, 5)
            elif note == 45:  # A2
                print("Switching to Program 6")
                await set_program_input(atem, 6)
            else:
                print(f"Unassigned Note: {note}")

def list_midi_ports():
    """List all available MIDI ports with detailed information"""
    temp_midi = rtmidi.MidiIn()
    ports = temp_midi.get_port_count()
    
    if ports == 0:
        print("No MIDI ports available!")
        return []
    
    print("\nAvailable MIDI ports:")
    print("--------------------")
    port_list = []
    for i in range(ports):
        port_name = temp_midi.get_port_name(i)
        print(f"Port {i}: {port_name}")
        port_list.append((i, port_name))
    print("--------------------")
    temp_midi.close_port()
    return port_list

async def setup_midi_inputs():
    global midi_inputs
    available_ports = list_midi_ports()
    
    if not available_ports:
        print("No MIDI ports found!")
        return False

    selected_ports = set()
    while True:
        try:
            port_input = input("\nSelect MIDI port number (or press Enter to finish): ").strip()
            
            if port_input == "":
                if not midi_inputs:
                    print("Please select at least one port.")
                    continue
                break
                
            port_num = int(port_input)
            if port_num in selected_ports:
                print("Port already selected. Choose a different port.")
                continue
                
            if 0 <= port_num < len(available_ports):
                new_midi_in = rtmidi.MidiIn()
                new_midi_in.open_port(port_num)
                port_name = available_ports[port_num][1]
                print(f"Opened MIDI port: {port_name}")
                midi_inputs.append((new_midi_in, port_name))
                selected_ports.add(port_num)
            else:
                print("Invalid port number. Please try again.")
        except ValueError:
            print("Please enter a valid number or press Enter to finish.")
    
    return True

async def test_atem_connection(ip):
    """Test ATEM connection and return diagnostic information"""
    import subprocess
    import platform
    
    print(f"\nTesting connection to ATEM at {ip}...")
    
    # Check if we can ping the ATEM
    ping_param = "-n" if platform.system().lower() == "windows" else "-c"
    try:
        output = subprocess.run(['ping', ping_param, '1', ip], 
                              capture_output=True, text=True, timeout=5)
        if output.returncode == 0:
            print(f"✓ Successfully pinged {ip}")
        else:
            print(f"✗ Could not ping {ip}")
    except subprocess.TimeoutExpired:
        print(f"✗ Ping timeout to {ip}")
    except Exception as e:
        print(f"✗ Error testing connection: {e}")

async def main():
    global atem
    queue = asyncio.Queue()

    try:
        # Set up multiple MIDI inputs
        if not await setup_midi_inputs():
            return

        # Test ATEM connection before attempting to connect
        await test_atem_connection(ATEM_4K_IP)

        # Initialize ATEM switcher
        atem = PyATEM()
        
        # Register events
        atem.registerEvent(atem.atem.events.connectAttempt, onConnectAttempt)
        atem.registerEvent(atem.atem.events.connect, onConnect)
        atem.registerEvent(atem.atem.events.disconnect, onDisconnect)

        print("\nConnecting to ATEM 4K...")
        connect_attempts = 0
        while connect_attempts < MAX_RECONNECT_ATTEMPTS:
            try:
                atem.connect(ATEM_4K_IP)
                await asyncio.sleep(2)
                if atem.connected:
                    print(f"Connected to ATEM 4K. Model: {atem.atemModel}")
                    print(f"Current program input: {atem.programInput[0].videoSource}")
                    print("\nAvailable inputs:")
                    for i in range(20):
                        if atem.inputProperties[i].longName:
                            print(f"Input {i}: {atem.inputProperties[i].longName}")
                    break
                connect_attempts += 1
            except Exception as e:
                print(f"Connection attempt {connect_attempts + 1} failed: {e}")
                connect_attempts += 1
                if connect_attempts < MAX_RECONNECT_ATTEMPTS:
                    print(f"Retrying in 2 seconds...")
                    await asyncio.sleep(2)

        if not atem.connected:
            print(f"\nFailed to connect to ATEM after {MAX_RECONNECT_ATTEMPTS} attempts.")
            print("Please check:")
            print(f"1. Is the ATEM powered on and accessible at {ATEM_4K_IP}?")
            print("2. Are you on the same network as the ATEM?")
            print("3. Is there a firewall blocking the connection?")
            return

        # Set up callbacks for all MIDI inputs
        def create_midi_callback_wrapper(port_name):
            def wrapper(message, time_stamp):
                queue.put_nowait((message, time_stamp, port_name))
            return wrapper

        for midi_in, port_name in midi_inputs:
            midi_in.set_callback(create_midi_callback_wrapper(port_name))

        print("\nWaiting for MIDI input... Press Ctrl+C to exit.")
        print("\nMIDI Note Mappings:")
        print("E2  (Note 40): Switch to Program 1")
        print("F2  (Note 41): Switch to Program 2")
        print("F#2 (Note 42): Switch to Program 3")
        print("G2  (Note 43): Switch to Program 4")
        print("G#2 (Note 44): Switch to Program 5")
        print("A2  (Note 45): Switch to Program 6")

        # Start the MIDI callback handler
        midi_task = asyncio.create_task(midi_callback(queue))

        # Keep the script running
        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass
        except KeyboardInterrupt:
            print("\nExiting...")

        # Stop the MIDI callback handler
        await queue.put(None)
        await midi_task

    finally:
        print("\nCleaning up...")
        for midi_in, _ in midi_inputs:
            midi_in.close_port()
        if atem is not None:
            atem.disconnect()
        print("Script ended")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass