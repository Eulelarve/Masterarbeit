% Send one JSON instrument-list message to the gesture-control PC.
% Creates a temporary IPv4 UDP endpoint, JSON-encodes the add_instruments
% field, converts the payload to UTF-8 bytes, and sends it to targetIp:targetPort.
% This script is a send-only connectivity test; it does not receive replies.

function udp_sender()

    % Ziel einstellen: PC-Videosystem
    targetIp = "192.168.0.11";
    targetPort = 5005;

    % Zu sendende Daten
    infos = struct( ...
        "add_instruments", ...
        ["trumpet", "trumpet", "Tröte", "piano", ...
         "violin", "trommel", "xylo", "r2d2"] ...
    );

    % Struktur in JSON umwandeln
    payload = jsonencode(infos);

    % UDP-Socket erstellen
    u = udpport("datagram", "IPV4");
    cleanupObject = onCleanup(@() delete(u)); %#ok<NASGU>

    % JSON als UTF-8-Bytes senden
    data = unicode2native(payload, "UTF-8");
    write(u, uint8(data), "uint8", targetIp, targetPort);

    fprintf("Nachricht gesendet an %s:%d:\n", ...
        targetIp, targetPort);
    disp(payload);

end
