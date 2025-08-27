

# This pipeline can get data from gr-iridium directly run it also over iridium-toolkit and process it 
# Additionally, it has use a window method to process the data in chunks and reconstruct into bigger packets into a bigger statistics
import subprocess
import argparse
import re
import util
import sqlite3
import sys
import select
from ber import calculate_ber
import numpy as np

BUFFER_SIZE = 1000  # Number of lines to buffer before processing

lcw_types = ["IIP", "IIQ", "IIU", "IIR", "IDA", "MSG", "VDA", "VO6", "VOC", "VOD", "MS3", "VOZ", "NXT"]
total_type_counts = {lcw_type: {"enc":0, "total": 0} for lcw_type in lcw_types}


all_types = {
        "total": 0,
        "IBC": 0,
        "IDA": 0,
        "IIP": 0,
        "IIQ": 0,
        "IIR": 0,
        "IIU": 0,
        "IMS": 0,
        "IRA": 0,
        "IRI": 0,
        "ISY": 0,
        "ITL": 0,
        "IU3": 0,
        "I36": 0,
        "I38": 0,
        "MSG": 0,
        "VDA": 0,
        "VO6": 0,
        "VOC": 0,
        "VOD": 0,
        "MS3": 0,
        "VOZ": 0,
        "IAQ": 0,
        "NXT": 0,
        "RAW": 0
    }

channel_map = [f"{i}.{j}" for i in range(1, 40) for j in range(1, 9)]

channels_buf = [[] for _ in channel_map]

GRANULARITY = 1000
prr_buf = np.array([0.0 for _ in range(0,GRANULARITY)])
prr_count_frames = np.array([0 for _ in range(0,GRANULARITY)])

