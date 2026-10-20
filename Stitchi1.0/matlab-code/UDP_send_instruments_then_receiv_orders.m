
function udp_sender_receiver()

    % Einstellungen
    targetIp = "192.168.0.11";  % PC-Videosystem
    targetPort = 5005;
    localPort = 5005;

    % Zu sendende Daten
    infos = struct( ...
        "add_instruments", ...
        ["trumpet", "trumpet", "Tröte", "piano", ...
         "violin", "trommel", "xylo", "r2d2"] ...
    );

    % Struktur in JSON umwandeln
    payload = jsonencode(infos);

    % UDP-Socket erstellen und lokalen Empfangsport öffnen
    u = udpport("datagram", "IPV4", "LocalPort", localPort);
    cleanupObject = onCleanup(@() delete(u)); %#ok<NASGU>

    %% 1. Nachricht senden
    data = unicode2native(payload, "UTF-8");

    write(u, uint8(data), "uint8", targetIp, targetPort);

    fprintf("UDP-Nachricht gesendet an %s:%d:\n", ...
        targetIp, targetPort);
    disp(payload);

    %% 2. In den Empfangszustand wechseln
    fprintf("\nWarte auf UDP-Nachrichten auf Port %d ...\n", localPort);
    fprintf("Zum Beenden: Strg+C drücken.\n\n");

    while true

        if u.NumDatagramsAvailable > 0

            % Alle aktuell verfügbaren Datagramme lesen
            datagrams = read(u, u.NumDatagramsAvailable, "uint8");

            for k = 1:numel(datagrams)

                try
                    % Empfangene Bytes dekodieren
                    rawData = datagrams(k).Data;
                    jsonText = native2unicode(rawData, "UTF-8");

                    % JSON in MATLAB-Daten umwandeln
                    msg = jsondecode(jsonText);

                    fprintf("UDP-Nachricht empfangen:\n");
                    disp(msg);

                    fprintf("Absender: %s:%d\n\n", ...
                        datagrams(k).SenderAddress, ...
                        datagrams(k).SenderPort);

                catch ME
                    fprintf("Fehler beim Verarbeiten: %s\n", ME.message);
                end

            end
        end

        pause(0.01);
    end
end
