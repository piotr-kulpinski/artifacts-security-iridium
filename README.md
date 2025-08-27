# Systematic Security Analysis of the Iridium Radio Link

This repository contains the code for the paper "Systematic Security Analysis of the Iridium Radio Link".

This code contains the following main components: <br>
|-- key_extraction/ : Iridium SIM card key extraction tools <br>
|-- jamming_replay/ <br>
| |-- jamming.grc : GNU Radio flowgraph for jamming attacks <br>
| |-- replay.grc : GNU Radio flowgraph for replay attacks from SigMF files<br>
|-- pipeline/ <br>
| |-- pipeline.py : Privacy oriented pipeline for processing Iridium traffic <br>
| |-- plot-prr.py : Plotting script for Packet Reception Rate (PRR) against the SNR <br>
| |-- bch.py : supporting BCH functions <br>
| |-- ber.py : supporting Bit Error Rate (BER) functions <br>
| |-- util.py : supporting utility functions <br>
| |-- jsr-prr.py : Simulation of jamming attacks on Iridium Ring Alert <br>
|-- gr-iridiumtx/ :  GNU Radio module for transmitting Iridium signals <br>
| |-- grc/ : yaml files for custom GNU Radio blocks<br>
| |-- include/ : header files for custom GNU Radio blocks<br>
| |-- lib/ : C++ source files for custom GNU Radio blocks<br>
| |  |-- add_usrp_tags_impl.cc : add USRP tags for bursty transmission<br>
| |  |-- freq_impl.cc : frequency shifting block<br>
| |  |-- insert_delay_impl.cc : time offset block<br>
| |-- python/<br>
| |  |-- iridiumtx/ : main python script to control the GNU Radio flowgraph<br>
| |-- sample-data/ : sample data for testing<br>
| |-- utils/ : utility scripts for processing data<br>
| |  |-- convert_to_bitstream.py : converts a file of parsed frames from iridium-toolkit back text to bitstreams to be modulated<br>

## Source code

### For pipeline and simulations
- Python 3.10 or higher
- gr-iridium - installed in path
- iridium-toolkit - installed in path
- gnuradio - installed in path
- crcmod
- matplotlib


## Hardware for eavesdropping pipeline
- USRP B210
- Iridium L-band antenna
- Appropriate cables 

## Hardware for jamming/replay attacks
- HackRF One or USRP B210 (USRP B210 needs different sinks in the flowgraph)
- Iridium L-band antenna
- Appropriate cables 


# gr-iridiumtx
gr-iridiumtx it's a project extending the functionality of gr-iridium with the functionality to encode and modulate binary streams of valid Iridium bursts on the L-band link. The main functionality is the multi_gen.py, which takes a file as a input of iridium binary streams as in the output of collected Iridium binary streams with gr-iridium and outputs a SigMF file with the modulated binary streams onto the 10 MHz spectrum. This file then can be send over to any SDR that supports this spectrum and at the center frequency of Iridium L-band link.

Thus this tool can be used to generate legitimate Iridium signals to be sent over to legitimate Iridium devices to inject messages.

## Disclaimer
Regulations for transmitting on the Iridium L-band vary by country. Use this tool responsibly ideally only inside a faraday cage. Failing to use this tool responsibly may result in criminal offense. Creators of this tool do not take responsibility for any nefarious usage of this tool.

## Installation
Installation tested on Ubuntu 22.04, Python 3.10, GNURadio 3.10.

```
sudo apt install gnuradio-dev gr-osmosdr cmake libsndfile1-dev doxygen

git clone https://github.com/n00tzer0/gr-iridiumtx
cd gr-iridiumtx
cmake -B build
cmake --build build
sudo cmake --install build
sudo ldconfig
```

## Hardware
- Any SDR supporting 10 MHz bandwidth and L-band frequencies (e.g., USRP B210)
- L-band antenna
- Appropriate cables

## Usage
For generating SigMF files from recorded or created Iridium traffic. The recorded text output from gr-iridium can be replayed into a SigMF file. Example of the Ring alerts are presented in the sample-data directory. Depending on the number of frames being transmitted in parallel at the same time offset, set this many channels.

```
python3 python/iridiumtx/multi_gen.py --channels <number of channels> --<input text file>
```

