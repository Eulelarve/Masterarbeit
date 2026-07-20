import json
import socket

class SendOnChange:
    """
    Sends information only if at least one value has changed.
    """

    def __init__(self, device:tuple[str:int], printout=False):
        self.device = device
        self.printout = printout
        self._last_infos = {}

    def send(self, **infos):
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
        if infos == self._last_infos:
            return None

        self._last_infos = infos.copy()

        return send_info_to(
            self.device,
            printout=self.printout,
            **infos
        )

    def reset(self):
        """Forgets the previously sent values."""
        self._last_infos.clear()



# (perplexety): Ich würde die Funktion so bauen, 
# dass sie die Werte als JSON-String über UDP sendet. 
# Das ist robust für Integer und Strings und in MATLAB leicht wieder einlesbar.


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
    payload = json.dumps(payload_dict).encode("utf-8")

    if printout:
        print(f"Sending to {ip}:{port} -> {payload_dict}")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return sock.sendto(payload, (ip, port))
    finally:
        sock.close()

def receive_info(port, timeout=0, buffer_size=4096, printout=False, bind_ip="0.0.0.0"):
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
    import threading
    import time

    def rx_worker():
        print("RX thread started")
        msg, addr = receive_info(5005, timeout=0, printout=True, bind_ip="127.0.0.1")
        print("RX result:", msg, addr)

    def tx_worker():
        time.sleep(0.5)
        print("TX thread started")
        r = send_info_to(("127.0.0.1", 5005), printout=True, name="violin", angle=90)
        print("TX bytes:", r)

    rx_thread = threading.Thread(target=rx_worker, daemon=True)
    tx_thread = threading.Thread(target=tx_worker, daemon=True)

    rx_thread.start()
    tx_thread.start()

    tx_thread.join()
    rx_thread.join(timeout=2)

# # MATLAB code
# function send_info_to(ip, port, printout, infos)
#     payload = jsonencode(infos);

#     if printout
#         disp("Sending to " + ip + ":" + port)
#         disp(payload)
#     end

#     u = udpport("datagram","IPV4");
#     write(u, uint8(payload), "uint8", ip, port);
# end


# function [msg, addr] = receive_info(port, printout)
#     u = udpport("datagram","IPV4","LocalPort",port);

#     data = read(u, 1, "uint8");
#     msg = jsondecode(char(data'));

#     addr = [];
#     if printout
#         disp("Received message:")
#         disp(msg)
#     end
# end

# # mit time out
# function [msg, addr] = receive_info(port, timeout, printout)
#     arguments
#         port (1,1) double
#         timeout (1,1) double = 0
#         printout (1,1) logical = false
#     end

#     u = udpport("datagram","IPV4","LocalPort",port);

#     msg = [];
#     addr = [];

#     if timeout > 0
#         u.Timeout = timeout;
#     end

#     try
#         if timeout > 0
#             tStart = tic;
#             while u.NumDatagramsAvailable == 0
#                 if toc(tStart) >= timeout
#                     if printout
#                         disp("Receive timeout on port " + port)
#                     end
#                     return
#                 end
#                 pause(0.01);
#             end
#         else
#             while u.NumDatagramsAvailable == 0
#                 pause(0.01);
#             end
#         end

#         data = read(u, 1, "uint8");
#         msg = jsondecode(char(data'));

#         if printout
#             disp("Received message:")
#             disp(msg)
#         end

#     catch ME
#         if printout
#             disp("Receive error:")
#             disp(ME.message)
#         end
#     end
# end

# infos = struct("mode", 3, "name", "robot1", "status", "ready");
# send_info_to("127.0.0.1", 5005, true, infos);