Anleitung: UDP-Kommunikation zwischen Gestensteuerung und MATLAB

1. Gestensteuerung starten

Auf dem PC Videosystem zuerst die Gestensteuerung Stitchi 1.0 starten. Führe dazu die main.py im Python-Projekt aus.

Warte, bis die Gestensteuerung vollständig gestartet ist.


2. MATLAB-Skript ausführen

Führe anschließend eines der folgenden MATLAB-Skripte aus:

UDP_send_instruments_then_receiv_orders.m – sendet die festgelegte Instrumentenliste automatisch und empfängt anschließend die Instrumentenparameter.
UDP_send_instruments_per_comandline_and_reseiv.m – sendet ebenfalls die Instrumentenliste und ermöglicht zusätzlich, weitere Instrumente über die MATLAB-Konsole einzugeben.


3. Erwartetes Verhalten
Die gesendeten Instrumente erscheinen im Instrumentenmenü der grafischen Benutzeroberfläche (GUI) der Gestensteuerung.
Werden die Instrumente mit einer Greifgeste bewegt, werden die zugehörigen Instrumentenparameter in der MATLAB-Konsole angezeigt.
Beim Skript UDP_send_instruments_per_comandline_and_reseiv.m werden die Instrumentendaten erst nach Betätigen der Enter-Taste verarbeitet.
Vor dem Drücken von Enter kann ein zusätzlicher Instrumentenname eingegeben werden. Dieser wird ebenfalls an die Gestensteuerung gesendet und erscheint dort im Instrumentenmenü.


4. Beenden

Die MATLAB-Empfangsschleife kann mit Strg+C beendet werden.