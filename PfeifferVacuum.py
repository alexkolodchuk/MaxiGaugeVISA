#!/usr/bin/env python
# -*- encoding: UTF8 -*-

# Fork author: Aleksey Kolodchuk, kav110 AT campus.mephi.ru

# This file is part of MaxiGauge-VISA.
#
# MaxiGauge-VISA is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# MaxiGauge-VISA is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with MaxiGauge-VISA. If not, see <https://www.gnu.org/licenses/>.


### This module depends on PyVISA. Please follow the installation instructions here:
### https://pyvisa.readthedocs.io/en/latest/introduction/getting.html


import pyvisa
import time
import signal
import math
from enum import Enum
from threading import Thread, Event


class PressureReading:
    '''Объект, представляющий результат считывания давления с инструмента.
    
    Параметры
    ---------
    id : int
        Номер датчика, с которого произведено считывание - в отрезке от 1 до 6.
    status : int
        Код статуса считывания данных с датчика - в отрезке от 0 до 6.
    pressure : float
        Значение считанного давления.
    '''
    def __init__(self, id: int, status: int, pressure: float):
        if int(id) not in range(1,7): raise MaxiGaugeError('Pressure Gauge ID must be between 1-6')
        self.id = int(id)
        if int(status) not in PRESSURE_READING_STATUS.keys(): raise MaxiGaugeError('The Pressure Status must be in the range %s' % PRESSURE_READING_STATUS.keys())
        self.status = int(status)
        self.pressure = float(pressure)

    def statusMsg(self) -> str:
        '''Геттер для статуса считывания давления.
        
        Возвращает: str - статус считывания давления.
        '''
        return PRESSURE_READING_STATUS[self.status]

    def __repr__(self):
        return f'Gauge #{self.id}: Status {self.status} ({self.statusMsg()}), Pressure: {self.pressure} mbar\n'


class M(Enum):...
class C(Enum):...

