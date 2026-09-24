import xml.etree.ElementTree as ET

test = """
    <magasin>
        <produit nom="Pomme" prix="1.5"/>
        <produit nom="Banane" prix="2.0"/>
        <produit nom="Poire" prix="1.8"/>
    </magasin>
    """
root = ET.fromstring(test)

print(len(root))

for produit in root.findall("produit"):
    print(produit.get("nom"), produit.get("prix"))

print(root[2].get("prix"))