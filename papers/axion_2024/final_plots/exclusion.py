import matplotlib.pyplot as plt
import numpy as np
import scipy.constants as c


def axion_mass_to_frequency(mass):
    """eV to Hz"""
    return mass * c.e / (2 * np.pi * c.hbar)


def plot_bound(ax, masses, inverse_fa, **kwargs):
    large_inverse_fa = 1e10
    masses = np.append(np.append(masses[0], masses), masses[-1])
    inverse_fa = np.append(np.append(large_inverse_fa, inverse_fa), large_inverse_fa)
    ax.plot(masses, inverse_fa, **kwargs)


def fill_between(ax, masses, inverse_fa_lower, inverse_fa_upper = None, **kwargs):
    if inverse_fa_upper is None:
        inverse_fa_upper = 1e10
    ax.fill_between(masses, inverse_fa_lower, inverse_fa_upper, **kwargs)

data = np.load("exclusion.npz")

color_onix = "#477fbf"
color_nedm = "C1"
color_neutron_beam = "C2"

fig, ax = plt.subplots(figsize=(6, 4))
ax.set_xlabel("ALP mass (eV)")
ax.set_ylabel("$C_G / f_a$ (GeV${}^{-1}$)")
ax.set_xscale("log")
ax.set_yscale("log")

plot_bound(ax, data["nedm_masses"], data["nedm_inverse_fa"], color=color_nedm)
plot_bound(ax, data["neutron_beam_masses"], data["neutron_beam_inverse_fa"], color=color_neutron_beam)

plot_bound(
    ax, data["onix_masses"], data["onix_inverse_fa_geo_mean"],
    color=color_onix, linewidth=3, zorder=20,
)
fill_between(
    ax, data["onix_masses"], data["onix_inverse_fa_Sushkov"], data["onix_inverse_fa_Flambaum"],
    color=color_onix, alpha=0.6, zorder=15, linewidth=3, 
)
fill_between(
    ax, data["onix_masses"], data["onix_inverse_fa_Sushkov"],
    color=color_onix, alpha=0.9, zorder=15,
)

ax1 = ax.twiny()
ax1.set_xlabel("Oscillation frequency (Hz)")
ax1.set_xscale("log")

ax.set_ylim(0.5e-16, 5e-7)
lower_mass_bound = 3e-22
upper_mass_bound = 1.5e-15
ax.set_xlim(lower_mass_bound, upper_mass_bound)
ax1.set_xlim(axion_mass_to_frequency(lower_mass_bound), axion_mass_to_frequency(upper_mass_bound))

ax.text(1e-17, 0.3e-15, "nEDM", color="C1", fontsize=12)
ax.text(0.18e-15, 8e-14, "neutron\n  beam", color="C2", fontsize=12)
ax.arrow(0.5e-15, 16e-13, 0, 2e-11, color="C2", width=1e-18, head_length=3e-11, head_width=1e-16, overhang=0.2)
ax.fill_between([1e-19, 0.6e-18], 6e-12, 4.5e-11, zorder=150, color="white", linewidth=0.5, edgecolor="black")
ax.text(1.27e-19, 1e-11, "ONIX", color="black", fontsize=12, zorder=200)
plt.tight_layout()
plt.savefig("exclusion.pdf")
plt.show()
