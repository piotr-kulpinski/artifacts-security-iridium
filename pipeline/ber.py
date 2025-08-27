# Taken from:
# https://github.com/muccc/iridium-toolkit

# Everything here is (c) Sec & schneider and licensed under the 2-Clause BSD License
# Slightly editted to fit use case


from bch import ndivide, nrepair, bch_repair, bch_repair1
import re

iridium_access="001100000011000011110011" # Actually 0x789h in BPSK
uplink_access= "110011000011110011111100" # BPSK: 0xc4b
next_access_dl = "110011110011111111111100" # 0xdab
next_access_ul = "001111000000000011111111" # 0x40a
UW_DOWNLINK = [0,2,2,2,2,0,0,0,2,0,0,2]
UW_UPLINK   = [2,2,0,0,0,2,0,0,2,0,2,2]
NXT_UW_DOWNLINK = [2,2,0,2,2,0,2,0,2,0,2,2]
NXT_UW_UPLINK   = [0,2,0,0,0,0,0,0,2,0,2,0]
header_messaging="00110011111100110011001111110011" # 0x9669 in BPSK
header_time_location="11"+"0"*94
messaging_bch_poly=1897
ringalert_bch_poly=1207
acch_bch_poly=3545 # 1207 also works?
hdr_poly=29 # IBC header

def de_dqpsk(bits):
    symbols=[]
    imap=[0,1,3,2]
    # back into bpsk symbols
    for x in range(0,len(bits)-1,2):
        symbols.append(imap[int(bits[x+0])*2 + int(bits[x+1])])

    # undo differential decoding
    for c in range(1,len(symbols)):
        symbols[c]=(symbols[c-1]+symbols[c])%4

    return symbols

def de_interleave(group):
    symbols = [group[z+1]+group[z] for z in range(0,len(group),2)]
    # print(symbols)
    even = ''.join([symbols[x] for x in range(len(symbols)-2,-1, -2)])
    odd  = ''.join([symbols[x] for x in range(len(symbols)-1,-1, -2)])
    return (odd,even)

def bitdiff(a, b):
    return sum(x != y for x, y in zip(a, b))


def slice_extra(string, n):
    blocks = [string[x:x+n] for x in range(0, len(string)+1, n)]
    extra = blocks.pop()
    return (blocks,extra)

def slice(string, n):
    return [string[x:x+n] for x in range(0, len(string),n)]

# Parse a line to recover the number of bits with errors
# Only gives the number of errors that can be corrected, so the calculation is skewed towards perfect transmissions
def calculate_ber(line, type="IBC"):
    p = re.compile(r'(RAW): ([^ ]*) (\S+) (\d+) (?:N:([+-]?\d+(?:\.\d+)?)([+-]\d+(?:\.\d+)?)|A:(\w+)) [IL]:(\w+) +(\d+)% ([\d.]+|inf|nan) +(\d+) ([\[\]<> 01]+)(.*)')
    bit_errors = 0

    m=p.match(line)
    if m is None:
        return
    if m.group(5) is not None:
        snr=float(m.group(5))
        noise=float(m.group(6))
    
    bitstream_raw=(re.sub(r"[\[\]<> ]","",m.group(12)))
    uplink = -1
    if(bitstream_raw.startswith(iridium_access)):
        uplink=0
    elif(bitstream_raw.startswith(uplink_access)):
        uplink=1
    else:
        if len(bitstream_raw)>=len(iridium_access):
                access=de_dqpsk(bitstream_raw[:len(iridium_access)])
                if bitdiff(access, UW_DOWNLINK) < 4:
                    uplink=0
                    ec_uw=bitdiff(access,UW_DOWNLINK)
                    bit_errors += ec_uw
                elif bitdiff(access, UW_UPLINK) < 4:
                    uplink=1
                    ec_uw=bitdiff(access,UW_UPLINK)
                    bit_errors += ec_uw

    if uplink == 1:
        data=bitstream_raw[len(uplink_access):]
    elif uplink == 0:
        data=bitstream_raw[len(iridium_access):]
    else:
        return
        
    if type == "IBC":
        hdrlen=6
        blocklen=64
        msgtype=""
        if len(data)>=70 and not uplink:
            hdrlen=6
            blocklen=64
            (e1,_,_)=bch_repair1(hdr_poly,data[:hdrlen])
            (o_bc1,o_bc2)=de_interleave(data[hdrlen:hdrlen+blocklen])
            (e2,d2,b2)=bch_repair(ringalert_bch_poly,o_bc1[:31])
            (e3,d3,b3)=bch_repair(ringalert_bch_poly,o_bc2[:31])
            if e1>=0 and e2>=0 and e3>=0:
                if ((d2+b2+o_bc1[31]).count('1') % 2)==0:
                    if ((d3+b3+o_bc2[31]).count('1') % 2)==0:
                        msgtype="BC"
                        ec_lcw=e1

            if e1 < 0 or e2 < 0 or e3 < 0:
                return

        if msgtype == "BC":
            hdrlen=6
            header=data[:hdrlen]
            (e,d,bch)=bch_repair1(hdr_poly,header)
            bit_errors += e


            # Duplex slot packets have a maximum length of 179 symbols
            # but IBC have a 64 sym preamble instead of 16 sym, which reduces
            # their max len to 131 sym.

            ibclen = 131 * 2

            descrambled=[]
            (blocks,descramble_extra)=slice_extra(data[hdrlen:ibclen],64)
            for x in blocks:
                descrambled+=de_interleave(x)
            descramble_extra += data[ibclen:]

            poly=ringalert_bch_poly

            for block in descrambled:
                assert len(block)==32, "unknown BCH block len:%d"%len(block)

                parity=block[31:]
                block=block[:31]

                (errs,data,bch)=bch_repair(poly, block)
                if errs < 0:
                    return
                bit_errors += errs

                if ((data+bch+parity).count('1') % 2)==1:
                    bit_errors += 1
                    errs+=1
    return bit_errors, snr, noise, len(bitstream_raw)
