"""Zugriff auf die Tankerkönig-API (MTS-K Spritpreise Deutschland).

Kostenlose, offizielle Datenquelle. Der List-Endpunkt liefert alle
Tankstellen im Umkreis inkl. aktuellem Preis für den gewählten Kraftstoff.
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

LIST_URL = "https://creativecommons.tankerkoenig.de/json/list.php"


@dataclass
class Station:
    id: str
    name: str
    brand: str
    price: float
    dist_km: float
    is_open: bool
    place: str
    street: str = ""
    house_number: str = ""
    post_code: str = ""

    @property
    def label(self) -> str:
        brand = self.brand or self.name or "Tankstelle"
        return f"{brand} ({self.place})" if self.place else brand


def fetch_stations(
    api_key: str,
    lat: float,
    lng: float,
    radius_km: float,
    fuel_type: str = "e10",
    timeout: int = 20,
) -> list[Station]:
    """Tankstellen im Umkreis, aufsteigend nach Preis sortiert.

    Nur geöffnete Tankstellen mit gültigem Preis (> 0) werden zurückgegeben.
    """
    params = {
        "lat": lat,
        "lng": lng,
        "rad": radius_km,
        "sort": "price",
        "type": fuel_type,
        "apikey": api_key,
    }
    resp = requests.get(LIST_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok", False):
        raise RuntimeError(f"Tankerkönig-API-Fehler: {data.get('message', 'unbekannt')}")

    stations: list[Station] = []
    for s in data.get("stations", []):
        price = s.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            continue  # geschlossen oder kein E10 -> Preis null/false
        stations.append(
            Station(
                id=str(s.get("id", "")),
                name=s.get("name", "") or "",
                brand=s.get("brand", "") or "",
                price=float(price),
                dist_km=float(s.get("dist", 0.0)),
                is_open=bool(s.get("isOpen", False)),
                place=s.get("place", "") or "",
                street=s.get("street", "") or "",
                house_number=str(s.get("houseNumber", "") or ""),
                post_code=str(s.get("postCode", "") or ""),
            )
        )
    stations.sort(key=lambda st: st.price)
    return stations


def _norm(value: str) -> str:
    return (value or "").casefold().strip()


def find_preferred(stations: list[Station], spec) -> Station | None:
    """Bevorzugte Tankstelle in der Trefferliste finden.

    Harte Filter: Marke (in brand ODER name), Straße, Ort.
    Hausnummer wird bevorzugt, aber nicht erzwungen (Formatierung variiert).
    Bei mehreren Treffern gewinnt der günstigste.
    """
    cands: list[Station] = []
    for st in stations:
        if spec.brand and _norm(spec.brand) not in _norm(st.brand) and _norm(spec.brand) not in _norm(st.name):
            continue
        if spec.street and _norm(spec.street) not in _norm(st.street):
            continue
        if spec.place and _norm(spec.place) not in _norm(st.place):
            continue
        cands.append(st)
    if not cands:
        return None
    if spec.house_number:
        exact = [s for s in cands if _norm(s.house_number) == _norm(spec.house_number)]
        if exact:
            cands = exact
    return min(cands, key=lambda s: s.price)
