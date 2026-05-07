"""
main.py
-------
Entry point for the IEEE 33-bus DER load flow study.

Run
---
    python src/main.py

Output
------
  results/01_voltage_profile_comparison.png
  results/02_timeseries_voltage.png
  results/03_der_dispatch_and_soc.png
  results/04_power_losses.png
  results/05_voltage_violations.png
  results/timeseries_results.csv
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import pandapower as pp
import pandapower.networks as pn

from network    import build_base_network, add_ders
from simulation import run_base_loadflow, run_der_loadflow, run_timeseries
from plots      import (plot_voltage_comparison, plot_timeseries_voltage,
                        plot_der_dispatch, plot_losses, plot_violation_summary)

RESULTS_DIR = "results"


def print_summary(base_v, der_v, base_loss, df):
    print("\n" + "=" * 60)
    print("  IEEE 33-BUS DER LOAD FLOW — RESULTS SUMMARY")
    print("=" * 60)

    print("\n── Steady-State Load Flow ──────────────────────────────")
    print(f"  Min voltage  — Base case : {base_v.min():.4f} pu  (Bus {base_v.idxmin()})")
    print(f"  Min voltage  — With DER  : {der_v.min():.4f} pu  (Bus {der_v.idxmin()})")
    improvement = (der_v.min() - base_v.min()) * 100
    print(f"  Improvement             : +{improvement:.2f} %")

    print(f"\n  Max voltage  — Base case : {base_v.max():.4f} pu")
    print(f"  Max voltage  — With DER  : {der_v.max():.4f} pu")

    buses_under_base = int((base_v < 0.95).sum())
    buses_under_der  = int((der_v  < 0.95).sum())
    print(f"\n  Buses below 0.95 pu — Base : {buses_under_base}")
    print(f"  Buses below 0.95 pu — DER  : {buses_under_der}")

    print(f"\n  Total active loss — Base : {base_loss:.4f} MW")

    print("\n── 24-Hour Time-Series ─────────────────────────────────")
    print(f"  Avg hourly loss       : {df['Loss_MW'].mean():.4f} MW")
    print(f"  Max hourly loss       : {df['Loss_MW'].max():.4f} MW  (Hour {df.loc[df['Loss_MW'].idxmax(), 'Hour']})")
    print(f"  Min hourly loss       : {df['Loss_MW'].min():.4f} MW  (Hour {df.loc[df['Loss_MW'].idxmin(), 'Hour']})")
    print(f"\n  Normal hours          : {(df['Status'] == 'NORMAL').sum()}")
    print(f"  Undervoltage hours    : {(df['Status'] == 'UNDERVOLTAGE').sum()}")
    print(f"  Overvoltage hours     : {(df['Status'] == 'OVERVOLTAGE').sum()}")

    print(f"\n  BESS final SOC        : {df['SOC_pct'].iloc[-1]:.1f} %")
    print(f"  Peak PV generation    : {df['PV_MW'].max():.3f} MW  (Hour {df.loc[df['PV_MW'].idxmax(), 'Hour']})")
    print("=" * 60 + "\n")


def main():
    print("\n[1/6] Building base network ...")
    net_base = build_base_network()
    base_v, base_loss = run_base_loadflow(net_base)
    print(f"      Base case min voltage : {base_v.min():.4f} pu")
    print(f"      Base case total loss  : {base_loss:.4f} MW")

    print("\n[2/6] Adding DER assets ...")
    net_der = build_base_network()
    idx_pv1, idx_pv2, idx_bess, idx_ev = add_ders(net_der)
    der_v, der_loss = run_der_loadflow(net_der)
    print(f"      DER case min voltage  : {der_v.min():.4f} pu")
    print(f"      DER case total loss   : {der_loss:.4f} MW")

    print("\n[3/6] Running 24-hour time-series simulation ...")
    net_ts = build_base_network()
    i_pv1, i_pv2, i_bess, i_ev = add_ders(net_ts)
    df = run_timeseries(net_ts, i_pv1, i_pv2, i_bess, i_ev)
    csv_path = os.path.join(RESULTS_DIR, "timeseries_results.csv")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    df.to_csv(csv_path, index=False)
    print(f"      Time-series CSV saved → {csv_path}")

    print("\n[4/6] Generating plots ...")
    plot_voltage_comparison(base_v, der_v,             save_path=RESULTS_DIR)
    plot_timeseries_voltage(df,                        save_path=RESULTS_DIR)
    plot_der_dispatch(df,                              save_path=RESULTS_DIR)
    plot_losses(df, base_loss,                         save_path=RESULTS_DIR)
    plot_violation_summary(df,                         save_path=RESULTS_DIR)

    print("\n[5/6] Results summary ...")
    print_summary(base_v, der_v, base_loss, df)

    print("[6/6] Done. All outputs in /results\n")


if __name__ == "__main__":
    main()
