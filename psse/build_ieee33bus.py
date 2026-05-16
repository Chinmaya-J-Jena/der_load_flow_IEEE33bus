# -*- coding: utf-8 -*-
"""
build_ieee33bus.py
------------------
Builds the IEEE 33-bus radial distribution test system (Baran & Wu, 1989)
inside PSS/E v33 using the PSSPY API.
Python 2.7 compatible.

HOW TO RUN:
-----------
From Windows command prompt:
    "C:\Python27\python.exe" build_ieee33bus.py

OUTPUT:
-------
    IEEE33bus.sav         - PSS/E saved case file
    IEEE33bus_export.raw  - exported RAW file for backup
"""

import os
import sys

# Locate and import PSSPY
PSSE_PATH = r"C:\Program Files (x86)\PTI\PSSE33\PSSBIN"
if PSSE_PATH not in sys.path:
    sys.path.insert(0, PSSE_PATH)

import psspy
import redirect

redirect.psse2py()

psspy.psseinit(buses=50)
psspy.newcase()
psspy.basdat(1, [50, 0], [100.0, 50.0])

print("\n" + "="*55)
print("  Building IEEE 33-Bus System in PSS/E")
print("="*55)

# 1. BUS DATA
print("\n[1/5] Adding buses...")

buses = [
    (1,  12.66, 3),
    (2,  12.66, 1),(3,  12.66, 1),(4,  12.66, 1),(5,  12.66, 1),
    (6,  12.66, 1),(7,  12.66, 1),(8,  12.66, 1),(9,  12.66, 1),
    (10, 12.66, 1),(11, 12.66, 1),(12, 12.66, 1),(13, 12.66, 1),
    (14, 12.66, 1),(15, 12.66, 1),(16, 12.66, 1),(17, 12.66, 1),
    (18, 12.66, 1),(19, 12.66, 1),(20, 12.66, 1),(21, 12.66, 1),
    (22, 12.66, 1),(23, 12.66, 1),(24, 12.66, 1),(25, 12.66, 1),
    (26, 12.66, 1),(27, 12.66, 1),(28, 12.66, 1),(29, 12.66, 1),
    (30, 12.66, 1),(31, 12.66, 1),(32, 12.66, 1),(33, 12.66, 1),
]

for bus_num, base_kv, bus_type in buses:
    name = "BUS%-4d" % bus_num
    psspy.bus_data_3(
        bus_num,
        [bus_type, 1, 1, 1],
        [base_kv, 1.0, 0.0, 1.1, 0.9],
        name
    )
print("    %d buses added." % len(buses))

# 2. LOAD DATA
print("\n[2/5] Adding loads...")

loads = [
    (2,0.100,0.060),(3,0.090,0.040),(4,0.120,0.080),(5,0.060,0.030),
    (6,0.060,0.020),(7,0.200,0.100),(8,0.200,0.100),(9,0.060,0.020),
    (10,0.060,0.020),(11,0.045,0.030),(12,0.060,0.035),(13,0.060,0.035),
    (14,0.120,0.080),(15,0.060,0.010),(16,0.060,0.020),(17,0.060,0.020),
    (18,0.090,0.040),(19,0.090,0.040),(20,0.090,0.040),(21,0.090,0.040),
    (22,0.090,0.040),(23,0.090,0.050),(24,0.420,0.200),(25,0.420,0.200),
    (26,0.060,0.025),(27,0.060,0.025),(28,0.060,0.020),(29,0.120,0.070),
    (30,0.200,0.600),(31,0.150,0.070),(32,0.210,0.100),(33,0.060,0.040),
]

for bus, p_mw, q_mvar in loads:
    psspy.load_data_4(
        bus, r"""1""",
        [1, 1, 1, 1, 1, 1],
        [p_mw, q_mvar, 0.0, 0.0, 0.0, 0.0, 1]
    )

total_p = sum(l[1] for l in loads)
total_q = sum(l[2] for l in loads)
print("    %d loads added." % len(loads))
print("    Total load: %.3f MW + j%.3f MVAr" % (total_p, total_q))

# 3. GENERATOR
print("\n[3/5] Adding slack generator at Bus 1...")

psspy.machine_data_4(
    1, r"""1""",
    [1, 1, 1, 1, 1, 1],
    [0.0, 0.0, 9999.0, -9999.0, 9999.0, -9999.0,
     100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0, 0, 1]
)
print("    Slack generator added at Bus 1.")

