from bc_to_bits import IBCMessage
from ra_to_bits import IRAMessage
from isy import ISYMessage
import sys


freqs = {}

def filter_iridium_messages(input_file, output_file):
    messages = []

    with open(input_file, 'r') as infile:
        for line in infile:
            msg = None
            if line.startswith('IRA'):
                msg = IRAMessage(line)
            if line.startswith('IBC'):
                msg = IBCMessage(line)
            if line.startswith('ISY'):
                msg = ISYMessage(line)
            if msg is None:
                continue
            if msg.get_bitstream() != '':
                messages.append(msg.pretty())
                freq = msg.get_frequency()
                freq = int(round(freq / 10000) * 10000)
                if freq in freqs:
                    freqs[freq] += 1
                else:
                    freqs[freq] = 1
                msg.get_all()[1]

    # messages = transform_offset(messages)
    # messages = filter_duplicates(messages)
    with open(output_file, 'w') as outfile:
        for message in messages:
            outfile.write(message + '\n')

def filter_duplicates(messages):
    last_freq = None
    last_timestamp = None
    last_bitstream_len = None
    filtered_messages = []

    for message in messages:
        split = message.split(' ')
        timestamp = float(split[1])
        frequency = int(split[2])
        
        if last_timestamp is None or last_timestamp is None:
            last_freq = frequency
            last_timestamp = timestamp
            last_bitstream_len = len(split[4])
            filtered_messages.append(message)
            continue
        
        frequency = int(round(frequency / 10000) * 10000)
        last_freq = int(round(last_freq / 10000) * 10000)

        # Make it more dumb for now to avoid duplicates at the same time
        if (timestamp - last_timestamp) < 0.005: # frequency == last_freq and
            if len(split[4]) > last_bitstream_len:
                filtered_messages[-1] = message
            last_freq = frequency
            last_timestamp = timestamp
            last_bitstream_len = len(split[4]) 
            continue
        
        last_freq = frequency
        last_timestamp = timestamp
        last_bitstream_len = len(split[4]) 
        filtered_messages.append(message)
    
    return filtered_messages

def transform_offset(data):
    first = data[0].split(' ')
    first_timestamp = float(first[1]) # this is in miliseconds
    for i,line in enumerate(data):
        split = line.split(' ')
        split[1] = str(round((float(split[1]) - first_timestamp) / 1000, 6) )
        line = ' '.join(split)
        data[i] = line
    return data
    

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python spoofing.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    filter_iridium_messages(input_file, output_file)
    # transform_offset(open(output_file, 'r').readlines())
    print(freqs)