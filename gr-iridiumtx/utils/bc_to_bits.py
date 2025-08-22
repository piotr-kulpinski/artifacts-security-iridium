# Transform BC message to bitstream for transmission

# ### IBC: Broadcast

#     IBC: [...] bc:0 sat:028 cell:32 0 slot:0 sv_blkn:0 aq_cl:1111111111111111 aq_sb:22 aq_ch:2 00 0000 tmsi_expiry:2020-06-25T14:18:30.44Z [0 Rid:119 ts:1 ul_sb:22 dl_sb:22 access:3 dtoa:001 dfoa:00 00] []
#     IBC: [...] bc:0 sat:028 cell:24 0 slot:0 sv_blkn:0 aq_cl:1111111111111111 aq_sb:19 aq_ch:2 00 0000 time:2022-01-04T23:00:48.89Z [] []
#     IBC: [...] bc:0 sat:028 cell:24 0 slot:0 sv_blkn:0 aq_cl:1111111111111111 aq_sb:19 aq_ch:2 00 101010110001111001000111110000 max_uplink_pwr:20 [] []

# IBC can optionally have one of three information sets followed by channel assignments

# Broadcast message formats: 
# Name              |    Length (bits) | 	Description
##### BC TYPE 0
#### First block:
# Satellite number	     7	
# Beam id	             6	
# Unknown	             1	
# Time Slot              1
# Satellite blocking     1	
# Acquisition Classes	 16	
# Acquisition Subband	 5	                 
# Acquisition Channels   3	                
# Unknown	             2	                
#
### Second block:
# Message Type	         6	                BCH downlink sub-band
## MSG TYPE 0
# Unknown                30
# Max Uplink Power       6
## MSG TYPE 1
# Unknown                4
# Time                   32                 L-Band Frame Counter, 90ms granularity
## MSG TYPE 2
# Unknown                4
# TMSI Expiry            32                 Time of expiry of TMSI
## MSG TYPE UNKNOWN
# Type data              42

##### Rest of the blocks or any other BC type
# Assigment Type         3
## Assignment Type 0
# Random ID              8
# Time Slot              2                  +1 to map to 1-4 
# Uplink Subband         5
# Downlink Subband       5
# Frequency Access       3                  +1 to map to 1-4
# DTOA                   8                  Delta Time of Arrival [signed]
# DFOA                   6                  Delta Frequency of Arrival
# Unknown                2
## Assignment 


# Column|Content|Example|Comment
# --:|-|-|-
# 8||bc:0|
# 9|satellite id|sat:028|same 7-bit-id as in `IRA`
# 10|cell id|cell:32|a.k.a. spot beam number
# 11|unknown|0|1 bit
# 12|slot|slot:0|1 bit
# 13|sv_blocking|sv_blkn:0|1 bit
# 14|acquisition classes|aq_cl:1111111111111111|bitfield
# 15|acquisition subband|aq_sb:19|
# 16|acquisition channel|aq_ch:2|
# 17|unknown02|00|2 bits

# #### variant 1:

# Column|Example|Comment
# --:|-|-
# 18|0000|
# 19|tmsi_expiry:2020-06-25T14:18:30.44Z|seems to be mostly constant

# #### variant 2:

# Column|Example|Comment
# --:|-|-
# 18|0000|
# 19|time:2022-01-04T23:00:48.89Z|L-Band Frame Counter, 90ms granularity

# #### variant 3:

# Column|Example|Comment
# --:|-|-
# 18|101010110001111001000111110000|unknown
# 19|max_uplink_pwr:20|seems to be constant

# #### Channel Assigments
#     [0 Rid:119 ts:1 ul_sb:22 dl_sb:22 access:3 dtoa:001 dfoa:00 00]
#   The channel assignment are sent in response to `IAQ` requests from a mobile terminal and assign a frequency & timeslot for further communication.

# Content|Example|Comment
# -|-|-
# type|0|0-7
# random id|Rid:119|matches rid from `IAQ` packet
# timeslot|ts:1|1-4
# uplink subband|ul_sb:22|
# downlink subband|dl_sb:22|
# frequency_access|access:3|
# delta time of arrival|dtoa:+005|signed
# delta frequency of arrival|dfoa:00|signed
# unknown|00|2 bits|

# Notes:
# 1. Type 7 is likely used for iridium "next generation" devices and currently not understood.

import re
import sys
from iridium_message import IridiumMessage
import json


