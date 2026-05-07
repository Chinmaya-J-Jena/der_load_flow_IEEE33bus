"""
plots.py
--------
All visualisation functions for the DER load flow study.
Every function saves a PNG to the results/ folder AND
returns the matplotlib Figure for optional inline display.
"""

import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec

# ── colour palette (consistent across all plots) ──────────────────────────────
C_BASE   = "#1f77b4"   # blue  — base case
C_DER    = "#e87722"   # amber — with DER
C_PV     = "#2ca02c"   # green — PV generation
C_BESS   = "#9467bd"   # purple — BESS
C_EV     = "#d62728"   # red   — EV load
C_LIMIT  = "#888888"   # gray  — IEEE voltage limits
C_NORMAL = "#2ca02c"
C_UNDER  = "#d62728"
C_OVER   = "#ff7f0e"
C_DISCHARGE = "#008b8b"

V_UPPER  = 1.05
V_LOWER  = 0.95


def _save(fig, filename, save_path):
    os.makedirs(save_path, exist_ok=True)
    fpath = os.path.join(save_path, filename)
    fig.savefig(fpath, dpi=150, bbox_inches="tight")
    print(f"  Saved → {fpath}")
    return fig


# ── Plot 1 : Voltage profile comparison ───────────────────────────────────────
def plot_voltage_comparison(base_v, der_v, save_path="results"):
    """
    Bar-style comparison of bus voltage magnitudes:
    base case vs with PV + BESS + EV.
    """
    buses = range(len(base_v))

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(buses, base_v.values, marker="o", markersize=5,
            color=C_BASE, linewidth=1.8, label="Base case (no DER)")
    ax.plot(buses, der_v.values,  marker="s", markersize=5,
            linestyle="--", color=C_DER, linewidth=1.8,
            label="With PV + BESS + EV")

    ax.axhline(V_LOWER, color=C_LIMIT, linestyle=":", linewidth=1.2,
               label=f"Lower limit ({V_LOWER} pu) — IEEE 1547")
    ax.axhline(V_UPPER, color=C_LIMIT, linestyle="-.", linewidth=1.2,
               label=f"Upper limit ({V_UPPER} pu) — IEEE 1547")

    # shade violation zone
    ax.fill_between(buses, 0.90, V_LOWER,
                    color=C_UNDER, alpha=0.08, label="Undervoltage zone")

    ax.set_xlim(-0.5, len(base_v) - 0.5)
    ax.set_ylim(0.88, 1.08)
    ax.set_xlabel("Bus number", fontsize=11)
    ax.set_ylabel("Voltage magnitude (pu)", fontsize=11)
    ax.set_title("IEEE-33 Bus: Voltage profile — Without DER vs DER integration",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=9, loc="lower left")
    ax.grid(True, alpha=0.3)

    # annotate min voltage improvement
    min_base = base_v.min()
    min_der  = der_v.min()
    ax.annotate(
        f"Min base: {min_base:.4f} pu",
        xy=(base_v.idxmin(), min_base),
        xytext=(base_v.idxmin() + 1.5, min_base - 0.012),
        arrowprops=dict(arrowstyle="->", color=C_BASE),
        color=C_BASE, fontsize=8
    )
    ax.annotate(
        f"Min DER: {min_der:.4f} pu",
        xy=(der_v.idxmin(), min_der),
        xytext=(der_v.idxmin() + 1.5, min_der + 0.008),
        arrowprops=dict(arrowstyle="->", color=C_DER),
        color=C_DER, fontsize=8
    )

    plt.tight_layout()
    return _save(fig, "01_voltage_profile_comparison.png", save_path)