# 4. BRANCH DATA
print("\n[4/5] Adding branches...")

BASE_Z = (12.66 ** 2) / 100.0

branches_ohm = [
    (1,2,0.0922,0.0470),(2,3,0.4930,0.2511),(3,4,0.3660,0.1864),
    (4,5,0.3811,0.1941),(5,6,0.8190,0.7070),(6,7,0.1872,0.6188),
    (7,8,0.7114,0.2351),(8,9,1.0300,0.7400),(9,10,1.0440,0.7400),
    (10,11,0.1966,0.0650),(11,12,0.3744,0.1238),(12,13,1.4680,1.1550),
    (13,14,0.5416,0.7129),(14,15,0.5910,0.5260),(15,16,0.7463,0.5450),
    (16,17,1.2890,1.7210),(17,18,0.7320,0.5740),(2,19,0.1640,0.1565),
    (19,20,1.5042,1.3554),(20,21,0.4095,0.4784),(21,22,0.7089,0.9373),
    (3,23,0.4512,0.3083),(23,24,0.8980,0.7091),(24,25,0.8960,0.7011),
    (6,26,0.2030,0.1034),(26,27,0.2842,0.1447),(27,28,1.0590,0.9337),
    (28,29,0.8042,0.7006),(29,30,0.5075,0.2585),(30,31,0.9744,0.9630),
    (31,32,0.3105,0.3619),(32,33,0.3410,0.5302),
]

for from_bus, to_bus, r_ohm, x_ohm in branches_ohm:
    r_pu = r_ohm / BASE_Z
    x_pu = x_ohm / BASE_Z
    psspy.branch_data_3(
        from_bus, to_bus, r"""1""",
        [1, 1, 1, 1, 1, 1],
        [r_pu, x_pu, 0.0, 250.0, 250.0, 250.0,
         0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
    )

print("    %d branches added." % len(branches_ohm))
print("    Base impedance: %.4f ohms" % BASE_Z)

# 5. SOLVE AND SAVE
print("\n[5/5] Running Newton-Raphson load flow...")

psspy.solution_params_3(
    [0, 0, 0, 0, 0, 0, 0, 0],
    [1e-4, 1e-4, 99.0, 99.0, 100.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
)

ierr = psspy.fnsl([0, 0, 0, 1, 1, 0, 0, 0])

if ierr == 0:
    print("    Load flow CONVERGED successfully.")
else:
    print("    WARNING: Load flow error code %d" % ierr)

print("\n" + "="*55)
print("  LOAD FLOW RESULTS SUMMARY")
print("="*55)

ierr, vm       = psspy.abusreal(-1, 1, 'PU')
ierr, bus_nums = psspy.abusint(-1, 1, 'NUMBER')

if vm and bus_nums:
    voltages  = list(vm[0])
    buses_out = list(bus_nums[0])
    min_v     = min(voltages)
    max_v     = max(voltages)
    min_bus   = buses_out[voltages.index(min_v)]
    max_bus   = buses_out[voltages.index(max_v)]

    print("\n  Min bus voltage : %.4f pu  (Bus %d)" % (min_v, min_bus))
    print("  Max bus voltage : %.4f pu  (Bus %d)" % (max_v, max_bus))
    print("\n  Buses below 0.95 pu : %d" % sum(1 for v in voltages if v < 0.95))
    print("  Buses above 1.05 pu : %d" % sum(1 for v in voltages if v > 1.05))

    print("\n  Bus-by-Bus Voltage (pu):")
    print("  " + "-"*35)
    for b, v in zip(buses_out, voltages):
        flag = " *** BELOW LIMIT" if v < 0.95 else ""
        print("  Bus %2d : %.4f pu%s" % (b, v, flag))

ierr, plosses = psspy.systot('LOSS')
if not ierr:
    print("\n  Total active power loss  : %.4f MW"   % plosses.real)
    print("  Total reactive power loss: %.4f MVAr" % plosses.imag)

print("="*55)

script_dir = os.path.dirname(os.path.abspath(__file__))
sav_file   = os.path.join(script_dir, "IEEE33bus.sav")
raw_file   = os.path.join(script_dir, "IEEE33bus_export.raw")

psspy.save(sav_file)
print("\n  Case saved  : %s" % sav_file)

psspy.rawd_2(0, 1, [0, 0, 1, 0], 0, raw_file)
print("  RAW exported: %s" % raw_file)

print("\n  Done. Open IEEE33bus.sav in PSS/E to view the network.\n")
