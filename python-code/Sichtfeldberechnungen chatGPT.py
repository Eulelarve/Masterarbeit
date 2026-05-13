import math


def sichtfeld_in_meter(
    entfernung_m: float,
    horizontaler_winkel_deg: float,
    vertikaler_winkel_deg: float
) -> tuple[float, float]:
    """
    Berechnet die sichtbare Breite und Höhe einer Kamera
    in Metern anhand des Öffnungswinkels und der Entfernung.
    """

    breite_m = 2 * entfernung_m * math.tan(
        math.radians(horizontaler_winkel_deg / 2)
    )

    hoehe_m = 2 * entfernung_m * math.tan(
        math.radians(vertikaler_winkel_deg / 2)
    )

    return breite_m, hoehe_m


def sichtfeld_in_winkel(
    entfernung_m: float,
    breite_m: float,
    hoehe_m: float
) -> tuple[float, float]:
    """
    Berechnet den horizontalen und vertikalen Öffnungswinkel
    einer Kamera aus sichtbarer Breite/Höhe und Entfernung.

    Parameter:
        entfernung_m (float):
            Abstand der Kamera zur Szene in Metern.

        breite_m (float):
            Sichtbare Breite in Metern.

        hoehe_m (float):
            Sichtbare Höhe in Metern.

    Rückgabe:
        (horizontaler_winkel_deg, vertikaler_winkel_deg)
    """

    horizontaler_winkel_deg = math.degrees(
        2 * math.atan(breite_m / (2 * entfernung_m))
    )

    vertikaler_winkel_deg = math.degrees(
        2 * math.atan(hoehe_m / (2 * entfernung_m))
    )

    return horizontaler_winkel_deg, vertikaler_winkel_deg


# Beispiel
if __name__ == "__main__":

    entfernung = 10  # Meter

    # Winkel -> Meter
    breite, hoehe = sichtfeld_in_meter(
        entfernung,
        horizontaler_winkel_deg=90,
        vertikaler_winkel_deg=60
    )

    print("Winkel -> Meter")
    print(f"Breite: {breite:.2f} m")
    print(f"Höhe:   {hoehe:.2f} m")

    # Meter -> Winkel
    h_winkel, v_winkel = sichtfeld_in_winkel(
        entfernung,
        breite_m=20,
        hoehe_m=11.55
    )

    print("\nMeter -> Winkel")
    print(f"Horizontaler Winkel: {h_winkel:.2f}°")
    print(f"Vertikaler Winkel:   {v_winkel:.2f}°")

print("\n-------------\n")


def diagonaler_fov_zu_horizontal_und_vertikal(
    diagonaler_winkel_deg: float,
    seitenverhaeltnis_breite: float,
    seitenverhaeltnis_hoehe: float
) -> tuple[float, float]:
    """
    Wandelt einen diagonalen Öffnungswinkel (Diagonal FoV)
    in horizontalen und vertikalen Öffnungswinkel um.

    Parameter:
        diagonaler_winkel_deg (float):
            Diagonaler Öffnungswinkel in Grad.

        seitenverhaeltnis_breite (float):
            Breitenanteil des Seitenverhältnisses
            (z.B. 16 bei 16:9).

        seitenverhaeltnis_hoehe (float):
            Höhenanteil des Seitenverhältnisses
            (z.B. 9 bei 16:9).

    Rückgabe:
        (horizontaler_winkel_deg, vertikaler_winkel_deg)
    """

    # Seitenverhältnis normieren
    w = seitenverhaeltnis_breite
    h = seitenverhaeltnis_hoehe

    # Diagonale des Seitenverhältnisses
    diagonal = math.sqrt(w**2 + h**2)

    # Tangens des halben diagonalen Winkels
    tan_diag_halb = math.tan(
        math.radians(diagonaler_winkel_deg / 2)
    )

    # Horizontaler Winkel
    horizontaler_winkel_deg = math.degrees(
        2 * math.atan(tan_diag_halb * (w / diagonal))
    )

    # Vertikaler Winkel
    vertikaler_winkel_deg = math.degrees(
        2 * math.atan(tan_diag_halb * (h / diagonal))
    )

    return horizontaler_winkel_deg, vertikaler_winkel_deg


# Beispiel
if __name__ == "__main__":

    diagonal_fov = 110  # Grad
    aspect_w = 16
    aspect_h = 9

    h_fov, v_fov = diagonaler_fov_zu_horizontal_und_vertikal(
        diagonal_fov,
        aspect_w,
        aspect_h
    )

    print(f"Diagonaler FoV: {diagonal_fov}°")
    print(f"Seitenverhältnis: {aspect_w}:{aspect_h}")
    print(f"Horizontaler FoV: {h_fov:.2f}°")
    print(f"Vertikaler FoV:   {v_fov:.2f}°")


print("\n-------------\n")


