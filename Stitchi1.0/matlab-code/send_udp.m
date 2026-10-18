function udp_sender()

    % Ziel einstellen
    targetIp = "127.0.0.1";
    targetPort = 5005;

    % Zu sendende Daten
    infos = struct( ...
        "mode", 3, ...
        "name", "robot1", ...
        "status", "ready" ...
    );

    % Struktur in JSON umwandeln
    payload = jsonencode(infos);

    % UDP-Socket ohne festen lokalen Port erstellen
    u = udpport("datagram", "IPV4");

    % Socket nach dem Senden freigeben
    cleanupObject = onCleanup(@() cleanupUdp(u)); %#ok<NASGU>

    % Nachricht senden
    write(u, uint8(payload), "uint8", targetIp, targetPort);

    fprintf("Nachricht gesendet an %s:%d:\n", targetIp, targetPort);
    disp(payload);
end


function cleanupUdp(u)

    if ~isempty(u) && isvalid(u)
        clear u
    end
end