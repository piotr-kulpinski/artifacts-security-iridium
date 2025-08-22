# Transform ISY message to bitstream for transmission

### ISY
#Contain a constant bit pattern, used mainly to transmit info via the LCW


# Ring Alert message format: (63 bits minimum header info)
# Name              |    Length (bits) | 	Description
# Unique word	         24	                Always downlink 
#                                           Everything underneath is scrambled data
# LCW
# ISY message format: (minimum 96 bits)

# example:
# LCW(7,T:acchl,C:acchl[msg_type:1,bloc_num:0,sapi_code:0,segm_list:00111111],0,00) Sync=OK
# LCW(7,T:maint,C:maint[1][lqi:3,power:0],0000000000000000) Sync=OK pattern=10


import re
import sys
from iridium_message import IridiumMessage

class ISYMessage(IridiumMessage):
    fill = 0
    descramble_extra_bits = ""
    def __init__(self, line):
        self.type = "ISY"
        self.line = line
        self.parse_phy(line)
        lcw_bits = self.parse_lcw(line)
        isy = self.parse(line)
        # Construct the bitstream

        for key in isy:
            self.bitstream += isy[key]

        # print("LCW bits: ", len(lcw_bits))
        # print("Bitstream before LCW: ", len(self.bitstream))

        self.bitstream = lcw_bits + self.bitstream

    # Parse the Ring alert message
    def parse(self, line):
        if self.direction == "DL":
            pattern = '01'
        if self.direction == "UL":
            p = re.compile(
                r"ISY: .* pattern=(\d+)"
            )
            match = p.match(line)
            if not match: 
                print(line)
                raise ValueError("Line does not match the expected format")
            pattern = match.group(1)
        pattern_bitstream = ''
        for _ in range(int(312/2)):
            pattern_bitstream += pattern
        line_json = {
            "pattern": pattern_bitstream,
        }
        return line_json
    


if __name__ == "__main__":
    isy = ISYMessage(sys.argv[1])
    print(isy.pretty())
  