```
██████   █████  ███    ██  ██████  ███████ ██████  
██   ██ ██   ██ ████   ██ ██       ██      ██   ██ 
██   ██ ███████ ██ ██  ██ ██   ███ █████   ██████  
██   ██ ██   ██ ██  ██ ██ ██    ██ ██      ██   ██ 
██████  ██   ██ ██   ████  ██████  ███████ ██   ██ 
```

this is a unlocked hoc patches. Please do not daily drive this.<br>
It may kill your console and your cat.<br>

features:<br>
1375mV Mariko vmax, 1395mV erista vmax<br>
gpu vmax 1525mV<br>
RAM 1500mV VDD2/VDDQ<br>
Display 1325mV<br>
erista cpu 2601mhz<br>
mariko cpu 2907mhz<br>
erista gpu 1382mhz<br>
mariko gpu 1766mhz<br>

how to use:<br>

copy files to a cloned version of HOC source (in repo root)<br>
run python script to patch everything<br>
compile HOC and enjoy(?)<br>

this should unlock all HOC versions, so you can use in development 3.0.0, release 2.5.1 or a older version (if desired)<br>

tSkin temp unlock code to avoid overheating (put in system_settings.ini)<br>
```
[tc]
holdable_tskin=u32!0xEA60
touchable_tskin=u32!0xEA60
tskin_pcb_coefficients_console_on_fwdbg=str!"[4000, 90000]" 
tskin_pcb_coefficients_handheld_on_fwdbg=str!"[4000, 90000]" 
tskin_soc_coefficients_console_on_fwdbg=str!"[4000, 90000]" 
tskin_soc_coefficients_handheld_on_fwdbg=str!"[4000, 90000]" 
```
