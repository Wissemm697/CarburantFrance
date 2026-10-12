import csv
import requests
import zipfile
import xml.etree.ElementTree as ET

URL = "https://donnees.roulez-eco.fr/opendata/instantane_ruptures"
CARBURANTS = ["Gazole", "SP95", "SP98", "E10", "E85", "GPLc"]

rep = requests.get(URL, timeout=60)
rep.raise_for_status()

with open("carburant.zip", "wb") as f:
    f.write(rep.content)

with zipfile.ZipFile("carburant.zip", "r") as archive:
    archive.extractall()

tree = ET.parse("PrixCarburants_instantane_ruptures.xml")
root = tree.getroot()

AllStation = []

for station in root.findall("pdv"):
    stationEssence = {}
    stationEssence["id"] = station.get("id")

    cp = station.get("cp")
    stationEssence["code_postal"] = cp
    if cp.startswith(("97", "98")):      # DOM-TOM : département sur 3 chiffres
        stationEssence["departement"] = cp[:3]
    else:
        stationEssence["departement"] = cp[:2]

    ville = station.find("ville")
    if ville is not None and ville.text:
        stationEssence["ville"] = ville.text.strip().upper()

    lat = station.get("latitude")
    lon = station.get("longitude")
    if lat and lon:
        stationEssence["latitude"] = float(lat) / 100000
        stationEssence["longitude"] = float(lon) / 100000

    for prix in station.findall("prix"):
        stationEssence[prix.get("nom")] = float(prix.get("valeur"))

    AllStation.append(stationEssence)

colonnes = ["id", "code_postal", "ville", "departement", "latitude", "longitude"] + CARBURANTS

with open("prix_carburants.csv", "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=colonnes, delimiter=";", restval="")
    writer.writeheader()
    writer.writerows(AllStation)

print(len(AllStation), "stations exportées")