import sqlite3
import numpy as np
import matplotlib.pyplot as plt

prr_buf = np.zeros(1000)
prr_count_frames = np.zeros(1000)


def read_prr_stats(db_path):
    global prr_buf, prr_count_frames
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT prr_sum, count FROM prr_stats")
    rows = cursor.fetchall()
    for idx, row in enumerate(rows):
        prr_sum, count = row
        prr_buf[idx] = prr_sum
        prr_count_frames[idx] = count
        
    conn.close()

def plot_ppr(filename='ppr.png'):
    disp = (prr_buf*100)/prr_count_frames
    x = np.arange(len(disp)) / 10

    plt.plot(x, disp)
    plt.xlabel('SNR [dB]')
    plt.ylabel('Packet reception rate [%]')
    plt.title('Packet reception rate per SNR')

    print(f"Saving to {filename}")
    plt.savefig(filename)


db_path = "./iridium_metadata.db"
read_prr_stats(db_path)
plot_ppr()