def quadratischer_fov_zu_seitenverhaeltnis(
    basis_horizontal_deg: float,
    basis_vertikal_deg: float,
    ziel_breite: float,
    ziel_hoehe: float
) -> tuple[float, float]:
    """
    Erweitert ein vorhandenes Sichtfeld auf ein neues Seitenverhältnis,
    sodass das ursprüngliche Sichtfeld vollständig enthalten bleibt.

    Beispiel:
        Ausgang: 60° x 60°
        Ziel-Seitenverhältnis: 16:9

    Ergebnis:
        Vertikal bleibt mindestens 60°
        Horizontal wird passend erweitert.

    Parameter:
        basis_horizontal_deg (float):
            Ursprünglicher horizontaler Öffnungswinkel.

        basis_vertikal_deg (float):
            Ursprünglicher vertikaler Öffnungswinkel.

        ziel_breite (float):
            Ziel-Seitenverhältnis Breite
            (z.B. 16).

        ziel_hoehe (float):
            Ziel-Seitenverhältnis Höhe
            (z.B. 9).

    Rückgabe:
        (neuer_horizontaler_fov_deg, neuer_vertikaler_fov_deg)
    """

    ziel_aspekt = ziel_breite / ziel_hoehe

    # Tangens der halben Basiswinkel
    tan_h = math.tan(math.radians(basis_horizontal_deg / 2))
    tan_v = math.tan(math.radians(basis_vertikal_deg / 2))

    # Aktuelles Seitenverhältnis im Winkelraum
    aktuelles_aspekt = tan_h / tan_v

    if aktuelles_aspekt < ziel_aspekt:
        # Ziel ist breiter -> horizontal erweitern
        neuer_tan_h = tan_v * ziel_aspekt
        neuer_tan_v = tan_v
    else:
        # Ziel ist höher/schmaler -> vertikal erweitern
        neuer_tan_h = tan_h
        neuer_tan_v = tan_h / ziel_aspekt

    neuer_horizontal_deg = math.degrees(
        2 * math.atan(neuer_tan_h)
    )

    neuer_vertikal_deg = math.degrees(
        2 * math.atan(neuer_tan_v)
    )

    return neuer_horizontal_deg, neuer_vertikal_deg


# Beispiel
if __name__ == "__main__":

    h_fov, v_fov = quadratischer_fov_zu_seitenverhaeltnis(
        basis_horizontal_deg=60,
        basis_vertikal_deg=60,
        ziel_breite=16,
        ziel_hoehe=9
    )

    print(f"Neuer horizontaler FoV: {h_fov:.2f}°")
    print(f"Neuer vertikaler FoV:   {v_fov:.2f}°")

print("\n-------------\n")



def horizontal_und_vertikal_zu_diagonal(
    horizontaler_winkel_deg: float,
    vertikaler_winkel_deg: float,
    seitenverhaeltnis_breite: float,
    seitenverhaeltnis_hoehe: float
) -> float:
    """
    Berechnet den diagonalen Öffnungswinkel (Diagonal FoV)
    aus horizontalem und vertikalem Öffnungswinkel sowie
    dem Seitenverhältnis.

    Parameter:
        horizontaler_winkel_deg (float):
            Horizontaler Öffnungswinkel in Grad.

        vertikaler_winkel_deg (float):
            Vertikaler Öffnungswinkel in Grad.

        seitenverhaeltnis_breite (float):
            Breitenanteil des Seitenverhältnisses
            (z.B. 16 bei 16:9).

        seitenverhaeltnis_hoehe (float):
            Höhenanteil des Seitenverhältnisses
            (z.B. 9 bei 16:9).

    Rückgabe:
        diagonaler_winkel_deg (float)
    """

    # Seitenverhältnis
    w = seitenverhaeltnis_breite
    h = seitenverhaeltnis_hoehe

    diagonal = math.sqrt(w**2 + h**2)

    # Tangens der halben Winkel
    tan_h = math.tan(math.radians(horizontaler_winkel_deg / 2))
    tan_v = math.tan(math.radians(vertikaler_winkel_deg / 2))

    # Diagonaler Tangens aus Geometrie
    tan_d = math.sqrt(tan_h**2 + tan_v**2)

    diagonaler_winkel_deg = math.degrees(
        2 * math.atan(tan_d)
    )

    return diagonaler_winkel_deg


# Beispiel
if __name__ == "__main__":

    h_fov, v_fov = quadratischer_fov_zu_seitenverhaeltnis(
        basis_horizontal_deg=70,
        basis_vertikal_deg=45,
        ziel_breite=16,
        ziel_hoehe=9
    )

    print(f"Neuer horizontaler FoV: {h_fov:.2f}°")
    print(f"Neuer vertikaler FoV:   {v_fov:.2f}°")

    # h_fov = 107
    # v_fov = 60

    diagonal_fov = horizontal_und_vertikal_zu_diagonal(
        h_fov,
        v_fov,
        16,
        9
    )

    print(f"Horizontaler FoV: {h_fov}°")
    print(f"Vertikaler FoV:   {v_fov}°")
    print(f"Diagonaler FoV:   {diagonal_fov:.2f}°")