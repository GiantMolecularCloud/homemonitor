# Homemonitor

This is a slightly adjusted version of ![CO2meter](https://github.com/vfilimonov/co2meter) by ![Vladimir Filimonov](https://github.com/vfilimonov). I plan to add more sensors (humidity, temperature) in the future, hence the new repo.

For details and installation, please see the ![CO2meter](https://github.com/vfilimonov/co2meter) page.


## setting up a systemd service

(Tested on a Raspberry Pi 3B+ with Raspbian Stretch Lite.)

- Make sure that homemonitor and homemonitor.service are executable.
- Adjust the paths in homemonitor.service to point to your copy of the homemonitor executable and your data/log directory of choice.
- Also adjust the local IP address to match your network. The one used here (192.168.179.41) is just an example!
- Copy the service to `/etc/systemd/system/`. This requires root!
  `sudo cp homemonitor.servivce /etc/systemd/system/`
- Start the service with `sudo systemctl start homemonitor.service`
- To automatically start homemonitor after reboot, run `sudo systemctl enable homemonitor.service`
- After changing the service (e.g. because the paths were wrong), it needs to be reload `sudo systemctl reload-daemon`
