% MATLAB code
function send_info_to(ip, port, printout, infos)
    payload = jsonencode(infos);

    if printout
        disp("Sending to " + ip + ":" + port)
        disp(payload)
    end

    u = udpport("datagram","IPV4");
    write(u, uint8(payload), "uint8", ip, port);
end


function [msg, addr] = receive_info(port, printout)
    u = udpport("datagram","IPV4","LocalPort",port);

    data = read(u, 1, "uint8");
    msg = jsondecode(char(data'));

    addr = [];
    if printout
        disp("Received message:")
        disp(msg)
    end
end

% % mit time out
function [msg, addr] = receive_info2(port, timeout, printout)
    arguments
        port (1,1) double
        timeout (1,1) double = 0
        printout (1,1) logical = false
    end

    u = udpport("datagram","IPV4","LocalPort",port);

    msg = [];
    addr = [];

    if timeout > 0
        u.Timeout = timeout;
    end

    try
        if timeout > 0
            tStart = tic;
            while u.NumDatagramsAvailable == 0
                if toc(tStart) >= timeout
                    if printout
                        disp("Receive timeout on port " + port)
                    end
                    return
                end
                pause(0.01);
            end
        else
            while u.NumDatagramsAvailable == 0
                pause(0.01);
            end
        end

        data = read(u, 1, "uint8");
        msg = jsondecode(char(data'));

        if printout
            disp("Received message:")
            disp(msg)
        end
   catch ME
        if printout
            disp("Receive error:")
            disp(ME.message)
        end
    end
end

infos = struct("mode", 3, "name", "robot1", "status", "ready");
send_info_to("127.0.0.1", 5005, true, infos);
receive_info(5005, true);