class MaxiGauge:
    '''Обёртка для сеанса ввода/вывода с инструментом MaxiGauge™ Pfeiffer Vacuum TPG256A.
    Документация к методам здесь ссылается на контент в его официальном англоязычном мануале.
    
    Параметры 
    ---------
    resourceName : str
        Адрес ресурса инструмента.
    baud : int
        Скорость передачи данных в бодах (по умолчанию: 9600).
    debug : bool
        Включен ли режим отладки (по умолчанию: False).
        
    Исключения при инициализации
    ----------
    ValueError: Реализация VISA не найдена.
    pyvisa.errors.VisaIOError: Запрашиваемое устройство отсуствует.
    '''
    def __init__(self, resource_name: str, baud=9600, debug=False):
        self.debug = debug
        self.logfile_name = 'tpg256a-data.txt'
        
        try:
            rm = pyvisa.ResourceManager()
            self.connection = rm.open_resource(resource_name, baudrate=baud, open_timeout=0.2)
        except ValueError:
            raise MaxiGaugeError('VISA backend not found. Take a look at https://pyvisa.readthedocs.io/en/latest/introduction/getting.html#backend')
        except pyvisa.errors.VisaIOError:
            raise MaxiGaugeError('Instrument not found at the address.')
        
        #self.send(Controls.ETX) ### Оставлю на случай, если понадобится сбрасывать устройство при подключении.

    def checkDevice(self) -> str:
        '''Получить информацию о контрасте экрана и нажатых кнопках на инструменте.
        
        Возвращает: str - искомая информация.
        '''
        return f'''The Display Contrast is currently set to {self.displayContrast()} (out of 20).
Keys since MaxiGauge was switched on: {", ".join(map(str, self.pressedKeys()))} (out of 1,2,3,4,5).\n'''

    def pressedKeys(self) -> list[bool]:
        '''Получить информацию о нажатых прямо сейчас кнопках на инструменте.
        
        Возвращает: list[bool] - список из 5 значений True/False, описывающих, какие кнопки нажаты, а какие - нет.
        '''
        keys = int(self.send(Mnemonics.TKB, 1)[0])
        pressed_keys = []
        for i in range(4, -1, -1): ### Математика для пересчёта возвращаемого десятичного числа, в двоичное число
            if keys/2**i == 1:
                pressed_keys.append(i+1)
                keys = keys%2**i
        pressed_keys.reverse()
        return list(map(bool, pressed_keys))

    def displayContrast(self, new_contrast: None) -> int:
        '''Получить текущую контрастность экрана или установить новую (если она передана).
        
        Параметры
        ---------
        newContrast : int|None
            Контрастность экрана - целое число в отрезке от 0 до 20 или None (по умолчанию: None).
        
        Возвращает: int - контрастность экрана.
        '''
        if new_contrast == None: return int(self.send(Mnemonics.DCC, 1)[0])
        else: return int(self.send(Mnemonics.DCC+','+str(new_contrast), 1)[0])

    def pressures(self) -> list[PressureReading]:
        '''Считать значения на всех датчиках инструмента.
        
        Возвращает: list[PressureReading] - список из данных, собранных с каждого датчика.
        '''
        return [self.pressure(i+1) for i in range(6)]

    def pressure(self, sensor: int) -> PressureReading:
        '''Считать значение на датчике инструмента.
        
        Параметры
        ---------
        sensor : int
            Номер датчика - число в отрезке от 1 до 6.
        
        Возвращает: PressureReading - считанные с датчика данные.
        
        Исключения
        ----------
        MaxiGaugeError: введён неверный номер датчика или 
        '''
        if sensor < 1 or sensor > 6:
            raise MaxiGaugeError('Sensor can only be between 1 and 6. You choose ' + str(sensor))
        reading = self.send(Mnemonics.PR+str(sensor), 1)  ### результат будет в виде x,x.xxxEsx <CR><LF> (см. стр. 88)
        try:
            r = reading[0].split(',')
            status = int(r[0])
            pressure = float(r[-1])
        except:
            raise MaxiGaugeError('Problem interpreting the returned line:\n'+str(reading))
        return PressureReading(sensor, status, pressure)

    def signalHandler(self, sig, frame):
        '''Остановить непрерывное считывание значений со всех датчиков инструмента.
        '''
        self.stopping_continuous_update.set()
        signal.signal(signal.SIGINT, signal.SIG_DFL)

    def startContinuousPressureUpdates(self, update_time: float, log_every = 0):
        '''Запустить непрерывное считывание значений со всех датчиков инструмента.
        
        Параметры
        ---------
        updateTime : float
            Время (в секундах) между двумя соседними считываниями.
        logEvery : int
            Время (в секундах) между двумя соседними записями значений в лог-файл.
        '''
        self.stopping_continuous_update =  Event()
        signal.signal(signal.SIGINT, self.signalHandler)
        self.update_time = update_time
        self.log_every = log_every
        self.update_counter = 1
        self.t = Thread(target = self.continuousPressureUpdates)
        self.t.daemon = True
        self.t.start()

    def continuousPressureUpdates(self):
        '''Бесконечный цикл считывания и записи в лог-файл значений давления с инструмента. \
        Пока ключ stopping_continuous_update не True, он выполняет следующие действия на повторе:
            1. Кэширует показания датчиков и время их снятия
            2. Записывает их в логфайл
            3. (Иногда) записывает усреднённые показания датчиков и непонятно пока, какое, время снятия
            4. Как-то сложно вычисляет время ожидания до следующего цикла
        '''
        cache: list[list[float]] = []
        while not self.stopping_continuous_update.is_set():
            start_time = time.time()
            self.update_counter += 1
            self.cached_pressures = self.pressures()
            cache.append([time.time()] + [sensor.pressure if sensor.status in [0,1,2] else float('nan') for sensor in self.cached_pressures] )
            if self.log_every > 0 and (self.update_counter%self.log_every == 0):
                logtime = cache[self.log_every/2][0]
                avgs = [(sum(vals)/self.log_every) for vals in list(zip(*cache))[1:]]
                self.logToFile(logtime=logtime, logvalues=avgs)
                cache = []
            time.sleep(0.1) # we want a minimum pause of 0.1 s
            while not self.stopping_continuous_update.isSet() and (self.update_time - (time.time()-start_time) > .2):
                time.sleep(.2)
            time.sleep(max([0., self.update_time - (time.time()-start_time)]))
        #sys.stderr.write(line)
        if self.log_every > 0 and (self.update_counter%self.log_every == 0):
            self.flushLogfile()

    def logToFile(self, logtime: float = None, logvalues: list[float] = None):
        '''Записать значения давления в лог-файл.
        
        Параметры
        ---------
        logtime : float
            Время, которому соответствует запись (по умолчанию: None, записанным значениям будет соответствовать текущее время устройства).
        logvalues : list[float]
            Значения, которые необходимо записать (по умолчанию: None, в файл запишутся все кэшированные значения).
        '''
        try:
            self.logfile
        except:
            self.logfile = open(self.logfilename, 'a')
        if not logtime:
            logtime = time.time()
        if not logvalues:
            logvalues = [sensor.pressure if sensor.status in [0,1,2] else float('nan') for sensor in self.cached_pressures]
        line = str(logtime) + ', ' + ', '.join(['%.3E' % val if not math.isnan(val) else '' for val in logvalues])
        self.logfile.write(line+'\n')

    def flushLogfile(self):
        '''Очистить буфер записи лог-файла.
        '''
        try:
            self.logfile.flush()
            from os import fsync
            fsync(self.logfile)
        except:
            pass

    def debugMessage(self, message):
        '''Вывести отладочное сообщение (при MaxiGauge.debug = True).
        
        Параметры
        ---------
        message : str
            Сообщение на вывод.
        '''
        if self.debug: print(repr(message))

    def send(self, mnemonic: M | str, num_enquiries = 0) -> str:
        '''Отправить мнемонику инструменту и получить полный ответ.
        
        Параметры
        ---------
        mnemonic : Mnemonics или str
            Мнемоника - ASCII-строка без символов окончания, отправляемая инструменту. Также мнемонику можно выбрать из перечисления Mnemonics.
        numEnquiries : str
            Количество запросов на получение данных (по умолчанию: 0).
            
        Возвращает: str - ASCII-строка с запрошенными данными.
        '''
        self.connection.clear()
        self.write(mnemonic+LINE_TERMINATION)       # Отправка команды
        self.getACQorNAK()                          # Получение подтверждения/отказа о команде
        response = []
        for i in range(num_enquiries):
            self.enquire()                          # Запрос на получение данных
            response.append(self.read())            # Получение данных
        return response

    def write(self, what: M | str):
        '''Отправить сообщение инструменту.
        
        Параметры
        ---------
        what : str
            Сообщение на отправку.
        '''
        self.debugMessage(what)
        self.connection.write(what)

    def enquire(self):
        '''Отправить инструменту строку ENQ - запрос за передачу данных.
        '''
        self.write(C.ENQ)

    def read(self) -> str:
        '''Прочитать информацию с инструмента до первого конца строки.
        
        Возвращает: str - искомое сообщение до первого <CR><LF> (стр. 82).
        '''
        return self.connection.read()

    def getACQorNAK(self) -> str:
        '''Обработать получение подтверждения/отказа на передачу данных.
        
        Возвращает: str - полученное с инструмента сообщение.
        '''
        return_code = self.connection.read()
        self.debugMessage(return_code)
        
        # В контроллере Франкфуртского университета есть баг с командой DCC, при котором контроллер забывает ответить ACQ/NAK. Оставлю этот exception на случай, если с нашим произойдёт то же самое:
        if len(return_code)<3: raise MaxiGaugeError('Only received a line termination from MaxiGauge. Was expecting ACQ or NAK.')
        
        # Отказ 😳
        if len(return_code) > 2 and return_code[-3] == C.NAK:
            self.enquire()
            error = self.read().split(',', 1)
            print(repr(error))
            errmsg = {
                'System Error': ERR_CODES[0][int(error[0])],
                'Gauge Error': ERR_CODES[1][int(error[1])]
            }
            raise MaxiGaugeNAKError(errmsg)
        
        if len(return_code) > 2 and return_code[-3] != C.ACQ:
            raise MaxiGaugeError('Expecting ACQ or NAK from MaxiGauge but neither were sent.')
        
        # 100% респекта тем ответам, которые дошли до этой строчки
        return return_code[:-(len(LINE_TERMINATION)+1)]
        
    def __del__(self):
        # Удаление ресурса включает в себя остановка идущих операций ввода-вывода (если такие есть)
        # и закрытие сессии с ресурсом
        
        if hasattr(self, 'stopping_continuous_update'):
            self.stopping_continuous_update.set()
        #self.send(C.ETX)
        if hasattr(self, 'connection') and self.connection: self.connection.close()


