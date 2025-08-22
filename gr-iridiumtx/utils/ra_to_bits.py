# Transform RA message to bitstream for transmission

# Ring Alert message format: (63 bits minimum header info)
# Name              |    Length (bits) | 	Description
# Unique word	         24	                Always downlink 
#                                           Everything underneath is scrambled data
# Satelline number	     7	
# Beam id	             6	
# Pos x	                 12	
# Pos y	                 12	
# Pos z	                 12	
# Interval	             7	                90ms interval of RA 
# Time slot	             1	                Broadcast slot 1 or 4
# EPI	                 1	                ???
# BC sb	                 5	                BCH downlink sub-band
# Additional info	    >42	                Different TMSI and other info to be sent

# example:
# sat:087 beam:21 xyz=(+1428,-0002,+1076) pos=(+37.00/-000.08) alt=797 RAI:48 ?10 bc_sb:20 P00: {OK}


import re
import sys
from iridium_message import IridiumMessage

class IRAMessage(IridiumMessage):
    fill = 0
    descramble_extra_bits = ""
    def __init__(self, line):
        self.type = "IRA"
        self.direction = "DL"
        self.line = line
        self.parse_phy(line)
        ra = self.parse(line)

        # Construct the bitstream
        for key in ra:
            self.bitstream += ra[key]
        
        self.encode()
    
        # Fill pattern?? : 1010001001110011101111110110110101010100010001011100001011100110
        self.fill_pattern()

        # Interleave 3 only the first 96 bits (first block)
        self.scramble3(once=True)

        # Rest interleave 2
        self.scramble2(begin_at=96)

        self.bitstream = self.interleaved + self.descramble_extra_bits

    def fill_pattern(self):
        for _ in range(self.fill):
            self.bitstream_bch += "1010001001110011101111110110110101010100010001011100001011100110"



    # Parse the Ring alert message
    def parse(self, line):
        pattern = re.compile(
            r"IRA: .* sat:(\d+) beam:(\d+) xyz=\(\+?(-?\d+),\+?(-?\d+),\+?(-?\d+)\) "
            r"pos=\(\+?(-?\d+\.\d+)\/.?(\d+\.\d+)\) alt=(.?\d+) RAI:(\d+) \?(\d{1})(\d{1}) bc_sb:(\d+) (.*)"
        )
        match = pattern.match(line)
        if not match: 
             print(line)
             raise ValueError("Line does not match the expected format")

        x = int(match.group(3))
        y = int(match.group(4))
        z = int(match.group(5))
        
        
        if match.group(1).lstrip('0') == '':
            sat_n = 0
        else:
            sat_n = int(match.group(1).lstrip('0'))

        line_json = {
                "satellite_number": format(int(sat_n), '07b'),
                "beam_id": format(int(match.group(2)), '06b'),
                "pos_x": format((1 << 12) + x if x < 0 else x, '012b'),
                "pos_y": format((1 << 12) + y if y < 0 else y, '012b'),
                "pos_z": format((1 << 12) + z if z < 0 else z, '012b'),
                "RAI": format(int(match.group(9)), '07b'),
                "slot": format(int(match.group(10)), '01b'),
                "epi": format( int(match.group(11)), '01b'), # not sure what this is
                "bc_sb": format(int(match.group(12)), '05b'),
                # "status": match.group(12)
            }
        
        additional_info = match.group(13)
        
        # TMSI
        tmsi_pattern = re.compile(r"tmsi:(\w{8}) msc_id:(\d+)")
        pages = tmsi_pattern.findall(additional_info)
        for i, match in enumerate(pages):
            line_json.update({
                f"page_tmsi_{i}": format(int(match[0], 16), '032b'),
                f"page_zero1_{i}": format(0, '02b'),
                f"page_msc_id{i}": format(int(match[1]), '05b'),
                f"page_zero2{i}": format(0, '03b'),
            })
        
        tmsi_pattern = re.compile(r"tmsi:(\w{8}) 0:(\d+) msc_id:(\d+) 0:(\d+)")
        pages = tmsi_pattern.findall(additional_info)
        for i, match in enumerate(pages):
            line_json.update({
                f"page_tmsi_{i}": format(int(match[0], 16), '032b'),
                f"page_zero1_{i}": format(int(match[1]), '02b'),
                f"page_msc_id{i}": format(int(match[2]), '05b'),
                f"page_zero2{i}": format(int(match[3]), '03b'),
            })


        # Fill 
        fill_pattern = re.compile(r"FILL=(\d+)")
        fill = fill_pattern.search(additional_info)
        if fill:
            self.fill = int(fill.group(1))

        line_json.update({
            "end_pages": "1"*42,
        })

        # Extra bits
        extra_bits = re.compile(r"\+(\d+)")
        extra_bits = extra_bits.search(additional_info)

        if extra_bits:
            line_json.update({
                "extra_bits": extra_bits.group(1),
            })

        # Descramble extra
        descramble = re.compile(r"descr_extra:(\d+)")
        descramble_extra = descramble.search(additional_info)
        if descramble_extra:
            self.descramble_extra_bits = descramble_extra.group(1)

        return line_json
    


if __name__ == "__main__":
    ra = IRAMessage(sys.argv[1])
    print(ra.pretty())
  