class IBCMessage(IridiumMessage):
    def __init__(self, line):
        self.type = "IBC"
        self.line = line
        self.parse_phy(line)
        bc = self.parse(line)

        if bc is None:
            return
        # Construct the bitstream
        for key in bc:
            self.bitstream += bc[key]
        
        self.encode()
        self.scramble2()

        # Add bc header
        header_bits = self.bch_encode(0,29)
        header_bits = format(header_bits, '06b')

        self.bitstream = header_bits + self.interleaved

    # Parse the Broadcast message
    def parse(self, line):
        pattern = re.compile(
            r"IBC: .* bc:(\d+) sat:(\d{3}) cell:(\d{2}) (\d) slot:(\d) sv_blkn:(\d) "
            r"aq_cl:(\d{16}) aq_sb:(\d{2}) aq_ch:(\d+) (\d{2})"
            r"(.*)"
        )
        match = pattern.match(line)
        other_line = False
        if not match:
            p2 = re.compile(
                r"IBC: .* bc:(\d+) (.*)"
            )
            if p2.match(line):
                other_line = True
            else:
                print(line)
                raise ValueError("Line does not match the expected format")
        if other_line:
            line_json = {}
            additional_info = p2.match(line).group(2).strip(" ")
        else:
            line_json = {        
            #"bc":                              int(match.group(1)), # not used
            "satellite_number":         format(int(match.group(2)), '07b'),
            "beam_id":                  format(int(match.group(3)), '06b'),
            "unknown01":                format(int(match.group(4)), '01b'),
            "slot":                     format(int(match.group(5)), '01b'),
            "sv_blocking":              format(int(match.group(6)), '01b'),
            "acquisition_classes":          str(int(match.group(7))), # 16 bits
            "acquisition_subband":      format(int(match.group(8)), '05b'),
            "acquisition_channel":      format(int(match.group(9)), '03b'),
            "unknown02":                format(int(match.group(10)), '02b'),
            }
        


            additional_info = match.group(11).strip(" ")

        # Time
        time_pattern = re.compile(r"(\d{4}) time:(\S+)")
        additional_match = time_pattern.match(additional_info)
        if additional_match:
            line_json.update({
                "type":                 format(1, '06b'),
                "unknown03":            format(int(additional_match.group(1)), '04b'),
                "time":                 format(self.str_time_to_iritime(additional_match.group(2)), '032b'),
            })

        # TMSI expiry
        tmsi_pattern = re.compile(r"(\d{4}) tmsi_expiry:(\S+)")
        additional_match = tmsi_pattern.match(additional_info)
        if additional_match:
            line_json.update({
                "type":                 format(2, '06b'),
                "unknown03":            format(int(additional_match.group(1)), '04b'),
                "tmsi_expiry":          format(self.str_time_to_iritime(additional_match.group(2)), '032b'),
            })
        
        # Uplink power
        uplink_power = re.compile(r"(\d{30}) max_uplink_pwr:(\d+)")
        additional_match = uplink_power.match(additional_info)
        if additional_match:
            line_json.update({
                "type":                 format(0, '06b'),
                "unknown03":            additional_match.group(1),
                "max_uplink_pwr":       format(int(additional_match.group(2)), '06b'),
            })

        # Unknown assignments
        assignments = re.compile(r"\[(\d+) (\d+)\]")
        assignments = assignments.findall(additional_info)
        for i, match in enumerate(assignments):
            line_json.update({
                f"assignment_type_unknown_{i}": format(int(match[0]), '03b'),
                f"assignment_unknown_{i}": match[1],
            })

        # Classic assignment
        assignments = re.compile(
            r"\[(\d{1}) Rid:(\d+) ts:(\d+) ul_sb:(\d+) dl_sb:(\d+) access:(\d+) dtoa:(\S+) dfoa:(\d+) (\d{2})\]"
        )
        assignments = assignments.findall(additional_info)
        for i, match in enumerate(assignments):
            dtoa = int(match[6])
            if dtoa < 0:
                dtoa = 256 + dtoa
            line_json.update({
                f"assignment_type_{i}":         format(int(match[0]), '03b'),
                f"assignment_random_id_{i}":    format(int(match[1]), '08b'),
                f"assignment_timeslot_{i}":     format(int(match[2])-1, '02b'),
                f"assignment_ul_sb_{i}":        format(int(match[3]), '05b'),
                f"assignment_dl_sb_{i}":        format(int(match[4]), '05b'),
                f"assignment_access_{i}":       format(int(match[5])-1, '03b'),
                f"assignment_dtoa_{i}":         format(dtoa,'08b'),
                f"assignment_dfoa_{i}":         format(int(match[7]),'06b'),
                f"assignment_unknown4_{i}":     match[8],
            })
        
        return line_json


if __name__ == "__main__":
    bc = IBCMessage(sys.argv[1])
    print(bc.pretty())
