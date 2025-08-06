from mininet.log import setLogLevel, info
from mn_wifi.link import wmediumd, adhoc
from mn_wifi.cli import CLI
from mn_wifi.net import Mininet_wifi
from mn_wifi.wmediumdConnector import interference
import sys
import os
import math

station_count = 1
topology_type = "linear"
distance_scale = 1
mobility = ""

def topology():
    global station_count, topology_type, distance_scale, mobility

    net = Mininet_wifi(link=wmediumd, wmediumd_mode=interference)

    info(f"*** Creating {station_count} station(s)\n")
    positions = []
    for i in range(station_count):
        pos = f"{round((20 * distance_scale * (i + 1)) - 10)},10,0"
        positions.append(pos)

    stations = []

    if topology_type == "circle":
        info("*** Using circular topology\n")
        radius = round(20 * distance_scale)  
        center_x, center_y = round(100 * distance_scale), round(100 * distance_scale)  # Center of the circle

        for i in range(station_count):
            angle = 2 * math.pi * i / station_count  # Evenly spaced around circle
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            pos = f"{x:.2f},{y:.2f},0"  # z = 0

            sta = net.addStation(f'sta{i}', ip=f'10.0.0.{i + 1}/24', position=pos)
            stations.append(sta)
    else:
        for i in range(station_count):
            sta = net.addStation(f'sta{i}', ip=f'10.0.0.{i + 1}/24', position=positions[i])
            stations.append(sta)

    net.setPropagationModel(model="logDistance", exp=4)
    net.configureNodes()

    # Mobility setup
    if mobility == "random":
        info("*** Applying RandomDirection mobility\n")
        net.startMobility(time=0)
        for sta in stations:
            sta.mobility_model = 'RandomDirection'
            sta.min_v = 1
            sta.max_v = 2
            sta.min_x = 0
            sta.max_x = 200
            sta.min_y = 0
            sta.max_y = 60
        net.stopMobility(time=30)

    elif mobility == "waypoint":
        info("*** Applying RandomWaypoint mobility\n")
        net.startMobility(time=0)
        for sta in stations:
            sta.mobility_model = 'RandomWaypoint'
            sta.min_v = 1
            sta.max_v = 2
            sta.min_x = 0
            sta.max_x = 200
            sta.min_y = 0
            sta.max_y = 60
        net.stopMobility(time=30)

    elif mobility == "gauss":
        info("*** Applying GaussMarkov mobility\n")
        net.startMobility(time=0)
        for sta in stations:
            sta.mobility_model = 'GaussMarkov'
            sta.min_v = 1
            sta.max_v = 2
        net.stopMobility(time=30)

    else:
        info("*** Using Static (no mobility)\n")

    net.plotGraph(max_x=(200 * distance_scale), max_y=(200 * distance_scale))

    info("*** Creating adhoc links\n")
    for i, sta in enumerate(stations):
        net.addLink(sta, cls=adhoc, intf=f'sta{i}-wlan0',
                    ssid='adhocNet', mode='g', channel=5)

    info("*** Starting network\n")
    net.build()

    gossip_path = os.path.abspath("gossip.py")
    info("*** Starting gossip.py on each station\n")
    for i, sta in enumerate(stations):
        log_path = f'/tmp/gossip_{mobility}_{i}.log'
        sta.cmd(f'python3 {gossip_path} {station_count} {i} > {log_path} 2>&1 &')

    info(f"*** Running CLI for mobility = {mobility}\n")
    CLI(net)

    info("*** Stopping network\n")
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    
    if len(sys.argv) > 1:
            station_count = int(sys.argv[1])
    if len(sys.argv) > 2:
            topology_type = sys.argv[2]
    if len(sys.argv) > 3:
            distance_scale = float(sys.argv[3])
    if len(sys.argv) > 4:
            mobility = sys.argv[4]

    info(f"Creating {station_count} station(s) with mobility='{mobility}'\n")
    topology()