### ------ определяем ошибки, которые могут возникнуть ------

class MaxiGaugeError(Exception):
    pass

class MaxiGaugeNAKError(MaxiGaugeError):
    pass

### --- Управляющие cимволы, как определены на стр. 81 английского ---
###              мануала для Pfeiffer Vacuum TPG256A
class C(Enum):
    ETX = '\x03', # End of Text (Ctrl-C)   Reset the interface
    CR  = '\x0D', # Carriage Return        Go to the beginning of line
    LF  = '\x0A', # Line Feed              Advance by one line
    ENQ = '\x05', # Enquiry                Request for data transmission
    ACQ = '\x06', # Acknowledge            Positive report signal
    NAK = '\x15', # Negative Acknowledge   Negative report signal
    ESC = '\x1b', # Escape

LINE_TERMINATION = C.CR + C.LF # CR, LF и CRLF все возможны (стр. 82)


### Мнемоники, как определены на стр. 85
class M(Enum):
  BAU = 'BAU', # Baud rate                           Baud rate                                    95
  CAx = 'CAx', # Calibration factor Sensor x         Calibration factor sensor x (1 ... 6)        92
  CID = 'CID', # Measurement point names             Measurement point names                      88
  DCB = 'DCB', # Display control Bargraph            Bargraph                                     89
  DCC = 'DCC', # Display control Contrast            Display control contrast                     90
  DCD = 'DCD', # Display control Digits              Display digits                               88
  DCS = 'DCS', # Display control Screensave          Display control screensave                   90
  DGS = 'DGS', # Degas                               Degas                                        93
  ERR = 'ERR', # Error Status                        Error status                                 97
  FIL = 'FIL', # Filter time constant                Filter time constant                         92
  FSR = 'FSR', # Full scale range of linear sensors  Full scale range of linear sensors           93
  LOC = 'LOC', # Parameter setup lock                Parameter setup lock                         91
  NAD = 'NAD', # Node (device) address for RS485     Node (device) address for RS485              96
  OFC = 'OFC', # Offset correction                   Offset correction                            93
  PNR = 'PNR', # Program number                      Program number                               98
  PRx = 'PRx', # Status, Pressure sensor x (1 ... 6) Status, Pressure sensor x (1 ... 6)          88
  PUC = 'PUC', # Underrange Ctrl                     Underrange control                           91
  RSX = 'RSX', # Interface                           Interface                                    94
  SAV = 'SAV', # Save default                        Save default                                 94
  SCx = 'SCx', # Sensor control                      Sensor control                               87
  SEN = 'SEN', # Sensor on/off                       Sensor on/off                                86
  SPx = 'SPx', # Set Point Control Source for Relay xThreshold value setting, Allocation          90
  SPS = 'SPS', # Set Point Status A,B,C,D,E,F        Set point status                             91
  TAI = 'TAI', # Test program A/D Identify           Test A/D converter identification inputs    100
  TAS = 'TAS', # Test program A/D Sensor             Test A/D converter measurement value inputs 100
  TDI = 'TDI', # Display test                        Display test                                 98
  TEE = 'TEE', # EEPROM test                         EEPROM test                                 100
  TEP = 'TEP', # EPROM test                          EPROM test                                   99
  TID = 'TID', # Sensor identification               Sensor identification                       101
  TKB = 'TKB', # Keyboard test                       Keyboard test                                99
  TRA = 'TRA', # RAM test                            RAM test                                     99
  UNI = 'UNI', # Unit of measurement (Display)       Unit of measurement (pressure)               89
  WDT = 'WDT', # Watchdog and System Error Control   Watchdog and system error control           101


