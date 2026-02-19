# udpu-client-golang

## Cross Compilation Libraries

You can use this repository for cross-compilation libraries: http://more.musl.cc/

## Standard Compilation
go build -o client

## Cross Compilation Example
./build.sh

## Running the Client
Execute the client with specific parameters:

sudo ./client --discovery-host=161.184.221.236 --discovery-port=8888 --mac-interface=br-lan --download-path=/tmp/tmp

### Default Values
- `--mac-interface` defaults to `br-lan`
- `--download-path` defaults to `/tmp`

## LED Control Setup in OpenWrt
1. Copy the contents of the `dist` directory to the router, preserving permissions and symlinks.
2. Make sure `ubus` and `jsonfilter` are present on the device.
3. Check the symlink `/usr/bin/router-led` → `/usr/bin/router-led-v1`.
4. If the client runs not as root, make sure the file `/usr/share/acl.d/router-state.json` is installed and restart `rpcd`.
5. Enable and start the service: `/etc/init.d/router-led enable` and `/etc/init.d/router-led start`.
6. Verify functionality with `ubus send router.state '{"state":"active"}'` and logs `logread | grep router`.

## LED List Setup
The list of LEDs is controlled by the variables `ROUTER_LED_ACTIVE_LIST` and `ROUTER_LED_INACTIVE_LIST`. They can be set in `/etc/profile`, `/etc/rc.local`, or in the configuration of the launching service before `/usr/bin/router-state-listener` starts.

## Getting State from Server
After receiving `subscriber_uid`, the client performs request to the main server. The response must contain the fields `state` (`registered`, `not_registered`, `unknown`) and `status` (`online`, `offline`, `unknown`). Depending on these values, the client sets LEDs to `active`, `inactive`, or `off` and publishes the `router.state` event. 
