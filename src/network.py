"""
network.py
----------
Builds the IEEE 33-bus test network and attaches DER assets
(PV, BESS, EV charging) at buses selected on the basis of
voltage-sensitivity: buses 13 and 30 show the largest voltage
depressions in the base-case load flow.
"""

import pandapower as pp
import pandapower.networks as pn


def build_base_network():
    """
    Load the IEEE 33-bus radial distribution test system (Baran & Wu, 1989).
    Base voltage : 12.66 kV
    Total load   : 3.715 MW + j2.300 MVAr
    Returns
    -------
    net : pandapowerNet
    """
    net = pn.case33bw()
    return net


def add_ders(net, pv_mw=1.0, bess_mw=0.5, bess_mwh=2.0, ev_mw=1.0):
    """
    Add PV generators, a Battery Energy Storage System (BESS),
    and an EV charging load to the network.

    Bus selection rationale
    -----------------------
    Bus 13 : end of the longest feeder branch — lowest base-case voltage
    Bus 30 : tail of the second lateral — second weakest bus
    Bus 27 : mid-feeder node, representative EV charging point

    Parameters
    ----------
    net      : pandapowerNet  — base network (modified in place)
    pv_mw    : float          — rated PV output per unit (MW)
    bess_mw  : float          — BESS charge/discharge power rating (MW)
    bess_mwh : float          — BESS energy capacity (MWh)
    ev_mw    : float          — peak EV charging load (MW)

    Returns
    -------
    idx_pv1, idx_pv2 : int — sgen indices
    idx_bess         : int — storage index
    idx_ev           : int — load index
    """
    idx_pv1 = pp.create_sgen(
        net, bus=13, p_mw=pv_mw, q_mvar=0.0,
        name="PV_Bus14", type="PV"
    )
    idx_pv2 = pp.create_sgen(
        net, bus=30, p_mw=pv_mw, q_mvar=0.0,
        name="PV_Bus31", type="PV"
    )
    idx_bess = pp.create_storage(
        net, bus=30, p_mw=0.0,
        max_e_mwh=bess_mwh, soc_percent=50.0,
        min_e_mwh=0.2 * bess_mwh,
        name="BESS_Bus31"
    )
    idx_ev = pp.create_load(
        net, bus=27, p_mw=ev_mw, q_mvar=0.3,
        name="EV_Charging_Bus28"
    )
    return idx_pv1, idx_pv2, idx_bess, idx_ev
