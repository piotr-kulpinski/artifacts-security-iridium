import datetime
import re


class Zulu(datetime.tzinfo):
    def utcoffset(self, dt):
        return datetime.timedelta(0)
    def dst(self, dt):
        return datetime.timedelta(0)
    def tzname(self, dt):
        return "Z"

Z = Zulu()

lcw_ft_table = {
    'maint': 0,
    'acchl': 1,
    'hndof': 2,
    'rsrvd': 3,
}

maint_code_table = {
    'sync': 0,
    'switch': 1,
    'maint[2]': 3,
    'geoloc': 6,
    'maint[1]': 12,
    '<silent>': 15, 
}

acchl_code_table = {
    'acchl': 1,
}

hndof_code_table = {
    'handoff_cand': 12,
    'handoff_resp': 3,
    '<silent>': 15,
}


class IridiumMessage:
    type = ''
    bitstream = ''
    bitstream_bch = ''
    interleaved = ''
    direction = ''
    uw_downlink = "001100000011000011110011"
    uw_uplink =   "110011000011110011111100"
    phy_details = ''
    snr = ""
    noise = ""

    def parse_phy(self, line):
        parts = line.split()
        match = re.search(r'.*-(\d+)-.*', parts[1])
        if match:
            timestamp_s = int(match.group(1))
            self.timestamp = timestamp_s + float(parts[2])

        match_snr = re.search(r'.*\|(.*)\|(.*)', parts[5])
        if match_snr:
            self.snr = match_snr.group(2)
            self.noise = match_snr.group(1)

        self.frequency = int(parts[3])
        self.direction = parts[7]
        self.phy_details = ' '.join(parts[1:4]) + ' N:' + self.snr + self.noise + ' I:00000000000 ' + parts[4] + ' 0.00000 ' + parts[6]
    
    def parse_lcw(self, line):
        lcw3 = {}

        m = re.match(r'.*LCW\((\d+),T:(\w+),C:(\S+)\).*', line)
        if not m:
            raise ValueError("Line does not match LCW format")
        self.ft = int(m.group(1))

        type_name = m.group(2)
        self.type = lcw_ft_table.get(type_name)
        if self.type is None:
            raise ValueError(f"Unknown LCW type: {type_name}")
        
        lcw = m.group(3)
        # print(f"LCW: {lcw}")
        if type_name == 'maint':
            self.lcw_ft = lcw_ft_table.get('maint')
            if lcw.startswith('maint[1]'):
                m2 = re.match(r'maint\[(\d+)\]\[lqi:(\d+),power:(\d+)\],(\d+)', lcw)
                if not m2:
                    raise ValueError("Malformed maint message")
                self.lcw_code = maint_code_table.get('maint[1]')
                lcw3['lcw3bits'] = m2.group(4) # 16 bits
                lcw3['power']    = format(int(m2.group(3)), '03b')
                lcw3['lqi']      = format(int(m2.group(2)), '02b')

            elif lcw.startswith('maint[2]'):
                m2 = re.match(r'maint\[(\d+)\]\[lqi:(\d+),power:(\d+),f_dtoa:(\d+),f_dfoa:(\d+)\],(\d+)\|(\d+)', lcw)
                if not m2:
                    raise ValueError("Malformed maint message")
                self.lcw_code = maint_code_table.get('maint[2]')
                lcw3['lcw3bit_first']  = m2.group(6) # 1 bit
                lcw3['lqi']            = format(int(m2.group(2)), '02b')
                lcw3['power']          = format(int(m2.group(3)), '03b')
                lcw3['f_dtoa']         = format(int(m2.group(4)), '07b')
                lcw3['f_dfoa']         = format(int(m2.group(5)), '07b')
                lcw3['lcw3bit_second'] = m2.group(7) # 1 bit

            elif lcw.startswith('<silent>'):
                self.lcw_code = maint_code_table.get('<silent>')
                lcw3['lcw3bits'] = lcw.split(',')[1] # 21 bits

            elif lcw.startswith('sync'):
                m2 = re.match(r'sync\[status:(\d+),dtoa:(\d+),dfoa:(\d+)\],(\d+)\|(\d+)', lcw)
                if not m2:
                    print(f"Malformed sync message: {lcw}")
                    raise ValueError("Malformed sync message")
                self.lcw_code = maint_code_table.get('sync')
                lcw3['lcw3bit_first']  = m2.group(4) # 1 bit
                lcw3['status']         = format(int(m2.group(1)), '01b')
                lcw3['lcw3bit_second'] = m2.group(5)  # 1 bit
                lcw3['dtoa']           = format(int(m2.group(2)), '010b')
                lcw3['dfoa']           = format(int(m2.group(3)), '08b')

            elif lcw.startswith('switch'):
                m2 = re.match(r'switch\[dtoa:(\d+),dfoa:(\d+)\],(\d+)', lcw)
                if not m2:
                    raise ValueError("Malformed switch message")
                self.lcw_code = maint_code_table.get('switch')
                lcw3['lcw3bits'] = m2.group(3) # 3 bits
                lcw3['dtoa'] = format(int(m2.group(1)), '010b')
                lcw3['dfoa'] = format(int(m2.group(2)), '08b')
                
            elif lcw.startswith('geoloc'):
                self.lcw_code = maint_code_table.get('geoloc')
                lcw3['lcw3bits'] = lcw.split(',')[1] # 21 bits

            elif lcw.startswith('rsrvd'):
                m2 = re.match(r'rsrvd\((\d+)\)', lcw)
                if not m2:
                    raise ValueError("Malformed acchl rsrvd message")
                self.lcw_code = int(m2.group(1))
                lcw3['lcw3bits'] = lcw.split(',')[1]

        elif type_name == 'acchl':
            self.lcw_ft = lcw_ft_table.get('acchl')
            if lcw.startswith('acchl'):
                m2 = re.match(r'acchl\[msg_type:(\d+),bloc_num:(\d+),sapi_code:(\d+),segm_list:(\d+)\],(\d+),(\d+)', lcw)
                if not m2:
                    raise ValueError("Malformed acchl message")
                self.lcw_code = acchl_code_table.get('acchl')
                lcw3['lcw3bits_first'] = m2.group(5) # 1 bit
                lcw3['msg_type'] = format(int(m2.group(1), 16), '03b')
                lcw3['bloc_num'] = format(int(m2.group(2), 16), '01b')
                lcw3['sapi_code'] = format(int(m2.group(3), 16), '03b')
                lcw3['segm_list'] = m2.group(4)
                lcw3['lcw3bits_second'] =  format(int(m2.group(6), 16), '05b') # 5 bits

            elif lcw.startswith('rsrvd'):
                m2 = re.match(r'rsrvd\((\d+)\)', lcw)
                if not m2:
                    raise ValueError("Malformed acchl rsrvd message")
                self.lcw_code = int(m2.group(1))
                lcw3['lcw3bits'] = lcw.split(',')[1]

        elif type_name == 'hndof':
            self.lcw_ft = lcw_ft_table.get('hndof')
            if lcw.startswith('handoff_cand'):
                m2 = re.match(r'handoff_cand', lcw)
                if not m2:
                    raise ValueError("Malformed handoff_cand message")
                self.lcw_code = hndof_code_table.get('handoff_cand') 
                lcw3['lcw3bit_first'] = lcw.split(',')[1] # 11 bits
                lcw3['lcw3bit_second'] = lcw.split(',')[2] # 10 bit

            elif lcw.startswith('handoff_resp'):
                m2 = re.match(r'handoff_resp\[cand:(\S),denied:(\d),ref:(\d),slot:(\d),sband_up:(\d+),sband_dn:(\d+),access:(\d)\],(\d+),(\d+)', lcw)
                if not m2:
                    print(f"Malformed handoff_resp message: {lcw}")
                    raise ValueError("Malformed handoff_resp message")
                self.lcw_code = hndof_code_table.get('handoff_resp')
                lcw3['lcw3bit_first'] = m2.group(8) # 2 bits
                lcw3['cand'] = '0' if m2.group(1) == 'P' else '1' if m2.group(1) == 'S' else None
                lcw3['denied']         = format(int(m2.group(2)), '01b')
                lcw3['ref']            = format(int(m2.group(3)), '01b')
                lcw3['lcw3bit_second'] = m2.group(9) # 1 bit
                lcw3['slot']           = format(int(m2.group(4)) - 1, '02b')
                lcw3['sband_up']       = format(int(m2.group(5)), '05b')
                lcw3['sband_dn']       = format(int(m2.group(6)), '05b')
                lcw3['access']         = format(int(m2.group(7)) - 1, '03b')
                
            elif lcw.startswith('<silent>'):
                self.lcw_code = hndof_code_table.get('<silent>')
                lcw3['lcw3bits'] = lcw.split(',')[1] # 21 bits

            elif lcw.startswith('rsrvd'):
                m2 = re.match(r'rsrvd\((\d+)\)', lcw)
                if not m2:
                    raise ValueError("Malformed hndof rsrvd message")
                self.lcw_code = int(m2.group(1))
                lcw3['lcw3bits'] = lcw.split(',')[1] # 21 bits
            else:
                raise ValueError(f"Unknown handoff type: {lcw}")
            
        elif type_name == 'rsrvd':
            self.lcw_ft = lcw_ft_table.get('rsrvd')
            m2 = re.match(r'\<(\d+)\>', lcw)
            if not m2:
                raise ValueError("Malformed rsrvd message")
            self.lcw_code = int(m2.group(1))
            lcw3['lcw3bits'] = lcw.split(',')[1] # 21 bits
        

        self.lcw1 = format(self.ft, '03b')# first block
        try:
            self.lcw2 = format(self.lcw_ft, '02b') + format(self.lcw_code, '04b') # second block
        except ValueError:
            raise ValueError(f"Unknown LCW code: {self.lcw_code} line: {line}")
        
        self.lcw3 = '' 
        try:
            for key in lcw3:
                self.lcw3 += lcw3[key]
        except TypeError as e:
            raise TypeError(f"Int in LCW3: {e} line: {line}")
        try:
            lcw1_encoded = format(self.bch_encode(int(self.lcw1, 2), 29, input_len=3, gen_len=5), '07b')
            lcw2_encoded = format(self.bch_encode(int(self.lcw2, 2), 465, input_len=6, gen_len=9), '014b')[:-1]
            lcw3_encoded = format(self.bch_encode(int(self.lcw3, 2), 41, input_len=21, gen_len=6), '026b')
        except ValueError:
            raise ValueError(f"Unknown LCW code: {self.lcw_code} line: {line}")
        # print(f"LCW1: {self.lcw1} -> {lcw1_encoded}")
        # print(f"LCW2: {self.lcw2} -> {lcw2_encoded}")
        # print(f"LCW3: {self.lcw3} -> {lcw3_encoded}")

        lcw3_interleaved = self.interleave_lcw(lcw1_encoded, lcw2_encoded, lcw3_encoded)
        lcw3_interleaved = self.flip_bits(lcw3_interleaved)

        return lcw3_interleaved


    def pretty(self):
        if self.direction == 'DL':
            return f"RAW: {self.phy_details} {self.uw_downlink + self.bitstream}"
        elif self.direction == 'UL':
            return f"RAW: {self.phy_details} {self.uw_uplink + self.bitstream}"
        else:
            return f"No direction: RAW {self.phy_details} {self.bitstream}"

    def get_full_bitstream(self):
        return self.uw_downlink + self.bitstream if self.direction == 'DL' else self.uw_uplink + self.bitstream

    def get_bitstream(self):
        return self.bitstream
    
    def get_frequency(self):
        return self.frequency
    
    def get_all(self):
        return self.type, self.timestamp, self.frequency, self.bitstream
    
    def encode(self):
        # Convert bitstream to block and into decimal values
        blocks = [self.bitstream[i:i+21] for i in range(0, len(self.bitstream), 21)]
        for block in blocks:
            if not block.isdigit():
                print(self.line)
                print(self.bitstream)
                raise ValueError(f"Block '{block}' is not convertable to int")
            out = self.bch_encode(int(block, 2), 1207)
            out = format(out, '031b')

            # Parity bit
            parity_bit = str(out).count('1') % 2
            block_with_parity = str(out) + str(parity_bit)
            self.bitstream_bch += block_with_parity

    def scramble2(self, begin_at=0):

        # Padding maybe unnecessary, but some of the messages have {short} and that is not recontructed properly
        padding_length = (64 - (len(self.bitstream_bch) - begin_at % 64)) % 64
        self.bitstream_bch = self.bitstream_bch + '0' * padding_length
        

        # Scrambling (last step before transmission)
        for i in range(begin_at, len(self.bitstream_bch), 64):
            block = self.bitstream_bch[i:i+64]
            odd, even = block[:32], block[32:64]
            self.interleaved += self.interleave2(odd, even)

    def scramble3(self, once=False):

        if once:
            block = self.bitstream_bch[:96]
            first, second, third = block[:32], block[32:64], block[64:]
            self.interleaved += self.interleave3(first, second, third)
            return
        
        # Padding
        padding_length = (96 - (len(self.bitstream_bch) % 96)) % 96
        self.bitstream_bch = self.bitstream_bch + '0' * padding_length
        
        for i in range(0, len(self.bitstream_bch), 96):
            block = self.bitstream_bch[i:i+96]
            first, second, third = block[:32], block[32:64], block[64:]
            self.interleaved += self.interleave3(first, second, third)


    def interleave2(self, odd, even):
        symbols = [even[z]+even[z+1]+odd[z]+odd[z+1] for z in range(0,len(odd),2)]
        return ''.join(symbols[::-1])


    def interleave3(self, first, second, third):
        symbols = []
        for i in range(0, len(first), 2):
            symbols.append(first[i+1] + first[i])
            symbols.append(second[i+1] + second[i])
            symbols.append(third[i+1] + third[i])
        interleaved = ''.join(symbols)[::-1]
        return interleaved
    
    def interleave_lcw(self, lcw1, lcw2, lcw3):
        tbl = [40, 39, 36, 35, 32, 31, 28, 27, 24, 23, 20, 19, 16, 15, 12, 11,  8,  7,  4,  3,
               41, 38, 37, 34, 33, 30, 29, 26, 25, 22, 21, 18, 17, 14, 13, 10,  9,  6,  5,  2,
               1, 46, 45, 44, 43, 42]
        bits = [''] * 46
        lcw = lcw1 + lcw2 + lcw3
        for i, t in enumerate(tbl):
            bits[t - 1] = lcw[i]
        return ''.join(bits)
    
    def flip_bits(self, bitstream):
        flipped = ''
        for i in range(0, len(bitstream), 2):
            flipped += bitstream[i+1] + bitstream[i]
        return flipped

    def str_time_to_iritime(self, strtime):
        iritime = datetime.datetime.strptime(strtime, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=Z).timestamp()
        if iritime>1435708799: iritime+=1 # Leap second: 2015-06-30 23:59:59
        if iritime>1483228799: iritime+=1 # Leap second: 2016-12-31 23:59:59
        return int(round((iritime-1399818235)*100/9))

    # add bch bits
    # poly value = 1207 BCH(31,21) 

    def int_to_bin_list(self, n, width):
        return [int(x) for x in bin(n)[2:].zfill(width)]

    def bin_list_to_int(self,bin_list):
        return int(''.join(str(x) for x in bin_list), 2)

    def bch_encode(self, data, generator, input_len=21, gen_len=11):
        data_bits = self.int_to_bin_list(data, input_len)
        generator_bits = self.int_to_bin_list(generator, gen_len)
        padded_data = data_bits + [0] * (gen_len - 1)

        for i in range(input_len):
            if padded_data[i] == 1:
                for j in range(gen_len):
                    padded_data[i + j] ^= generator_bits[j]

        return data << gen_len - 1 | self.bin_list_to_int(padded_data[-gen_len - 1:])