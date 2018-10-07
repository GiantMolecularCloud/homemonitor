# Homemonitor

This is a slightly adjusted version of ![CO2meter](https://github.com/vfilimonov/co2meter) by ![Vladimir Filimonov](https://github.com/vfilimonov). The main difference for now is that the dashboard includes minimum/maximum markers for temperature and CO2 level. Note that I removed the homekit functionality because I don't need it.

 I plan to add more sensors (humidity, temperature) in the future, hence the new repo.

For details and installation, please see the ![CO2meter](https://github.com/vfilimonov/co2meter) page.


## setting up a systemd service

(Tested on a Raspberry Pi 3B+ with Raspbian Stretch Lite.)

- Make sure that homemonitor and homemonitor.service are executable.
- Adjust the paths in homemonitor.service to point to your copy of the homemonitor executable and your data/log directory of choice.
- Also adjust the local IP address to match your network. The one used here just happened to be the one assigned by my testing router!
- Copy the service to `/etc/systemd/system/`. This requires root!
  `sudo cp homemonitor.service /etc/systemd/system/`
- Start the service with `sudo systemctl start homemonitor.service`. Can be stopped with `sudo systemctl start homemonitor.service`.
- To automatically start homemonitor after reboot, run `sudo systemctl enable homemonitor.service`.
- After changing the service (e.g. because the paths were wrong), it needs to be reload `sudo systemctl reload-daemon`.
