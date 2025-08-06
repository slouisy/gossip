import socket
import threading
import time
import random
import sys
import logging
import subprocess
import re
import matplotlib.pyplot as plt
import numpy as np

# Setup logging
my_id = int(sys.argv[2])
my_ip = f"10.0.0.{my_id+1}"
log_filename = f"logs/gossip_log_sta{my_id}.log"
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

all_ips = []
removed_ips = []
port = 12345
discovery_port = 12346
view = {my_ip: 0}
lock = threading.Lock()

def completed():
    for ip in all_ips:
        if ip not in view:
            return False
    return True

def increase_hops(v):
    return {k: v[k] + 1 for k in v}

def merge(v1, v2):
    merged = v1.copy()
    for k in v2:
        if k not in merged or v2[k] < merged[k]:
            merged[k] = v2[k]
    final = dict(sorted(merged.items(), key=lambda item: item[1]))
    return final

def remove_peer(ip):
    with lock:
        view.pop(ip, None)
        if ip in all_ips:
            all_ips.remove(ip)
        removed_ips.append(ip)
        logging.warning(f"{ip} has been removed from view")

def mayday(ip):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        s.sendto(f"MAYDAY {ip}".encode(), ('10.0.0.255', discovery_port))
    except Exception as e:
        logging.warning(f"Mayday broadcast failed: {e}")
    time.sleep(5)

# === NEW: Select closest peer based on ping RTT ===
def get_closest_peers():
    peer_rtts = []
    logging.info("Getting Closest Peer")
    for ip in all_ips:
        try:
            result = subprocess.run(
                ['ping', '-c', '1', '-W', '1', ip],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True
            )

            # Check if ping was successful
            if result.returncode == 0:
                match = re.search(r'time=(\d+\.?\d*) ms', result.stdout)
                if match:
                    rtt = float(match.group(1))
                    peer_rtts.append((ip, rtt))
            else:
                logging.warning(f"Unreachable peer: {ip}")
                remove_peer(ip)
                #Alert Other Peers
                mayday(ip)
                logging.warning("Alerting other peers")


        except Exception as e:
            logging.warning(f"Ping failed for {ip}: {e}")
            

    if peer_rtts:
        peer_rtts.sort(key=lambda x: x[1])
        best = peer_rtts[0]
        logging.info(f"Peers: {peer_rtts}")
        logging.info(f"[CHOICE] Closest peer is {best[0]} with RTT {best[1]} ms")
        return peer_rtts
    else:
        logging.warning("No peers available")
        return None

def serve():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind((my_ip, port))  # Listen on all interfaces for the given port

    while True:
        data, addr = s.recvfrom(2048)
        received = eval(data.decode())
        sender_ip = addr[0]
        with lock:
            global view
            if received == {}:
                logging.info(f"[RECV pull from {sender_ip}]")
                reply = str(view).encode()
                s.sendto(reply, addr)
                logging.info(f"[SEND push reply to {sender_ip}] {view}")
            else:
                logging.info(f"[RECV push from {sender_ip}] {received}")
                received = increase_hops(received)
                view = merge(view, received)
                logging.info(f"[MERGE] updated view: {view}")

def gossip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        logging.info("GOSSIPING...")
        peer_ips = get_closest_peers()
        if not peer_ips :
            logging.warning("No reachable peers found. Skipping gossip round.")
            time.sleep(2)
            continue

        mode = random.choice(["push", "pull"])

        for peer in peer_ips:
            peer_ip = peer[0]
            with lock:
                if mode == "push":
                    payload = str(view).encode()
                    logging.info(f"[SEND push to {peer_ip}] {view}")
                else:
                    payload = str({}).encode()
                    logging.info(f"[SEND pull to {peer_ip}]")
            try:
                s.sendto(payload, (peer_ip, port))
            except Exception as e:
                logging.warning(f"[SEND FAILED to {peer_ip}] {e}")
        time.sleep(random.uniform(1, 3))

def discovery_broadcaster():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while True:
        try:
            s.sendto("DISCOVERY".encode(), ('10.0.0.255', discovery_port))
        except Exception as e:
            logging.warning(f"Discovery broadcast failed: {e}")
        time.sleep(5)

def discovery_listener():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind(('', discovery_port))

    while True:
        try:
            data, addr = s.recvfrom(1024)
            msg = data.decode()
            if msg == "DISCOVERY":
                if not (addr[0] in all_ips) and (addr[0] != my_ip):
                    all_ips.append(addr[0])
                    logging.warning(f"Updated IPs: {all_ips}")
            if msg.__contains__("MAYDAY"):
                    mayday_ip = msg.split(" ")[1]
                    logging.warning(f"Node Down: {mayday_ip}")
                    remove_peer(mayday_ip)
        except socket.timeout:
            continue

# === Start Threads ===
threading.Thread(target=serve, daemon=True).start()
threading.Thread(target=gossip, daemon=True).start()

threading.Thread(target=discovery_listener, daemon=True).start()
threading.Thread(target=discovery_broadcaster, daemon=True).start()



# === Print View Every 5 Seconds ===
while True:
    with lock:
        logging.info(f"[STATE] Current view: {view}")
    time.sleep(5)


