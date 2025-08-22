# Systematic Security Analysis of the Iridium Radio Link

This repository contains the code for the paper "Systematic Security Analysis of the Iridium Radio Link".

This code contains the following main components:
|-- pipeline.py : Privacy oriented pipeline for processing Iridium traffic
|-- jamming-sim.py : Simulation of jamming attacks on Iridium signals
|-- gr-iridiumtx/ :  GNU Radio module for transmitting Iridium signals, it is based on GNU Radio module template
| |-- grc/ : yaml files for custom GNU Radio blocks
| |-- include/ : header files for custom GNU Radio blocks
| |-- lib/ : C++ source files for custom GNU Radio blocks
| |  |-- add_usrp_tags_impl.cc : add USRP tags for bursty transmission
| |  |-- freq_impl.cc : frequency shifting block
| |  |-- insert_delay_impl.cc : time offset block
| |-- python/
| |  |-- iridiumtx/ : main python script to control the GNU Radio flowgraph
| |-- sample-data/ : sample data for testing
| |-- utils/ : utility scripts for processing data
| |  |-- convert_to_bitstream.py : converts a file of parsed frames from iridium-toolkit back text to bitstreams to be modulated

## Source code

### For pipeline and simulations
- Python 3.10 or higher
- gr-iridium - installed in path
- iridium-toolkit - installed in path
- gnuradio - installed in path
- crcmod
- matplotlib


## Hardware
- USRP B210
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


## Usage
For generating SigMF files from recorded or created Iridium traffic. The recorded text output from gr-iridium can be replayed into a SigMF file. Example of the Ring alerts are presented in the sample-data directory. Depending on the number of frames being transmitted in parallel at the same time offset, set this many channels.

```
python3 python/iridiumtx/multi_gen.py --channels <number of channels> --<input text file>
```

