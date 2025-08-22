import numpy as np
from scipy.special import erfc, comb, erfcinv
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

# Taken from:
# Joshua Smailes, https://github.com/ssloxford/SatIQ-noise

def bch_error_rate(ber, data_length, parity_length, t, interleave_depth, symbol_size):
    symbol_correct_rate = (1 - ber)**symbol_size
    symbol_error_rate = 1 - (1 - ber)**symbol_size
    block_length = (data_length+parity_length)/interleave_depth

    block_correct_rate = np.sum(list(map(
        lambda e: (
            (symbol_correct_rate)**(block_length-e)
            * symbol_error_rate**e
            * comb(block_length, e)
        ),
        range(0, t+1)
    )))
    packet_error_rate = 1 - (block_correct_rate)**interleave_depth
    len = (data_length + parity_length)*symbol_size*interleave_depth
    equivalent_ber = packet_error_rate*0.5
    return {
        "equivalent_ber": equivalent_ber,
        "packet_error_rate": packet_error_rate
    }

JSR = np.arange(10**(-18/10), 10**(8/10), 0.01)
bits_per_symbol = 2
EbN0s = (1/ JSR * (1/bits_per_symbol))
JSR_dB = 10*np.log10(JSR)
BPSK_new = lambda EbN0: 0.5 * erfc(np.sqrt(EbN0))
bch_packet_errors = np.vectorize(lambda ber: bch_error_rate(ber, data_length=21, parity_length=10, t=2, interleave_depth=3, symbol_size=2)["packet_error_rate"])

# Calculate BCH packet errors for each Eb/N0
packet_error_rates = 1 - bch_packet_errors(BPSK_new(EbN0s))

prr_to_jsr = interp1d(packet_error_rates, JSR_dB, kind='linear', fill_value="extrapolate")
jsr_value_at_prr_0_5 = prr_to_jsr(0.5)
print(f"JSR value (in dB) where PRR = 0.5: {jsr_value_at_prr_0_5}")

def plot_jammer_power():
    axs = plt.axes()
    JSR_dB = 10*np.log10(JSR)
    axs.plot(JSR_dB, packet_error_rates)
    plt.axhline(y=0.5, color='red', linestyle='--', linewidth=1.5, label="PRR = 0.5")

    # Adding labels, title, and legend
    plt.xlabel("Jamming to signal ratio [dB]")
    plt.ylabel("Packet reception rate")
    plt.savefig("prr_vs_jsr.png", dpi=300)


plot_jammer_power()
