## MaxiGaugeVISA

Это ПО для регистрации значений вакуумного давления
с помощью контроллера вакуумметра Pfeiffer-Vacuum MaxiGauge.

Оно позволяет выводит значения вакуумного давления и записывать его в лог-файл.

### Requirements

* [Python][] 3.8-3.11
* [PyVISA][] 1.14+ and [NI VISA][] 14+ to communicate with the MaxiGauge via the RS232 port.

### Credits

Philipp Klaus (pklaus) - thank you for writing the original software.

### License

Copyright (C) 2024 Aleksey Kolodchuk (Moscow Engineering Physics Institute) \
This software is licensed under GNU GPLv3 (see LICENSE.md for more information).

[Python]: http://www.python.org/getit/
[PyVISA]: https://github.com/pyvisa/pyvisa
[NI VISA]: https://www.ni.com/en/support/downloads/drivers/download.ni-visa.html
