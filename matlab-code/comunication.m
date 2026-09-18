function self_test_udp()

    % Einstellungen
    ip = "127.0.0.1";
    port = 5005;
    timeout = 5;       % Sekunden
    printout = true;

    % Daten zum Senden
    infos = struct( ...
        "mode", 3, ...
        "name", "robot1", ...
        "status", "ready" ...
    );

    % Einen gemeinsamen UDP-Socket zum Senden und Empfangen erstellen
    u = udpport("datagram", "IPV4", "LocalPort", port);

    % Socket beim Verlassen der Funktion automatisch schließen
    cleanupObject = onCleanup(@() clearUdpPort(u)); %#ok<NASGU>

    % Daten senden und anschließend empfangen
    send_info(u, ip, port, printout, infos);

    [msg, addr] = receive_info(u, timeout, printout);

    % Ergebnis ausgeben
    if isempty(msg)
        disp("Keine Nachricht empfangen.");
    else
        disp("Erfolgreich empfangen:");
        disp(msg);

        if ~isempty(addr)
            disp("Absender:");
            disp(addr);
        end
    end
end


function send_info(u, ip, port, printout, infos)

    % Struktur in JSON umwandeln
    payload = jsonencode(infos);

    if printout
        fprintf("Sende an %s:%d\n", ip, port);
        disp(payload);
    end

    % JSON als Byte-Datagramm senden
    write(u, uint8(payload), "uint8", ip, port);
end


function [msg, addr] = receive_info(u, timeout, printout)

    arguments
        u
        timeout (1,1) double = 0
        printout (1,1) logical = false
    end

    msg = [];
    addr = [];

    % Auf ein Datagramm warten
    tStart = tic;

    while u.NumDatagramsAvailable == 0

        if timeout > 0 && toc(tStart) >= timeout
            if printout
                fprintf("Empfangs-Timeout nach %.2f Sekunden.\n", timeout);
            end
            return;
        end

        pause(0.01);
    end

    try
        % Genau ein Datagramm lesen
        datagram = read(u, 1, "uint8");

        % Bei udpport("datagram") steht der Inhalt in .Data
        rawData = datagram(1).Data;

        % Bytes in Text und anschließend in MATLAB-Struktur umwandeln
        jsonText = char(rawData);
        msg = jsondecode(jsonText);

        % Absenderinformationen übernehmen
        if isprop(datagram, "SenderAddress")
            addr = struct( ...
                "IP", datagram(1).SenderAddress, ...
                "Port", datagram(1).SenderPort ...
            );
        end

        if printout
            disp("Nachricht empfangen:");
            disp(msg);
        end

    catch ME
        if printout
            disp("Empfangsfehler:");
            disp(ME.message);
        end
    end
end


function clearUdpPort(u)
    % UDP-Socket sauber freigeben
    if ~isempty(u) && isvalid(u)
        clear u
    end
end