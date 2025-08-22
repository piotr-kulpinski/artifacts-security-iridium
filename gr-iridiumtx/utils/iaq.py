
### IAQ Acquisition 

# IAQ: p-1740052938-e000 000004418.6381 1621910016  97% -35.11|-103.27|22.36 028 UL 0000 Rid:156 CRC:OK descr_extra:0011


from iridium_message import IridiumMessage
import re

class IAQMessage(IridiumMessage):
    fill = 0
    descramble_extra_bits = ""

    def __init__(self, line):
        self.type = "IAQ"
        self.line = line
        self.parse_phy(line)
        iaq = self.parse(line)
        # Construct the bitstream
        for key in iaq:
            self.bitstream += iaq[key]

        

    # Parse the IAQ message
    def parse(self, line):
        pattern = r"IAQ: .* (\d{4}) Rid:(\d+) CRC:\w+ descr_extra:(\d+)"
        match = re.match(pattern, line)
        if not match:
            print(line)
            raise ValueError("Line does not match the expected format")

        line_json = {
            "first_bits": match.group(1),
            "rid": match.group(2),
            "descr_extra": match.group(3)
        }
        return line_json