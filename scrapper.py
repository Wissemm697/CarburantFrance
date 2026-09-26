import requests
import zipfile
import xml.etree.ElementTree as ET

AllStation = []
carburants_possibles = ["Gazole", "SP95", "SP98", "E10", "E85", "GPLc"]

rep = requests.get("https://donnees.roulez-eco.fr/opendata/instantane_ruptures")

with open("carburant.zip", "wb") as f:
    f.write(rep.content)

with zipfile.ZipFile("carburant.zip", "r") as archive:
    archive.extractall()

tree = ET.parse("PrixCarburants_instantane_ruptures.xml")
root = tree.getroot()

for station in root.findall("pdv"):
    stationEssence = {}
    stationEssence["Code postale"] = station.get("cp")
    stationEssence["Nom de la ville"] = station.find("ville").text
    for prix in station.findall("prix"):
        stationEssence[prix.get("nom")] = prix.get("valeur")

    for carburant in carburants_possibles:
        if carburant not in stationEssence:
            stationEssence[carburant] = "x"

    AllStation.append(stationEssence)
