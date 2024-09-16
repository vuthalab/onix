import matplotlib.pyplot as plt
import numpy as np

data = np.load("spectrum.npz")
fs = data["freqs"]

fig, ax = plt.subplots(figsize=(6, 4))
ax.plot(fs, data["power_W_T"], color="#376f9f")
ax.plot(fs, data["power_W_T_binned"], color="C1", ls="dotted", linewidth=2)
ax.plot(fs, data["power_W_T_bound"], color="C3", linewidth=1.3, ls="dashed")
ax.set_ylabel("$\\delta W_T$ power spectral density (Hz$^2$ / Hz)")
ax.set_xlabel("Oscillation frequency (Hz)")
ax.set_xscale("log")
ax.set_yscale("log")
plt.tight_layout()
plt.savefig("spectrum.pdf")
plt.show()
