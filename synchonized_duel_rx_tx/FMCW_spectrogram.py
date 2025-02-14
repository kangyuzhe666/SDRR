import adi
import time
import matplotlib.pyplot as plt
import numpy as np
from scipy import signal
import sdr_utils as sutil
import seaborn as sns
import pandas as pd
import chart_studio.plotly as py
import plotly.graph_objects as go
from numpy.fft import fft, ifft


sdr = adi.ad9361(uri='ip:192.168.2.1')
samp_rate = 30.72e6    # must be <=30.72 MHz if both channels are enabled
num_samps_tx = 2**18
num_samps_rx = 2**20
#num_samps = 2**18      # number of samples per buffer.  Can be different for Rx and Tx
rx_lo = 2.0e9
rx_mode = "manual"  # can be "manual" or "slow_attack"
rx_gain0 = 40
rx_gain1 = 40
tx_lo = rx_lo
tx_gain0 = -1
tx_gain1 = -89


'''Configure Rx properties'''
sdr.rx_enabled_channels = [0, 1]
sdr.sample_rate = int(samp_rate)
sdr.rx_lo = int(rx_lo)
sdr.gain_control_mode = rx_mode
sdr.rx_hardwaregain_chan0 = int(rx_gain0)
sdr.rx_hardwaregain_chan1 = int(rx_gain1)
sdr.rx_buffer_size = int(num_samps_rx)

'''Configure Tx properties'''
sdr.tx_rf_bandwidth = int(samp_rate)
sdr.tx_lo = int(tx_lo)
sdr.tx_cyclic_buffer = True
sdr.tx_hardwaregain_chan0 = int(tx_gain0)
sdr.tx_hardwaregain_chan1 = int(tx_gain1)
sdr.tx_buffer_size = int(num_samps_tx)

f_low = 300
f_high = 3000
chirp_duration = 8e-3
dfdt = (f_high - f_low) / chirp_duration
Ts = 1/sdr.sample_rate
BW = 2e6 # Hz
# trying to generate a chirp 
t_range = np.arange(0, chirp_duration, Ts)
FM_chirp = signal.chirp(t_range, f_low, chirp_duration, f_high, method = 'linear')

tx_chirp = FM_chirp * 2**14
shaped = sutil.raised_cos_filter(tx_chirp, β = 0.9)
fm_down_chirp = np.flip(shaped)
shaped = np.concatenate([shaped,fm_down_chirp])
I = shaped
Q = np.zeros(len(shaped))
IQ_send = Q + 1j*Q
IQ2 = I + 1j*Q
#IQ_send = np.concatenate([IQ_send, IQ_send, IQ_send, IQ_send, IQ_send, IQ2, IQ2])
IQ_send = IQ2

TX2_zeros = np.zeros(len(IQ_send))
sdr.tx_cyclic_buffer = True # Enable cyclic buffers
sdr.tx([IQ_send, TX2_zeros]) # start transmitting

#sdr.rx_annotated = False
for i in range(0,10):
    sdr.rx()

for k in range(0,30):
    sample_rx = sdr.rx()
    data_rx_0 = sample_rx[0]
    data_rx_1 = sample_rx[1]
    num_taps = 10001 # it helps to use an odd number of taps
    cut_off = 10 # Hz
    sample_rate = sdr.sample_rate # Hz
    h = signal.firwin(num_taps, cut_off, nyq=sample_rate/2)
    data_rx_0_h = np.convolve(data_rx_0, h)
    data_rx_1_h = np.convolve(data_rx_1, h)
    mixed = data_rx_0_h * np.conjugate(data_rx_1_h)
    sr = sdr.sample_rate
    x = mixed

    sample_rate = sdr.sample_rate

    # fft_size = 1024
    # num_rows = int(np.floor(len(x)/fft_size))
    # spectrogram = np.zeros((num_rows, fft_size))
    # for i in range(num_rows):
    #     spectrogram[i,:] = 10*np.log10(np.abs(np.fft.fftshift(np.fft.fft(x[i*fft_size:(i+1)*fft_size])))**2)
    # spectrogram = spectrogram[:,fft_size//2:] # get rid of negative freqs because we simulated a real signal
    
    # plt.imshow(spectrogram, aspect='auto', extent = [0, sample_rate/2/1e6, 0, len(x)/sample_rate])
    # plt.xlabel("Frequency [MHz]")
    # plt.ylabel("Time [s]")
    # plt.title(f"plot #{k}")
    # plt.pause(0.05)
    x = x * np.hamming(len(x)) # apply a Hamming window
    Fs = sdr.sample_rate # lets say we sampled at 1 MHz
    # assume x contains your array of IQ samples
    N = 1024
    x = x[0:N] # we will only take the FFT of the first 1024 samples, see text below
    PSD = (np.abs(np.fft.fft(x))/N)**2
    PSD_log = 10.0*np.log10(PSD)
    PSD_shifted = np.fft.fftshift(PSD_log)
    #X = fft(x)
    #X = np.abs(X)/1e8
    center_freq = 2.0e9 # frequency we tuned our SDR to
    f = np.arange(Fs/-2.0, Fs/2.0, Fs/N) # start, stop, step.  centered around 0 Hz
    f += center_freq # now add center frequency
    plt.plot(f, PSD_shifted)
    plt.pause(0.05)
    #print(f"|f0: {X[0]}| f1: {X[1]} | f2: {X[2]} |")


plt.show()

sdr.tx_destroy_buffer()