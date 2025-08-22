import os, re
import argparse
# ITL: u-call.01-e000 000000426.3849 1626066176 100% -42.63|-104.10|29.88 432 DL V2 OK P1 R01 N05 1011111 0101100 1110100
# IU3: u-call.01-e020 000001917.5905 1621459456  65% -52.69|-103.57|21.12 179 DL LCW(3,T:maint,C:<silent>,000000000000000000000)                                                                 RS=no [10000000 10001000 00010101 00111110 10001101 00100110 00111010 00000111 11111111 01101111 00000111 11111111 11111111 00000111 10011111 11111111 00000111 11111111 11100111 00000111 11111111 11111111 00000111 11111111 11111111 00000111 11111101 10111111 00010011 11111111 11111111 00001111 01011001 10000011 01000111 10111011 10101110 00101001 01000011]


def make_buckets():
    """
    Create a dictionary to hold frequency buckets.
    Each bucket will hold messages with frequencies within a specified tolerance.
    """
    # The frequency range is between 16200000 and 16250000 Hz, with a each channel being 41667 Hz wide.
    buckets = {}
    for i in range(252):
        buckets[i] = {
            "min_frequency": int(1616000000 + i * 41666.667),
            "max_frequency": int(1616000000 + (i + 1) * 41666.667),
            "messages": []
        }
    return buckets


def process_line(line:str):
    # Extract frequency and other information using regex
    p = re.compile(r"([A-Z0-9]{3}):")
    m = p.match(line)
    if m:
        frame = m.group(1)
        # Remove simplex frames or unwanted lines
        if frame == "IRA" or frame == "ITL" or frame == "ERR" or frame == "NXT" or frame == "IMS":
            return None
        
        split = line.split()
        timestamp = float(split[2])
        frequency = int(split[3])
        p_lcw = re.compile(r"LCW\((\S+)\)")
        m = p_lcw.match(split[8])
        # print(split[8])
        control = ""
        if m:
            # LCW 
            control = m.group(1)
        rest = " ".join(split[4:])
        return {
            "type": frame,
            "frequency": frequency,
            "timestamp": timestamp,
            "control": control,
            "rest": rest,
        }

    else:
        return None

def parse_file(file, fixed_channel=False, frequency_tolerance=37500/2):
    buckets = make_buckets()
    
    # Read the file line by line
    with open(file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue  # Skip empty lines and comments
            
            data = process_line(line)
            if not data:
                continue  # Skip lines that do not match the expected format
            
            frequency = data["frequency"]
            max_freq = frequency + frequency_tolerance
            min_freq = frequency - frequency_tolerance
            
            if fixed_channel:
                # If fixed channel, assign to the bucket corresponding to the frequency
                bucket_index = int((frequency - 1616000000) // 41666.667)
                if bucket_index in buckets:
                    buckets[bucket_index]["messages"].append(data)
            else:
                # Find the appropriate bucket for the frequency
                max_index = int((max_freq - 1616000000) // 41666.667)
                min_index = int((min_freq - 1616000000) // 41666.667)
                for i in range(min_index, max_index + 1):
                    if i not in buckets:
                        continue
                    buckets[i]["messages"].append(data)
    return buckets

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Parse connection data.")
    parser.add_argument("filepath", type=str, help="Path to the data folder")
    args = parser.parse_args()

    filepath = args.filepath
    buckets = parse_file(filepath, True)

    # Print the buckets for verification
    for channel, meta in buckets.items():
        if not meta["messages"]:
            continue
        print(f"Subband {channel//8 + 1} Carrier {channel%8 + 1} Channel {channel + 1}:")
        for key, value in meta.items():
            if key == "messages":
                print(f"  Messages ({len(value)}):")
                for message in value:
                    print(f"    {message['type']} at {message['timestamp']} ms {message['control']}")
            else:
                print(f"  {key}: {value}")
    