### Коды ошибок, как определены на стр. 97
ERR_CODES = [
  {
        0: 'No error',
        1: 'Watchdog has responded',
        2: 'Task fail error',
        4: 'IDCX idle error',
        8: 'Stack overflow error',
       16: 'EPROM error',
       32: 'RAM error',
       64: 'EEPROM error',
      128: 'Key error',
     4096: 'Syntax error',
     8192: 'Inadmissible parameter',
    16384: 'No hardware',
    32768: 'Fatal error'
  } ,
  {
        0: 'No error',
        1: 'Sensor 1: Measurement error',
        2: 'Sensor 2: Measurement error',
        4: 'Sensor 3: Measurement error',
        8: 'Sensor 4: Measurement error',
       16: 'Sensor 5: Measurement error',
       32: 'Sensor 6: Measurement error',
      512: 'Sensor 1: Identification error',
     1024: 'Sensor 2: Identification error',
     2048: 'Sensor 3: Identification error',
     4096: 'Sensor 4: Identification error',
     8192: 'Sensor 5: Identification error',
    16384: 'Sensor 6: Identification error',
  }
]

### Статусы считывания давления, как определены на стр. 88
PRESSURE_READING_STATUS = {
  0: 'Measurement data okay',
  1: 'Underrange',
  2: 'Overrange',
  3: 'Sensor error',
  4: 'Sensor off',
  5: 'No sensor',
  6: 'Identification error'
}
