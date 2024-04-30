## MaxiGaugeVISA

Это ПО для регистрации значений вакуумного давления
с помощью контроллера вакуумметра Pfeiffer-Vacuum MaxiGauge.

Оно позволяет выводит значения вакуумного давления и записывать его в лог-файл.

### Требования к установке

* [Python][] 3.8-3.11
* [PyVISA][] 1.14+ и [NI VISA][] 14+ для связи с MaxiGauge через порт RS232.

### Спасибо

Philipp Klaus (pklaus) - thank you for writing the original software.

### Лицензия

Copyright (C) 2024 Aleksey Kolodchuk (Moscow Engineering Physics Institute) \
This software is licensed under GNU GPLv3 (see LICENSE.md for more information).

[Python]: http://www.python.org/getit/
[PyVISA]: https://github.com/pyvisa/pyvisa
[NI VISA]: https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html
