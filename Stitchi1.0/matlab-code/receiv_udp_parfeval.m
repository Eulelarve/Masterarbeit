
%{

Im MATLAB-Kommandofenster genügt dann:

	future = receiv_udp_parfeval();

Damit wird udp_receiver unmittelbar über parfeval im backgroundPool gestartet. 
Die Funktion receiv_udp_parfeval gibt danach das Future-Objekt zurück, 
über das der Hintergrundvorgang gesteuert werden kann.

Zum Beenden:

	cancel(future);

%}

function future = receiv_udp_parfeval()

    % UDP-Empfänger automatisch im Hintergrund starten
    future = parfeval( ...
        backgroundPool, ...
        @udp_receiver, ...
        0);

    fprintf("UDP-Empfänger wurde im Hintergrund gestartet.\n");
    fprintf("Zum Beenden: cancel(future)\n");
end


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

    % Endlosschleife
    while true

        if u.NumDatagramsAvailable > 0

            % Alle aktuell verfügbaren Datagramme lesen
            datagrams = read(u, u.NumDatagramsAvailable, "uint8");

            for k = 1:numel(datagrams)

                try
                    % Byte-Daten in JSON-Text umwandeln
                    jsonText = char(datagrams(k).Data);

                    % JSON dekodieren
                    msg = jsondecode(jsonText);

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
                    fprintf( ...
                        "Fehler beim Verarbeiten der Nachricht:\n%s\n\n", ...
                        ME.message);
                end
            end
        end

        % Prozessorlast reduzieren
        pause(0.01);
    end
end


function cleanupUdp(u)

    if ~isempty(u) && isvalid(u)
        clear u
    end

    fprintf("\nUDP-Empfänger wurde beendet.\n");
end