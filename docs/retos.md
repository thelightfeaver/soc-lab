# Catálogo de retos

Sin spoilers: solo título, tema y lo que se practica.

| # | Reto | Dificultad | Categoría | Pts | Practicas |
|---|---|---|---|---|---|
| 01 | Fuerza bruta SSH | 🟢 Fácil | Análisis de logs | 100 | grep/awk/uniq sobre `auth.log` |
| 02 | Cabeceras de phishing | 🟢 Fácil | Phishing | 100 | Lectura de cabeceras `Received`, SPF/DMARC |
| 03 | PowerShell codificado | 🟢 Fácil | Endpoint | 100 | `-EncodedCommand`, Base64 UTF-16LE |
| 04 | Coincidencia de IOC | 🟢 Fácil | Threat Intelligence | 100 | Cruce de hashes con un feed |
| 05 | Panel de administración oculto | 🟢 Fácil | Web | 100 | Detección de escáneres de directorios |
| 06 | Consulta a dominio en lista negra | 🟢 Fácil | Red | 100 | Logs DNS y coincidencia por sufijo |
| 07 | Túnel DNS | 🟡 Medio | Red | 200 | Reensamblado de datos en subdominios |
| 08 | Beaconing de C2 | 🟡 Medio | Red | 200 | Análisis de periodicidad |
| 09 | Inyección SQL | 🟡 Medio | Web | 200 | URL decoding, UNION SELECT |
| 10 | Cuenta creada por el intruso | 🟡 Medio | Windows | 200 | Correlación 4624/4720 por LogonId |
| 11 | Persistencia en cron | 🟡 Medio | Linux Forense | 200 | Archivos ocultos, cron, Base64 |
| 12 | Árbol de procesos de una macro | 🟡 Medio | Endpoint | 200 | Sysmon 1, ParentProcessId |
| 13 | Movimiento lateral | 🟠 Difícil | Windows | 300 | Mapeo IP→host, línea temporal |
| 14 | Exfiltración fuera de horario | 🟠 Difícil | Red | 300 | NetFlow, filtrado temporal y por red |
| 15 | Ransomware y reutilización de PID | 🟠 Difícil | Endpoint | 300 | Correlación temporal con PIDs reutilizados |
| 16 | Configuración cifrada con XOR | 🟠 Difícil | Malware | 300 | Fuerza bruta de XOR de un byte |
| 17 | JWT con alg none | 🟠 Difícil | Web | 300 | Decodificación JWT, falsificación de tokens |
| 18 | Exfiltración HTTP en PCAP | 🟣 Experto | Forense de red | 500 | Reensamblado TCP, gzip |
| 19 | Incidente multietapa | 🟣 Experto | Respuesta a incidentes | 500 | Correo → payload → proxy → DHCP |
| 20 | Manipulación de logs | 🟣 Experto | Linux Forense | 500 | Normalización y diff contra syslog central |

**Total: 4.800 puntos.**
