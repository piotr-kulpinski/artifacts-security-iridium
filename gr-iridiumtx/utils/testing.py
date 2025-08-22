# Extract lines from a bitstream file by timestamp
# For comparison with convert_to_bitstream.py output and original bitstream file


import re
from isy import ISYMessage
from ra_to_bits import IRAMessage
from bc_to_bits import IBCMessage

import argparse
import json
from termcolor import colored

# I36: p-1740870071-e000 000056983.0318 1623373444  97% -45.13|-102.92|26.58 179 DL LCW(3,T:maint,C:<silent>,000000000000000000000)   
def match_timestamp(orig, parsed):
    orig = orig.split()
    parsed = parsed.split()
    try:
        timestamp_orig = int(orig[1].split('-')[1])
        timestamp_parsed = int(parsed[1].split('-')[1])
    except (IndexError, ValueError):
        return False, ""

    if timestamp_orig != timestamp_parsed:
        return False, ""

    offset_orig = float(orig[2])
    offset_parsed = float(parsed[2])

    if offset_orig - offset_parsed > 0.01:
        return False, "orig"
    elif offset_parsed - offset_orig > 0.01:
        return False, "parsed"

    
    return True, ""



# input is a bitstream file and the parsed file
# output is a file with the statistics and the specific lines that were wrong and how many bits were different
def compare_bitstreams(original_file, parsed_file, frame_type="IRA", verbose=False):
    """
    Compare two bitstream files and report differences.
    
    :param original_file: Path to the original bitstream file.
    :param parsed_file: Path to the parsed bitstream file.
    :return: Dictionary with statistics and differences.
    """
    stats = {
        'differences': [],
        'total_lines': 0,
        'matched_lines': 0,
        'mismatched_lines': 0
    }
    
    with open(original_file, 'r') as orig_file, open(parsed_file, 'r') as parse_file:
        # Read lines from both files until one of them ends
        orig_line = orig_file.readline()
        parse_line = parse_file.readline()
        while True:
            if not orig_line or not parse_line:
                break
            
            res = match_timestamp(orig_line, parse_line)
            if res[0] is False and res[1] == "":
                parse_line = parse_file.readline() # get new line
                orig_line = orig_file.readline() # get new line
            elif  res[1] == "orig" or parse_line.startswith('ERR') or parse_line.startswith('LCW'):
                parse_line = parse_file.readline() # get new line
            elif res[1] == "parsed" or orig_line.startswith('ERR'):
                orig_line = orig_file.readline() # get new line
            elif res[0]:
                # Skip not 100% lines
                if orig_line.split()[6] != '100%' or parse_line.split()[4] != '100%':
                    parse_line = parse_file.readline()
                    orig_line = orig_file.readline()
                    continue
                msg = None
                if frame_type == "IRA":
                    if parse_line.startswith('IRA'):
                        msg = IRAMessage(parse_line)
                if frame_type == "ISY":
                    if parse_line.startswith('ISY'):
                        msg = ISYMessage(parse_line)
                if frame_type == "IBC":
                    if parse_line.startswith('IBC'):
                        msg = IBCMessage(parse_line)
                if msg is None or parse_line.startswith('I36'):
                    # orig_line = orig_file.readline()
                    parse_line = parse_file.readline()
                    continue
                if msg.get_bitstream() != '':
                    if verbose: print(f"parse line: {parse_line}")
            
                    stats['total_lines'] += 1
                    parse_line_bits = msg.get_full_bitstream()
                    orig_line_bits = orig_line.split()[9]

                    if parse_line_bits != orig_line_bits:
                        differences = {
                            'line_number': stats['total_lines'] + 1,
                            'original': orig_line.strip(),
                            'parsed': parse_line.strip(),
                            'original_bits': orig_line_bits,
                            'parsed_bits': parse_line_bits,
                            'len_original_bits': len(orig_line_bits),
                            'len_parsed_bits': len(parse_line_bits),
                            'total_bit_differences': sum(
                                1 for i in range(min(len(orig_line_bits), len(parse_line_bits)))
                                if orig_line_bits[i] != parse_line_bits[i]
                            ),
                            'bit_difference_indices': [
                                i for i in range(min(len(orig_line_bits), len(parse_line_bits)))
                                if orig_line_bits[i] != parse_line_bits[i]
                            ]
                        }
                        if differences['total_bit_differences'] > 5:
                            stats['differences'].append(differences)
                            stats['mismatched_lines'] += 1
                        
                    else:
                        stats['matched_lines'] += 1
                    orig_line = orig_file.readline()
                    parse_line = parse_file.readline()
                
            

    
    return stats

def pretty_print_differences(differences):
    """
    Pretty print the differences with colored bitstreams.

    :param differences: List of dictionaries containing differences.
    """

    for diff in differences:
        print(f"Line Number: {diff['line_number']}")
        print(f"Original: {diff['original']}")
        print(f"Parsed: {diff['parsed']}")
        print("Bitstream Comparison:")

        original_colored = ""
        parsed_colored = ""

        for i in range(max(len(diff['original_bits']), len(diff['parsed_bits']))):
            orig_bit = diff['original_bits'][i] if i < len(diff['original_bits']) else " "
            parsed_bit = diff['parsed_bits'][i] if i < len(diff['parsed_bits']) else " "

            if i in diff['bit_difference_indices']:
                original_colored += colored(orig_bit, 'red')
                parsed_colored += colored(parsed_bit, 'red')
            else:
                original_colored += orig_bit
                parsed_colored += parsed_bit

        print(f"  Original Bits: {original_colored}")
        print(f"  Parsed Bits:   {parsed_colored}")
        print(f"  Total Bit Differences: {diff['total_bit_differences']}")
        print("-" * 80)

def main():
    parser = argparse.ArgumentParser(description="Compare two bitstream files and report differences.")
    parser.add_argument("original_file", help="Path to the original bitstream file.")
    parser.add_argument("parsed_file", help="Path to the parsed bitstream file.")
    parser.add_argument("--frame_type", choices=["IRA", "ISY", "IBC"], default="IRA",
                        help="Type of frame to compare (default: IRA).")
    args = parser.parse_args()

    stats = compare_bitstreams(args.original_file, args.parsed_file, frame_type=args.frame_type, verbose=False)

    print("Comparison Statistics:")
    pretty_print_differences(stats['differences'])
    print(f"Total Lines: {stats['total_lines']}")
    print(f"Matched Lines: {stats['matched_lines']}")
    print(f"Mismatched Lines: {stats['mismatched_lines']}")


if __name__ == "__main__":
    main()