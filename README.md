# Homemonitor

This is a slightly adjusted version of ![CO2meter](https://github.com/vfilimonov/co2meter) by ![Vladimir Filimonov](https://github.com/vfilimonov). The main difference for now is that the dashboard includes minimum/maximum markers for temperature and CO2 level. Note that I removed the homekit functionality because I don't need it.

 I plan to add more sensors (humidity, temperature) in the future, hence the new repo.

For details and installation, please see the ![CO2meter](https://github.com/vfilimonov/co2meter) page.

## Requirements
- libusb, hidapi; see ![CO2meter](https://github.com/vfilimonov/co2meter) for installation details; if problems occur check the issue there
- python packages: pandas, numpy, flask, matplotlib
- If homemonitor should run automatically as a service (see below), these python packages must be installed for the root user. By default services run under root, so user installations will cause an error "cannot import matplotlib". Install it for root with `sudo -H pip3 install matplotlib`

## setting up a systemd service

(Tested on a Raspberry Pi 3B+ with Raspbian Stretch Lite.)

- Make sure that homemonitor and homemonitor.service are executable.
- Adjust the paths in homemonitor.service to point to your copy of the homemonitor executable and your data/log directory of choice.
- Also adjust the local IP address to match your network. The one used here just happened to be the one assigned by my testing router!
- Copy the service to `/etc/systemd/system/`. This requires root!
  `sudo cp homemonitor.service /etc/systemd/system/`
- Start the service with `sudo systemctl start homemonitor.service`. It can be stopped with `sudo systemctl stop homemonitor.service`.
- To automatically start homemonitor after reboot, run `sudo systemctl enable homemonitor.service`.
- Changing the service (the file in `/etc/systemd/system/`) requires a reload: `sudo systemctl daemon-reload`
- A service can be restarted, e.g. to reload a now version of server.py by `sudo systemctl restart homemonitor.service`
- The log file (stdout, stderr)  is accessible through `sudo journalctl -u homemonitor`

