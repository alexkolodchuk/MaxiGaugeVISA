#!/usr/bin/env python

### Load the module:
import sys
sys.path.append('../MaxiGaugeVISA')

from PfeifferVacuum import MaxiGauge, MaxiGaugeError
import time


### Initialize an instance of the MaxiGauge controller with
### the handle of the serial terminal it is connected to
mg = MaxiGauge('/dev/ttyUSB1')
logfile = open('measurement-data.txt', 'a')

### Read out the pressure gauges
while True:
    start_time = time.time()

    try:
        ps = mg.pressures()
    except MaxiGaugeError as e:
        print(e)
        continue
    line = "%d, " % int(time.time())
    for sensor in ps:
        #print(sensor)
        if sensor.status in [0,1,2]:
            line += "%.3E" % sensor.pressure
        line += ", "
    line = line[0:-2] # убрать последнюю точку и пробел
    print(line)
    sys.stdout.flush()
    logfile.write(line+'\n')
    logfile.flush()

    # do this every second
    end_time = time.time()-start_time
    time.sleep(max([0.0, 1-end_time]))
