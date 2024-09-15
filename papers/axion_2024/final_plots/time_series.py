import matplotlib.pyplot as plt
import numpy as np

data = np.load("time_series.npz")
ts = data["times"]
Zs = data["Zs"]
delta_W_Ts = data["delta_W_Ts"]

def downsample(data, N):
    return data[:(len(data) // N) * N].reshape(-1, N)[:, 0]

downsample_ratio = 10
ts = downsample(ts, downsample_ratio)
Zs = downsample(Zs, downsample_ratio)
delta_W_Ts = downsample(delta_W_Ts, downsample_ratio)

x_ratio = 1.5
fig, axs = plt.subplots(2, 2, sharex=False, sharey=False, figsize=(6, 4), width_ratios=(x_ratio, 1))
axs[1][0].set_ylabel("$Z_b$ (Hz)")
axs[0][0].set_ylabel("$\\delta W_T$ (Hz)")
axs[1][0].set_xlabel("Time (hour)", loc="right")

Z_b_padding = 5
W_T_padding = 0.5
y_limits_Z_b = (np.min(Zs) - Z_b_padding, np.max(Zs) + Z_b_padding)
y_limits_W_T = (np.min(delta_W_Ts) - W_T_padding, np.max(delta_W_Ts) + W_T_padding)
axs[0][0].set_ylim(*y_limits_W_T)
axs[0][1].set_ylim(*y_limits_W_T)
axs[1][0].set_ylim(*y_limits_Z_b)
axs[1][1].set_ylim(*y_limits_Z_b)

axs[0][0].text(0.02, 0.1, "(a)", transform=axs[0][0].transAxes, fontsize=12)
axs[1][0].text(0.02, 0.85, "(b)", transform=axs[1][0].transAxes, fontsize=12)

break_center_time = 300
left_mask = ts < break_center_time
right_mask = ts > break_center_time

Zs_kwargs = {
    "color": "C0",
    "s": 0.8,
    "marker": "o",
}
W_Ts_kwargs = {
    "color": "C7",
    "s": 0.8,
    "marker": "o",
}
axs[0][0].scatter(ts[left_mask], delta_W_Ts[left_mask], **W_Ts_kwargs)
axs[0][1].scatter(ts[right_mask], delta_W_Ts[right_mask], **W_Ts_kwargs)
axs[1][0].scatter(ts[left_mask], Zs[left_mask], **Zs_kwargs)
axs[1][1].scatter(ts[right_mask], Zs[right_mask], **Zs_kwargs)

# break the axis.
axs[0][0].set_xticklabels([])
axs[0][1].set_xticklabels([])
axs[0][1].set_yticklabels([])
axs[1][1].set_yticklabels([])
axs[0][0].spines["right"].set_visible(False)
axs[1][0].spines["right"].set_visible(False)
axs[0][1].set_yticks([])
axs[0][1].spines["left"].set_visible(False)
axs[1][1].set_yticks([])
axs[1][1].spines["left"].set_visible(False)

d = 2  # proportion of vertical to horizontal extent of the slanted line
kwargs = dict(marker=[(-1, -d), (1, d)], markersize=8,
              linestyle="none", color='k', mec='k', mew=1, clip_on=False)
axs[0][0].plot([1, 1], [0, 1], transform=axs[0][0].transAxes, **kwargs)
axs[1][0].plot([1, 1], [0, 1], transform=axs[1][0].transAxes, **kwargs)
axs[0][1].plot([0, 0], [1, 0], transform=axs[0][1].transAxes, **kwargs)
axs[1][1].plot([0, 0], [1, 0], transform=axs[1][1].transAxes, **kwargs)

previous_xlim = axs[1][1].get_xlim()
left_xlim = axs[1][0].get_xlim()
left_xlim_range = left_xlim[1] - left_xlim[0]
xlim_center = (previous_xlim[0] + previous_xlim[1]) / 2
new_xlim_left = (-left_xlim_range / 2 / x_ratio + xlim_center, left_xlim_range / 2 / x_ratio + xlim_center)
axs[0][1].set_xlim(*new_xlim_left)
axs[1][1].set_xlim(*new_xlim_left)

plt.tight_layout()
fig.subplots_adjust(wspace=0.03, )
plt.savefig("time-series.pdf")
plt.show()
