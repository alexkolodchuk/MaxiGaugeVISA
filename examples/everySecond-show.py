#!/usr/bin/env python

# Инициализация модулей
import sys
sys.path.append('../MaxiGaugeVISA')

from PfeifferVacuum import MaxiGauge, MaxiGaugeError
import time

# Подключение инструмента к программе
mg = MaxiGauge('/dev/ttyUSB1')

# Чтение данных
while True:
    start_time = time.time()

    try:
        ps = mg.pressures()
    except MaxiGaugeError as e:
        print(e)
        continue
    line = ""
    for sensor in ps:
        # вывод данных с датчиков
        if sensor.status in [0,1,2]: # если нормальный, ниже или выше порога
            line += str(sensor.pressure)
        line += ", "
    print(line[0:-2]) # убрать последнюю точку и пробел
    sys.stdout.flush()
    
    # и повторять каждую секунду
    end_time = time.time()-start_time
    time.sleep(max([0.0, 1.0-end_time]))
