function udp_receiver()

    % Einstellungen
    localPort = 5005;
    printout = true;

    % UDP-Empfänger erzeugen
    u = udpport( ...
        "datagram", ...
        "IPV4", ...
        "LocalPort", localPort);

    % Socket beim Beenden automatisch freigeben
    cleanupObject = onCleanup(@() cleanupUdp(u)); %#ok<NASGU>

    fprintf("UDP-Empfänger läuft auf Port %d.\n", localPort);
    fprintf("Zum Beenden: Strg+C drücken.\n\n");

    % Endlosschleife
    while true

        % Prüfen, ob Datagramme angekommen sind
        if u.NumDatagramsAvailable > 0

            % Alle aktuell vorhandenen Datagramme lesen
            datagrams = read(u, u.NumDatagramsAvailable, "uint8");

            for k = 1:numel(datagrams)

                try
                    % Nutzdaten aus dem Datagramm holen
                    rawData = datagrams(k).Data;

                    % Byte-Daten in JSON-Text umwandeln
                    jsonText = char(rawData);

                    % JSON in MATLAB-Daten umwandeln
                    msg = jsondecode(jsonText);

                    % Nachricht ausgeben
                    if printout
                        fprintf("Nachricht empfangen:\n");
                        disp(msg);
                    end

                    % Absender ausgeben, falls verfügbar
                    if isprop(datagrams(k), "SenderAddress")
                        fprintf( ...
                            "Absender: %s:%d\n\n", ...
                            datagrams(k).SenderAddress, ...
                            datagrams(k).SenderPort);
                    end

                catch ME
                    fprintf("Fehler beim Verarbeiten der Nachricht:\n");
                    fprintf("%s\n\n", ME.message);
                end
            end
        end

        % Verhindert unnötige Prozessorlast
        pause(0.01);
    end
end


function cleanupUdp(u)

    if ~isempty(u) && isvalid(u)
        clear u
    end

    fprintf("\nUDP-Empfänger wurde beendet.\n");
end