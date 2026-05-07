"""
simulation.py
-------------
Load flow and 24-hour time-series simulation functions.

Load flow solver : Newton-Raphson (pandapower default)
Convergence tol  : 1e-8 pu (pandapower default)
"""

import numpy as np
import pandas as pd
import pandapower as pp


# ── IEEE voltage limits ────────────────────────────────────────────────────────
V_UPPER = 1.05   # pu  (IEEE 1547 / ANSI C84.1 Range A)
V_LOWER = 0.95   # pu


def run_base_loadflow(net):
    """
    Run Newton-Raphson load flow on the base network (no DER).

    Returns
    -------
    vm_pu : pd.Series  — bus voltage magnitudes (pu)
    loss  : float      — total active power loss (MW)
    """
    pp.runpp(net, algorithm="nr", calculate_voltage_angles=True)
    vm_pu = net.res_bus.vm_pu.copy()
    loss  = net.res_line.pl_mw.sum()
    return vm_pu, loss


def run_der_loadflow(net):
    """
    Run load flow with DER assets already added to net.

    Returns
    -------
    vm_pu : pd.Series
    loss  : float
    """
    pp.runpp(net, algorithm="nr", calculate_voltage_angles=True)
    vm_pu = net.res_bus.vm_pu.copy()
    loss  = net.res_line.pl_mw.sum()
    return vm_pu, loss


def build_profiles(hours=24):
    """
    Build normalised 24-hour PV generation and load demand profiles.

    PV  : sinusoidal curve peaking at solar noon (hour 12), zero at night
    Load: base load 0.6 pu with evening peak (hour 19) driven by
          residential demand and EV charging

    Returns
    -------
    time_steps  : list[int]
    pv_profile  : np.ndarray  (0–1 normalised)
    load_profile: np.ndarray  (0.6–1.2 normalised)
    """
    time_steps   = list(range(hours))
    t            = np.array(time_steps)

    pv_profile   = np.maximum(0, np.sin((np.pi / 12) * (t - 6)))
    load_profile = 0.6 + 0.6 * np.sin((np.pi / 12) * (t - 18)) ** 2

    return time_steps, pv_profile, load_profile


def bess_dispatch(hour, pv_scale, soc_percent,
                  p_rated=0.5, soc_max=90.0, soc_min=20.0):
    """
    Simple rule-based BESS dispatch strategy.

    Strategy
    --------
    Charge  : when PV surplus is available (06:00–15:00, PV > 30 %)
              and SOC is below max limit
    Discharge: during evening demand peak (18:00–22:00)
              and SOC is above min limit
    Idle    : all other hours

    Parameters
    ----------
    hour      : int   — current simulation hour (0–23)
    pv_scale  : float — normalised PV output (0–1)
    soc_percent: float — current state of charge (%)
    p_rated   : float — power rating (MW)
    soc_max   : float — upper SOC limit (%)
    soc_min   : float — lower SOC limit (%)

    Returns
    -------
    p_mw : float — positive = discharging, negative = charging, 0 = idle
    """
    if 6 <= hour < 15 and pv_scale > 0.3 and soc_percent < soc_max:
        return -p_rated          # charging
    elif 18 <= hour <= 22 and soc_percent > soc_min:
        return  p_rated          # discharging
    else:
        return  0.0              # idle


def run_timeseries(net, idx_pv1, idx_pv2, idx_bess, idx_ev,
                   pv_rated=2.0, ev_rated=1.5):
    """
    Run a 24-hour quasi-static time-series load flow.

    At each hour:
      1. Scale PV output by hourly profile
      2. Determine BESS dispatch (rule-based SOC management)
      3. Scale EV charging by demand profile
      4. Run Newton-Raphson load flow
      5. Record bus voltages, losses, and BESS SOC

    Parameters
    ----------
    net       : pandapowerNet (with DERs already added)
    idx_pv1/2 : sgen indices for the two PV units
    idx_bess  : storage index
    idx_ev    : load index for EV charging
    pv_rated  : float — PV rated power (MW)
    ev_rated  : float — EV peak load (MW)

    Returns
    -------
    df : pd.DataFrame with columns:
         Hour, PV_MW, Load_Scale, BESS_MW, SOC_pct,
         Max_Voltage, Min_Voltage, Loss_MW,
         Buses_Under_095, Buses_Over_105, Status
    """
    time_steps, pv_profile, load_profile = build_profiles()

    results  = []
    soc      = 50.0           # initial SOC (%)
    bess_cap = net.storage.at[idx_bess, "max_e_mwh"]   # MWh

    for t, pv_scale, load_scale in zip(time_steps, pv_profile, load_profile):

        # ── PV dispatch ───────────────────────────────────────────────────────
        p_pv = pv_rated * pv_scale
        net.sgen.at[idx_pv1, "p_mw"] = p_pv
        net.sgen.at[idx_pv2, "p_mw"] = p_pv

        # ── BESS dispatch ─────────────────────────────────────────────────────
        p_bess = bess_dispatch(t, pv_scale, soc)
        net.storage.at[idx_bess, "p_mw"] = p_bess

        # update SOC (energy in/out over 1 hour, simple efficiency η=0.95)
        eta = 0.95
        delta_e = -p_bess * 1.0           # MWh (negative p = charging)
        if p_bess < 0:                    # charging
            soc += (abs(delta_e) * eta / bess_cap) * 100
        else:                             # discharging
            soc -= (abs(delta_e) / eta / bess_cap) * 100
        soc = float(np.clip(soc, 10.0, 95.0))

        # ── EV load ───────────────────────────────────────────────────────────
        net.load.at[idx_ev, "p_mw"] = ev_rated * load_scale

        # ── Solve load flow ───────────────────────────────────────────────────
        pp.runpp(net, algorithm="nr", calculate_voltage_angles=True)

        vm          = net.res_bus.vm_pu
        loss        = net.res_line.pl_mw.sum()
        n_under     = int((vm < V_LOWER).sum())
        n_over      = int((vm > V_UPPER).sum())

        if n_over > 0:
            status = "OVERVOLTAGE"
        elif n_under > 0:
            status = "UNDERVOLTAGE"
        else:
            status = "NORMAL"

        results.append({
            "Hour"           : t,
            "PV_MW"          : round(p_pv, 3),
            "Load_Scale"     : round(load_scale, 3),
            "BESS_MW"        : round(p_bess, 3),
            "SOC_pct"        : round(soc, 1),
            "Max_Voltage"    : round(vm.max(), 4),
            "Min_Voltage"    : round(vm.min(), 4),
            "Loss_MW"        : round(loss, 4),
            "Buses_Under_095": n_under,
            "Buses_Over_105" : n_over,
            "Status"         : status,
        })

    return pd.DataFrame(results)
