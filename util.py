import numpy as np
from scipy.stats import entropy

# it needs at least 64 bytes to calculate entropy correctly
def calculate_entropy(data):
    """Calculate the entropy of a data string using scipy."""
    if not data or len(data) < 64:
        return None
    
    # Convert the data to an array of byte values
    byte_array = np.frombuffer(data, dtype=np.uint8)
    
    # Calculate the frequency of each byte value
    byte_frequencies = np.bincount(byte_array, minlength=256) / len(byte_array)
    
    # Calculate the entropy
    return entropy(byte_frequencies, base=2)

def is_hex_encrypted(hex_string):
    """Check if the hex string is likely to be encrypted based on entropy."""
    # Convert the hex string to raw bytes
    try:
        # Convert the hex string to raw bytes
        bytes_data = bytes.fromhex(hex_string)
    except ValueError:
        # If the hex string is invalid, return False
        print(f"Invalid hex string: {hex_string}")  
        print(f"len: {len(hex_string)}")
        return False
    # bytes_data = bytes.fromhex(hex_string)
    
    # Calculate the entropy of the bytes data
    entropy_value = calculate_entropy(bytes_data)
    if not entropy_value:
        return False
    
    # print(f"entropy: {entropy_value} - {hex_string}")

    # Arbitrary threshold for detecting high entropy (indicative of encryption)
    # Higher cause most of the data can be encoded or compressed which increases the entropy
    threshold = 7.0
    
    return entropy_value > threshold


# function taken from iridium-toolkit
# https://github.com/muccc/iridium-toolkit

# Everything below is (c) Sec & schneider and licensed under the 2-Clause BSD License
# Slightly editted to fit use case

base_freq=1616*(10**6)   # int
channel_width=1e7/(30*8) # 30 sub-bands with 8 "frequency accesses" each

# return index instead subband.access
def channelize_str(freq):
    fbase = freq-base_freq
    freq_chan = int(fbase / channel_width)
    sb = int(freq_chan/8)+1
    fa = (freq_chan % 8)+1
    sx = freq_chan-30*8+1
    foff = fbase%channel_width
    freq_off = foff-(channel_width/2)
    return freq_chan