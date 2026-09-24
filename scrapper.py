import requests
import zipfile

rep = requests.get("https://donnees.roulez-eco.fr/opendata/instantane_ruptures")

with open("carburant.zip", "wb") as f:
    f.write(rep.content)

with zipfile.ZipFile("carburant.zip", "r") as archive:
    archive.extractall()


