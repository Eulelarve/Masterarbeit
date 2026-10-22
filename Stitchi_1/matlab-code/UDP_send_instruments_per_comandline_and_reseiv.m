% Stitchi 1.0
%
% Interactive MATLAB UDP test for adding instruments and receiving state.
% Sends an initial instrument list, then prompts for an optional instrument
% name on each loop. Any entered name is sent under the add_instruments key;
% incoming UDP JSON messages are read and printed. Uses local port 5005 and
% targets the video-system PC at 192.168.0.11:5005. Stop with Ctrl+C.

function udp_sender_receiver()

    % Ziel-PC einstellen
    targetIp = "192.168.0.11";
    targetPort = 5005;
    localPort = 5005;

    % UDP-Socket erstellen
    u = udpport("datagram", "IPV4", "LocalPort", localPort);
    cleanupObject = onCleanup(@() delete(u)); %#ok<NASGU>

    %% 1. Instrumentenliste senden
    infos = struct( ...
        "add_instruments", ...
        ["trumpet", "trumpet", "Tröte", "piano", ...
         "violin", "trommel", "xylo", "r2d2"] ...
    );

    payload = jsonencode(infos);
    data = unicode2native(payload, "UTF-8");

    write(u, uint8(data), "uint8", targetIp, targetPort);

    fprintf("Instrumentenliste gesendet an %s:%d:\n", ...
        targetIp, targetPort);
    disp(payload);

    %% 2. Empfang und Eingabe starten
    fprintf("\nUDP-Empfang läuft auf Port %d.\n", localPort);
    fprintf("Du kannst jetzt ein Instrument eingeben und senden.\n");
    fprintf("Zum Beenden: Strg+C.\n\n");

    % Eingabe in separatem Hintergrund-Thread wäre komplex.
    % Deshalb verwenden wir eine einfache interaktive Schleife.
    while true

        % Eingabe abfragen
        word = input("Instrument eingeben (Enter = keine Eingabe): ", "s");

        if ~isempty(strtrim(word))
            % Wort mit demselben JSON-Schlüssel senden
            msg = struct("add_instruments", string(strtrim(word)));
            payload = jsonencode(msg);
            data = unicode2native(payload, "UTF-8");

            write(u, uint8(data), "uint8", targetIp, targetPort);

            fprintf("Gesendet an %s:%d: %s\n\n", ...
                targetIp, targetPort, payload);
        end

        % Eingehende Nachrichten verarbeiten
        while u.NumDatagramsAvailable > 0
            datagrams = read(u, u.NumDatagramsAvailable, "uint8");

            for k = 1:numel(datagrams)
                try
                    rawData = datagrams(k).Data;
                    jsonText = native2unicode(rawData, "UTF-8");
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
    end
end
