import json
import socket
import numpy as np
import threading
from own_functions import add_to_dict, add_dict_to_dict
import settings as S

class SendOnChange:
    """
    Sends information only if at least one value has changed.
    """

    def __init__(self, device:tuple[str:int]):
        self.device = device
        self._last_infos = {}
        self.enable_printout = S.printout_udp

    def send(self, printout, **infos):
        """
        Sends the given information only if it differs from the
        previously sent values.

        Parameters
        ----------
        **infos : dict
            Key-value pairs to send.

        Returns
        -------
        int | None
            Number of sent bytes if data was sent, otherwise None.
        """
        printout = printout and self.enable_printout  
        if infos == self._last_infos:
            return None

        self._last_infos = infos.copy()

        return send_info_to(
            self.device,
            printout=printout,
            **infos
        )

    def reset(self):
        """Forgets the previously sent values."""
        self._last_infos.clear()



# (perplexety): Ich würde die Funktion so bauen, 
# dass sie die Werte als JSON-String über UDP sendet. 
# Das ist robust für Integer und Strings und in MATLAB leicht wieder einlesbar.

def json_converter(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def send_info_to(device, printout=False, **infos):
    """
    Send values via UDP as JSON.

    Parameters
    ----------
    device : tuple
        Target address as (ip, port).
    printout : bool, default=False
        If True, print the payload before sending.
    **infos : dict
        key-value pairs.

    Returns
    -------
    int
        Number of sent bytes.
    """
    ip, port = device
    payload_dict = dict(infos)
    payload = json.dumps(payload_dict, default=json_converter).encode("utf-8")

    if printout:
        print(f"Sending to {ip}:{port} -> {payload_dict}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return sock.sendto(payload, (ip, port))
    finally:
        sock.close()


class SaveUdpToDict:
    def __init__(self):
        self.rx_thread = threading.Thread(target=self.receive_loop, daemon=True)
        self.on = False
        self.printout = S.printout_udp
        self.msg_list:list[dict] = []
        self.loop_time:float = 0
        self.bind_ip = S.bind_ip

    def receive_loop(self):
        while self.on:
            msg, addr = receive_info(S.port, timeout=self.loop_time, printout=self.printout, bind_ip=self.bind_ip)
            self.add_meassage(msg)

    def add_meassage(self,msg:dict):
        if msg:
            self.msg_list.append(msg)

    def start_receiving(self):
        self.on = True
        self.rx_thread.start()

    def stop_receiving(self):
        self.on = False
        self.rx_thread.join(timeout=2)


    def get_msg(self, keep_in_list=False)->dict:
        if self.msg_list:
            if keep_in_list:
                msg = self.msg_list[0].copy()
            else:
                msg = self.msg_list.pop(0)
            return msg
        return {}

    def clear_msg_list(self):
        self.msg_list.clear()


def receive_info(port, timeout=0.0, buffer_size=4096, printout=False, bind_ip="0.0.0.0"):
    """
    Receive one UDP JSON packet.

    timeout = 0  -> wait forever
    timeout > 0  -> wait up to timeout seconds
    bind_ip      -> "0.0.0.0" for all interfaces, "127.0.0.1" for localhost test
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((bind_ip, port))

    if timeout and timeout > 0:
        sock.settimeout(timeout)
    else:
        sock.settimeout(None)

    try:
        data, addr = sock.recvfrom(buffer_size)
        msg = json.loads(data.decode("utf-8"))

        if printout:
            print(f"Received from {addr}: {msg}")

        return msg, addr

    except socket.timeout:
        if printout:
            print(f"Receive timeout on {bind_ip}:{port} after {timeout} s")
        return None, None

    finally:
        sock.close()



if __name__ == "__main__":
    # for testing
    import time

    def rx_worker():
        print("RX thread started")
        msg, addr = receive_info(S.port, timeout=0, printout=True, bind_ip=S.bind_ip)
        print("RX result:", msg, addr)

    def tx_worker():
        time.sleep(0.5)
        print("TX thread started")
        r = send_info_to((S.IPv4_videosystem, S.port), printout=True, name="violin", angle=90)
        print("TX bytes:", r)

    rx_thread = threading.Thread(target=rx_worker, daemon=True)
    tx_thread = threading.Thread(target=tx_worker, daemon=True)

    rx_thread.start()
    tx_thread.start()

    tx_thread.join()
    rx_thread.join(timeout=2)