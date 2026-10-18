"""Collecte des prix des carburants (flux open data du Ministère de l'Économie).

Produit trois fichiers dans data/ :
  - latest.csv               : une ligne par station, écrasé à chaque exécution
  - history_departements.csv : prix moyen/min/max par jour, département et carburant
  - history_national.csv     : idem, au niveau France
L'historique grossit d'un jour à chaque exécution (relancer le même jour remplace ce jour).
"""
import io
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests

URL = "https://donnees.roulez-eco.fr/opendata/instantane_ruptures"
CARBURANTS = ["Gazole", "SP95", "SP98", "E10", "E85", "GPLc"]
COLONNES = ["id", "code_postal", "ville", "departement", "latitude", "longitude",
            "date_collecte"] + CARBURANTS
# Plage plausible par carburant (en €/L) : hors de cette plage, c'est une erreur de saisie
# de la station (ex. un prix d'essence déclaré sur l'E85), le prix est ignoré.
PRIX_BORNES = {
    "Gazole": (1.5, 4.0), "SP95": (1.5 , 4.0), "SP98": (1.5, 4.0), "E10": (1.5, 4.0),
    "E85": (0.4, 1.6), "GPLc": (0.4, 1.8),
}
NB_STATIONS_MIN = 1000          # en dessous, on suppose un fichier source cassé
DATA_DIR = Path("data")


def telecharger_xml() -> bytes:
    """Télécharge le ZIP et renvoie le contenu du XML, sans rien écrire sur le disque."""
    rep = requests.get(URL, timeout=120)
    rep.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(rep.content)) as archive:
        return archive.read(archive.namelist()[0])


def departement(cp: str) -> str:
    if cp.startswith(("97", "98")):          # DOM-TOM : département sur 3 chiffres
        return cp[:3]
    if cp.startswith("20"):                  # Corse
        return "2A" if cp[:3] in ("200", "201") else "2B"
    return cp[:2]


def parser(xml_bytes: bytes, date_collecte: str) -> list[dict]:
    """Transforme le XML en liste de dictionnaires, un par station."""
    root = ET.fromstring(xml_bytes)  # des bytes : le parseur lit l'encodage déclaré (ISO-8859-1)
    stations = []
    for pdv in root.findall("pdv"):
        cp = (pdv.get("cp") or "").zfill(5)
        ville = pdv.find("ville")
        station = {
            "id": pdv.get("id"),
            "code_postal": cp,
            "ville": (ville.text or "").strip().upper() if ville is not None else "",
            "departement": departement(cp),
            "date_collecte": date_collecte,
        }
        try:
            lat, lon = float(pdv.get("latitude")) / 100000, float(pdv.get("longitude")) / 100000
            if lat != 0 or lon != 0:
                station["latitude"], station["longitude"] = round(lat, 5), round(lon, 5)
        except (TypeError, ValueError):
            pass
        for prix in pdv.findall("prix"):
            nom = prix.get("nom")
            try:
                valeur = float(prix.get("valeur"))
            except (TypeError, ValueError):
                continue
            if nom in PRIX_BORNES and PRIX_BORNES[nom][0] <= valeur <= PRIX_BORNES[nom][1]:
                station[nom] = valeur
        stations.append(station)
    return stations


def construire_historiques(df: pd.DataFrame, date_collecte: str):
    """Agrège le snapshot du jour : une ligne par (département, carburant) et par carburant."""
    long = df.melt(id_vars=["departement"], value_vars=CARBURANTS,
                   var_name="carburant", value_name="prix").dropna(subset=["prix"])
    agg = dict(prix_moyen=("prix", "mean"), prix_min=("prix", "min"),
               prix_max=("prix", "max"), nb_stations=("prix", "count"))
    dep = long.groupby(["departement", "carburant"]).agg(**agg).reset_index()
    nat = long.groupby("carburant").agg(**agg).reset_index()
    for table in (dep, nat):
        table["prix_moyen"] = table["prix_moyen"].round(4)
        table.insert(0, "date_collecte", date_collecte)
    return dep, nat


def ajouter_historique(nouveau: pd.DataFrame, chemin: Path) -> None:
    if chemin.exists():
        ancien = pd.read_csv(chemin, dtype={"departement": str})
        ancien = ancien[ancien["date_collecte"] != nouveau["date_collecte"].iloc[0]]
        nouveau = pd.concat([ancien, nouveau], ignore_index=True)
    nouveau.to_csv(chemin, index=False)


def main() -> None:
    date_collecte = datetime.now(timezone.utc).date().isoformat()
    DATA_DIR.mkdir(exist_ok=True)

    df = pd.DataFrame(parser(telecharger_xml(), date_collecte), columns=COLONNES)
    if len(df) < NB_STATIONS_MIN:
        raise SystemExit(f"Seulement {len(df)} stations lues : source inattendue, rien n'est écrit.")

    df.to_csv(DATA_DIR / "latest.csv", index=False)
    dep, nat = construire_historiques(df, date_collecte)
    ajouter_historique(dep, DATA_DIR / "history_departements.csv")
    ajouter_historique(nat, DATA_DIR / "history_national.csv")
    print(f"{date_collecte} : {len(df)} stations, {df[CARBURANTS].notna().any(axis=1).sum()} avec au moins un prix")


if __name__ == "__main__":
    main()