def init_db():
    """
    Initializes the SQLite database for storing Iridium metadata.
    """
    conn = sqlite3.connect('iridium_metadata.db')
    cursor = conn.cursor()
    
    # Create a table for storing Iridium metadata
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS all_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            count INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS encryption_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT,
            enc INTEGER,
            total INTEGER
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS prr_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prr_sum REAL,
            count INTEGER
        )
    ''')

    # if data already exists take the data out of database
    cursor.execute('SELECT type, count FROM all_stats')
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            lcw_type, count = row
            if lcw_type in all_types:
                all_types[lcw_type] = count
            else:
                print(f"Unknown LCW type in database: {lcw_type}")
    else:
        # Initialize all_stats table with all LCW types
        for lcw_type in all_types.keys():
            cursor.execute('''
                INSERT INTO all_stats (type, count) VALUES (?, ?)
            ''', (lcw_type, 0))
    
    cursor.execute('SELECT type, enc, total FROM encryption_stats')
    rows = cursor.fetchall()
    if rows:
        for row in rows:
            lcw_type, enc, total = row
            if lcw_type in total_type_counts:
                total_type_counts[lcw_type] = {"enc": enc, "total": total}
            else:
                print(f"Unknown LCW type in encryption stats: {lcw_type}")
    else:
        # Initialize encryption_stats table with all LCW types
        for lcw_type in lcw_types:
            cursor.execute('''
                INSERT INTO encryption_stats (type, enc, total) VALUES (?, ?, ?)
            ''', (lcw_type, 0, 0))

    cursor.execute('SELECT prr_sum, count FROM prr_stats')
    rows = cursor.fetchall()
    if rows:
        for idx, row in enumerate(rows):
            prr_sum, count = row
            prr_buf[idx] = prr_sum
            prr_count_frames[idx] = count
    else:
        # Initialize prr_stats table
        for _ in range(GRANULARITY):
            cursor.execute('''
                INSERT INTO prr_stats (prr_sum, count) VALUES (?, ?)
            ''', (0.0, 0))
        
    conn.commit()
    conn.close()

def update_db():
    """
    Updates the SQLite database with the current statistics.
    """
    conn = sqlite3.connect('iridium_metadata.db')
    cursor = conn.cursor()
    
    # Update all_stats table
    for lcw_type, counts in all_types.items():
        cursor.execute('''
            UPDATE all_stats SET count = ? WHERE type = ?
        ''', (counts, lcw_type))

    # Update encryption_stats table
    for lcw_type, counts in total_type_counts.items():
        cursor.execute('''
            UPDATE encryption_stats
            SET enc = ?, total =  ?
            WHERE type = ?
        ''', (counts["enc"], counts["total"], lcw_type)) 

    # Update prr_stats table
    for idx in range(GRANULARITY):
        prr_val = prr_buf[idx]
        prr_count = prr_count_frames[idx]
        cursor.execute('''
            UPDATE prr_stats
            SET prr_sum = ?, count = ?
            WHERE id = ?
        ''', (float(prr_val), int(prr_count), idx + 1))
    

    conn.commit()
    conn.close()


def reconstruct_packets():
    global channels_buf
    reconstructed_data = []
    # Reconstructs a packet from the frames - given heuristic - same channel, at most 10 seconds apart, same frame type
    # Reconstruct messages from the buffered data
    for channel_buf in channels_buf:
        msg = {"type": "","data": ""}
        for idx, line in enumerate(channel_buf):
                
            if line["time"] > channel_buf[idx-1]["time"] + 10:
                # print(line["time"], channel_buf[idx-1]["time"])
                if msg["data"] and len(msg["data"]) > 256: #124:
                    reconstructed_data.append(msg)
                msg = {"type": "","data": ""}
                continue
            
            if line["data"] and (msg["type"] == "" or msg["type"] == line["type"]):
                msg["type"] = line["type"]
                msg["data"] += line["data"]
                # print(len(msg["data"]))

        if msg["data"] and len(msg["data"]) > 256: # 124:
            reconstructed_data.append(msg) 
    
    
    channels_buf = [[] for _ in channel_map]  # Clear the buffer for the next round
    
    # check if reconstructed data is encrypted
    for msg in reconstructed_data:
        if msg["type"] in total_type_counts:
            total_type_counts[msg["type"]]["total"] += 1
            if util.is_hex_encrypted(msg["data"]):
                total_type_counts[msg["type"]]["enc"] += 1
        else:
            print(f"Unknown message type: {msg['type']}")

    reconstructed_data.clear()  # Clear the reconstructed data for the next round

def process_line(line):
    """
    Processes a line of data, extracts frequency and timestamp, and groups it.
    """
    try:
        parts = line.strip().split()
        if len(parts) < 3:
            print(f"Skipping line due to insufficient parts: {line.strip()}")
            return
        
        frame_type = parts[0][:-1]

        if frame_type == "ERR":
            # Skip error lines
            return
        
        # Extract timestamp
        time = parts[1]
        if time.split("-")[1].isdigit():
            seconds = int(time.split("-")[1])
            offset = float(parts[2])/1000
            time = seconds + offset
        else: # fallback if the timestamp is not in expected format, and just use milisecond offset
            time = float(parts[2])/1000

        # Extract frequency and channel index
        freq = parts[3]
        idx = util.channelize_str(int(freq))
        if idx < 0 or idx >= len(channel_map) or idx is None:
            print(f"Invalid channel index: {idx} for frequency {freq}")
            return

        # Count the occurrences of each LCW type
        if frame_type in all_types:
            all_types[frame_type] += 1
            all_types["total"] += 1

        # Filter by type
        if frame_type not in lcw_types:
            return

        data = None
        
        if frame_type == "IIP" or frame_type == "IDA" or frame_type == "VOC" or frame_type == "VDA" or frame_type == "VOZ":
            data_match = re.search(r'\[([0-9a-fA-F.][0-9a-fA-F.]+)\]', line)
            if data_match:
                data = data_match.group(1)
                data = data.replace(".", "")
        elif frame_type == "IIQ" or frame_type == "IIR":
            data_match = re.search(r'\[([0-9a-fA-F][0-9a-fA-F]+)\]', line)
            if data_match:
                data = data_match.group(1)
                data = data.replace(" ", "")
        elif frame_type == "IIU" or frame_type == "VO6":
            data_match = re.search(r'\[([0-1]+)\]', line)
            if data_match:
                data = data_match.group(1)
                data = data.replace(" ", "")
                try:
                    data = hex(int(data, 2))[2:]
                except ValueError:
                    print(f"ValueError: {data}, line: {line}")
        elif frame_type == "MSG":
            data_match = re.search(r'msg:([0-9a-fA-F]+).', line)
            if data_match:
                data = data_match.group(1)
        elif frame_type == "NXT":
            data_match = re.search(r'\> ([0-1 ]+)', line)
            if data_match:
                data = data_match.group(1)
                data = data.replace(" ", "")
                try:
                    data = hex(int(data, 2))[2:]
                except ValueError:
                    # print(f"ValueError: {data}, line: {line}")
                    data = None        
        m = {
            "type": frame_type,
            "time": time,
            "channel": idx,
            "data": data
        }


        channels_buf[idx].append(m)

    except Exception as e:
        print(f"Error processing line: {e}")
        print(f"Line content: {line.strip()}")
        print(f"{line.strip()}\n")


def parse_by_line(lines):
    """
    Splits the input lines into chunks based on the LCW types.
    """
    try:
        lines = lines.strip().split('\n')
        for line in lines:
            if line.strip():
                process_line(line)

        reconstruct_packets()

    except Exception as e:
        print(f"Error splitting lines: {e}")
        return None

def get_prr(lines):
    try:
        # BER calculation
        # Calculate the packet reception rate per SNR index calculated per received frame
        for line in lines:
            res = calculate_ber(line)
            if res is not None:
                bit_errors, snr, noise, len_bits = res
                packet_reception_rate = np.power((1 - (bit_errors/len_bits)), len_bits)
                prr_id = int(round(float(snr), 1) * 10)
                prr_buf[prr_id] += packet_reception_rate
                prr_count_frames[prr_id] += 1
    except Exception as e:
        print(f"An error occurred while calculating PRR: {e}")
        return None


def parse_iridium_traffic(lines:str, debug=False):
    try:
        iridium_parser = subprocess.Popen(
            ["iridium-parser.py" , "--harder", "--uw-ec"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if debug: print("iridium-parser PID: ", iridium_parser.pid)
        stdout, stderr = iridium_parser.communicate(input=lines)

        if stderr and "Warning" in stderr:
                if debug: print("Warning from iridium-toolkit:", stderr.strip())
        elif stderr:
            print("Error from iridium-toolkit:", stderr.strip())
            return None 
        output_lines = stdout.strip()
        if not output_lines:
            print("No output received from iridium-toolkit.")
            return None
        if iridium_parser.returncode != 0:
            print(f"Error parsing with iridium-toolkit: {output_lines.strip()}")
            return None
        
        parse_by_line(output_lines)

    except FileNotFoundError:
        print("iridium-toolkit is not installed or not in PATH.")
        return None
    except Exception as e:
        print(f"An error occurred while parsing: {e}")
        return None

def run_data_collection(config_path=None, sigmf_file=None, debug=False):
    try:
        if config_path != None:
            # Start gr-iridium and pipe its output to this script
            print("testing gr-iridium with config path:", config_path)
            process = subprocess.Popen(
                ["iridium-extractor", "-D", "4", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )  
        elif sigmf_file != None:
            process = subprocess.Popen(
                ["iridium-extractor","-D", "4", sigmf_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        else:
            print("Please provide a config path or a SigMF file for processing.")
            return
        
        print("Input q to quit the process")
        
        buffer = []
        if debug:
            print("gr-iridium PID: ", process.pid)

        for line in process.stdout:
            # Add line to buffer and increment line count
            buffer.append(line.strip())

            # Check for 'q' key press to quit
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                user_input = sys.stdin.read(1)
                if user_input.lower() == 'q':
                    print("User requested to quit. Exiting loop...")
                    process.terminate()
                    break  # Process the buffer when it reaches BUFFER_SIZE lines

            if len(buffer) >= BUFFER_SIZE:
                print(f"Processing {BUFFER_SIZE} buffered lines...")
                lines = '\n'.join(buffer)
                parse_iridium_traffic(lines, debug=debug)
                get_prr(buffer)

                # Clear the buffer and reset line count
                buffer.clear()
                update_db()  # Update the database with current statistics
        

        
        # Process any remaining lines in the buffer
        lines = '\n'.join(buffer)
        print(f"Processing remaining {len(buffer)} lines...")
        parse_iridium_traffic(lines, debug=debug)
        get_prr(buffer)
        # Clear the buffer and reset line count
        buffer.clear()
        update_db()  # Final update to the database

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    print("Starting Iridium data processing pipeline...")
    init_db()  # Initialize the database

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Process Iridium data using gr-iridium and iridium-toolkit.")
    parser.add_argument("--config", type=str, help="Path to the gr-iridium configuration file.")
    parser.add_argument("--sigmf", type=str, help="Path to the SigMF file for offline processing.")
    args = parser.parse_args()

    # Pass arguments to run_data_collection
    run_data_collection(config_path=args.config, sigmf_file=args.sigmf, debug=False)
    print(total_type_counts)
    print(all_types)
    print(prr_count_frames)