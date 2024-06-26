#!/usr/bin/env python

### Load the module:
import sys
sys.path.append('../MaxiGaugeVISA')

from PfeifferVacuum import MaxiGauge

### Initialize an instance of the MaxiGauge controller with
### the handle of the serial terminal it is connected to
mg = MaxiGauge('/dev/ttyUSB0')

### Run the self check (not needed)
print(mg.checkDevice())

### Set device characteristics (here: change the display contrast)
print("Set the display contrast to:", mg.displayContrast(10))

### Read out the pressure gauges
print(mg.pressures())

### Display the value of the pressure gauges for 20 repeated read outs
for i in range(20):
    ps = mg.pressures()
    print("Sensor 1: %4e mbar" % ps[0].pressure + "Sensor 6: %4e mbar" % ps[5].pressure)