# ── Plot 2 : 24-hour voltage envelope ─────────────────────────────────────────
def plot_timeseries_voltage(df, save_path="results"):
    """
    Max and min bus voltage over 24 hours with status shading.
    """
    fig, ax = plt.subplots(figsize=(12, 5))

    hours = df["Hour"]
    ax.fill_between(hours, df["Min_Voltage"], df["Max_Voltage"],
                    alpha=0.15, color=C_DER, label="Voltage envelope (min–max)")
    ax.plot(hours, df["Max_Voltage"], marker="^", markersize=5,
            color=C_DER, linewidth=1.8, label="Max bus voltage")
    ax.plot(hours, df["Min_Voltage"], marker="v", markersize=5,
            color=C_BASE, linewidth=1.8, label="Min bus voltage")

    ax.axhline(V_LOWER, color=C_LIMIT, linestyle=":", linewidth=1.2,
               label=f"{V_LOWER} pu lower limit")
    ax.axhline(V_UPPER, color=C_LIMIT, linestyle="-.", linewidth=1.2,
               label=f"{V_UPPER} pu upper limit")

    # shade violation hours
    for _, row in df.iterrows():
        if row["Status"] == "UNDERVOLTAGE":
            ax.axvspan(row["Hour"] - 0.5, row["Hour"] + 0.5,
                       color=C_UNDER, alpha=0.12)
        elif row["Status"] == "OVERVOLTAGE":
            ax.axvspan(row["Hour"] - 0.5, row["Hour"] + 0.5,
                       color=C_OVER, alpha=0.12)

    ax.set_xlim(-0.5, 23.5)
    ax.set_ylim(0.88, 1.08)
    ax.set_xticks(range(24))
    ax.set_xlabel("Hour of day", fontsize=11)
    ax.set_ylabel("Voltage magnitude (pu)", fontsize=11)
    ax.set_title("Hourly bus voltage envelope — IEEE-33 bus with DER",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    return _save(fig, "02_timeseries_voltage.png", save_path)


# ── Plot 3 : DER dispatch profiles ────────────────────────────────────────────
def plot_der_dispatch(df, save_path="results"):
    """
    Stacked view of PV generation, BESS power, EV load,
    and BESS state-of-charge over 24 hours.
    """
    fig = plt.figure(figsize=(13, 8))
    gs  = GridSpec(2, 1, figure=fig, hspace=0.35)

    # ── top panel: power dispatch ─────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0])
    hours = df["Hour"]

    ax1.bar(hours - 0.25, df["PV_MW"], width=0.25,
            color=C_PV, alpha=0.85, label="PV generation (MW)")
    ax1.bar(hours,        df["Load_Scale"] * 1.5, width=0.25,
            color=C_EV, alpha=0.7, label="EV charging load (MW, scaled)")

    # BESS: positive = discharge (green), negative = charge (purple)
    bess_charge    = df["BESS_MW"].clip(upper=0)
    bess_discharge = df["BESS_MW"].clip(lower=0)
    ax1.bar(hours + 0.25, bess_discharge, width=0.25,
            color=C_DISCHARGE, alpha=0.85, label="BESS discharging (MW)")
    ax1.bar(hours + 0.25, bess_charge,    width=0.25,
            color=C_BESS,  alpha=0.85, label="BESS charging (MW)")

    ax1.axhline(0, color="black", linewidth=0.8)
    ax1.set_xlim(-0.5, 23.5)
    ax1.set_xticks(range(24))
    ax1.set_xlabel("Hour of day", fontsize=10)
    ax1.set_ylabel("Power (MW)", fontsize=10)
    ax1.set_title("DER dispatch: PV · BESS · EV — 24-hour profile",
                  fontsize=12, fontweight="bold")
    ax1.legend(fontsize=8, ncol=2)
    ax1.grid(True, alpha=0.3, axis="y")

    # ── bottom panel: BESS SOC ────────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[1])
    ax2.fill_between(hours, df["SOC_pct"], alpha=0.3, color=C_BESS)
    ax2.plot(hours, df["SOC_pct"], marker="o", markersize=4,
             color=C_BESS, linewidth=1.8, label="BESS SoC (%)")
    ax2.axhline(20, color=C_UNDER, linestyle=":", linewidth=1,
                label="Min SoC limit (20 %)")
    ax2.axhline(90, color=C_OVER,  linestyle=":", linewidth=1,
                label="Max SoC limit (90 %)")
    ax2.set_xlim(-0.5, 23.5)
    ax2.set_ylim(0, 105)
    ax2.set_xticks(range(24))
    ax2.set_xlabel("Hour of day", fontsize=10)
    ax2.set_ylabel("SoC (%)", fontsize=10)
    ax2.set_title("BESS SoC — Hourly cycle",
                  fontsize=12, fontweight="bold")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    return _save(fig, "03_der_dispatch_and_soc.png", save_path)


# ── Plot 4 : Active power losses ──────────────────────────────────────────────
def plot_losses(df, base_loss, save_path="results"):
    """
    Hourly active power loss (MW) with base-case loss reference line.
    """
    fig, ax = plt.subplots(figsize=(12, 4))
    hours = df["Hour"]

    colors = [C_NORMAL if s == "NORMAL" else
              C_UNDER  if s == "UNDERVOLTAGE" else C_OVER
              for s in df["Status"]]

    ax.bar(hours, df["Loss_MW"], color=colors, alpha=0.8, label="Hourly loss (MW)")
    ax.axhline(base_loss, color=C_BASE, linestyle="--", linewidth=1.5,
               label=f"Base case loss ({base_loss:.4f} MW)")

    green_patch  = mpatches.Patch(color=C_NORMAL, label="Normal voltage")
    red_patch    = mpatches.Patch(color=C_UNDER,  label="Undervoltage hour")
    orange_patch = mpatches.Patch(color=C_OVER,   label="Overvoltage hour")
    ax.legend(handles=[green_patch, red_patch, orange_patch,
                        plt.Line2D([0], [0], color=C_BASE,
                                   linestyle="--", label=f"Base loss {base_loss:.4f} MW")],
              fontsize=8)

    ax.set_xlim(-0.5, 23.5)
    ax.set_xticks(range(24))
    ax.set_xlabel("Hour of day", fontsize=11)
    ax.set_ylabel("Active power loss (MW)", fontsize=11)
    ax.set_title("Hourly distribution network losses — with DER integration",
                 fontsize=13, fontweight="bold")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    return _save(fig, "04_power_losses.png", save_path)


# ── Plot 5 : Voltage violation summary ────────────────────────────────────────
def plot_violation_summary(df, save_path="results"):
    """
    Stacked bar showing buses under/over IEEE limits at each hour.
    """
    fig, ax = plt.subplots(figsize=(12, 4))
    hours = df["Hour"]

    ax.bar(hours, df["Buses_Under_095"], color=C_UNDER, alpha=0.8,
           label="No. of Buses below 0.95 pu")
    ax.bar(hours, df["Buses_Over_105"],
           bottom=df["Buses_Under_095"],
           color=C_OVER, alpha=0.8,
           label="No. of Buses above 1.05 pu")

    ax.set_xlim(-0.5, 23.5)
    ax.set_xticks(range(24))
    ax.set_xlabel("Hour of day", fontsize=11)
    ax.set_ylim(0.0, 25.0)
    ax.set_ylabel("Number of buses", fontsize=11)
    ax.set_title("Voltage violation Buses  per hour — IEEE-33 bus with DER",
                 fontsize=13, fontweight="bold")
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    return _save(fig, "05_voltage_violations.png", save_path)
