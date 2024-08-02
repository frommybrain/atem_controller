import rtmidi
import time
import asyncio
import signal
from PyATEMMax.ATEMMax import ATEMMax as PyATEM

# ATEM switcher IP addresses
ATEM_HD_IP = "192.168.0.245"  # Your HD ATEM IP
ATEM_4K_IP = "192.168.0.31"   # Your 4K ATEM IP

midi_in = None
atem_hd = None
atem_4k = None

async def set_program_input(atem, input_num):
    try:
        if atem.atemModel == "ATEM 1 M/E Production Studio 4K":
            current_input = atem.auxSource[0]
            print(f"Current Aux 1 input: {current_input}")
            
            print(f"Attempting to set Aux 1 to input {input_num}")
            atem.setAuxSourceInput(0, input_num)
            await asyncio.sleep(0.1)  # Small delay to allow the switcher to respond
            
            new_input = atem.auxSource[0]
            print(f"New Aux 1 input: {new_input}")
            
            if new_input == input_num:
                print(f"Successfully switched Aux 1 to input {input_num}")
            else:
                print(f"Failed to switch Aux 1 to input {input_num}. Switcher reports input {new_input}")
        else:
            current_input = atem.programInput[0].videoSource
            print(f"Current program input: {current_input}")
            
            print(f"Attempting to set program to input {input_num}")
            atem.setProgramInputVideoSource(0, input_num)
            await asyncio.sleep(0.1)  # Small delay to allow the switcher to respond
            
            new_input = atem.programInput[0].videoSource
            print(f"New program input: {new_input}")
            
            if str(new_input) == f"input{input_num}":
                print(f"Successfully switched to input {input_num}")
            else:
                print(f"Failed to switch to input {input_num}. Switcher reports input {new_input}")
    except asyncio.CancelledError:
        pass  # Handle cancellation gracefully
    except Exception as e:
        print(f"Error setting input: {e}")
        print(f"Switcher state: connected={atem.connected}, model={atem.atemModel}")

def onConnectAttempt(params):
    print(f"Trying to connect to switcher at {params['switcher'].ip}")

def onConnect(params):
    print(f"Connected to switcher at {params['switcher'].ip}")

def onDisconnect(params):
    print(f"DISCONNECTED from switcher at {params['switcher'].ip}")

def onReceive(params):
    # Filter out frequent messages
    if params['cmd'] not in ['Time', 'RXMS']:
        print(f"Received [{params['cmd']}]: {params['cmdName']}")

async def midi_callback(queue):
    while True:
        message, time_stamp = await queue.get()
        if message is None:
            break

        midi_message, delta_time = message
        if midi_message[0] == 144 and midi_message[2] > 0:  # Note On message with velocity > 0
            note = midi_message[1]
            print(f"\nReceived Note On: {note}")
            if note == 25:
                print("Scenario 1: 4K ATEM to Program 1, HD ATEM to NDI input (4)")
                await asyncio.gather(
                    set_program_input(atem_4k, 1),
                    set_program_input(atem_hd, 4)
                )
            elif note == 27:
                print("Scenario 2: 4K ATEM to Program 2, HD ATEM to NDI input (4)")
                await asyncio.gather(
                    set_program_input(atem_4k, 2),
                    set_program_input(atem_hd, 4)
                )
            elif note == 29:
                print("Scenario 3: 4K ATEM to Program 2, HD ATEM to input 1")
                await asyncio.gather(
                    set_program_input(atem_4k, 2),
                    set_program_input(atem_hd, 1)
                )
            elif note == 30:
                print("Scenario 4: 4K ATEM to Program 2, HD ATEM to input 2")
                await asyncio.gather(
                    set_program_input(atem_4k, 2),
                    set_program_input(atem_hd, 2)
                )
            elif note == 32:
                print("Scenario 5: 4K ATEM to Program 2, HD ATEM to input 3")
                await asyncio.gather(
                    set_program_input(atem_4k, 2),
                    set_program_input(atem_hd, 3)
                )
            else:
                print("Unassigned Note")

async def main():
    global midi_in, atem_hd, atem_4k

    queue = asyncio.Queue()

    try:
        # Initialize MIDI input
        midi_in = rtmidi.MidiIn()
        available_ports = midi_in.get_ports()

        # Print available ports
        print("Available MIDI ports:")
        for i, port in enumerate(available_ports):
            print(f"{i}: {port}")

        # Let user select a port
        if available_ports:
            while True:
                try:
                    port_num = int(input("Select MIDI port number: "))
                    midi_in.open_port(port_num)
                    print(f"Opened MIDI port: {available_ports[port_num]}")
                    break
                except rtmidi.SystemError as e:
                    print(f"Error opening port {port_num}: {e}")
                    print("Please try another port.")
                except ValueError:
                    print("Please enter a valid number.")
        else:
            print("No MIDI ports available. Opening virtual port.")
            midi_in.open_virtual_port("My virtual input")

        # Initialize ATEM switchers
        atem_hd = PyATEM()
        atem_4k = PyATEM()

        # Register events
        for atem in [atem_hd, atem_4k]:
            atem.registerEvent(atem.atem.events.connectAttempt, onConnectAttempt)
            atem.registerEvent(atem.atem.events.connect, onConnect)
            atem.registerEvent(atem.atem.events.disconnect, onDisconnect)
            atem.registerEvent(atem.atem.events.receive, onReceive)

        print("Connecting to ATEM HD...")
        atem_hd.connect(ATEM_HD_IP)

        print("Connecting to ATEM 4K...")
        atem_4k.connect(ATEM_4K_IP)

        # Wait for connections to establish
        await asyncio.sleep(2)

        if atem_hd.connected:
            print(f"Connected to ATEM HD. Model: {atem_hd.atemModel}")
            print(f"Current program input: {atem_hd.programInput[0].videoSource}")
        else:
            print("Failed to connect to ATEM HD")

        if atem_4k.connected:
            print(f"Connected to ATEM 4K. Model: {atem_4k.atemModel}")
            print(f"Current Aux 1 input: {atem_4k.auxSource[0]}")
            print("Available inputs on 4K ATEM:")
            for i in range(20):
                if atem_4k.inputProperties[i].longName:
                    print(f"Input {i}: {atem_4k.inputProperties[i].longName}")
        else:
            print("Failed to connect to ATEM 4K")

        def midi_callback_wrapper(message, time_stamp):
            queue.put_nowait((message, time_stamp))

        midi_in.set_callback(midi_callback_wrapper)

        print("\nWaiting for MIDI input... Press Ctrl+C to exit.")

        # Start the MIDI callback handler
        midi_task = asyncio.create_task(midi_callback(queue))

        # Keep the script running
        try:
            while True:
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            pass  # Handle cancellation gracefully
        except KeyboardInterrupt:
            print("\nExiting...")

        # Stop the MIDI callback handler
        await queue.put((None, None))
        await midi_task

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        print("Cleaning up...")
        if midi_in is not None:
            midi_in.close_port()
        if atem_hd is not None:
            atem_hd.disconnect()
        if atem_4k is not None:
            atem_4k.disconnect()
        print("Script ended")

def shutdown(loop):
    tasks = asyncio.all_tasks(loop=loop)
    for task in tasks:
        task.cancel()
    loop.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    signal.signal(signal.SIGINT, lambda s, f: shutdown(loop))
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()