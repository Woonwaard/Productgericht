'''
Versie 3.2, Projectenmodel vernieuwen
Het is wenselijk om het projecten model regelmatig te vernieuwen 
Ervaring leert dat vernieuwen beter werkt richting arcGIS Online als dit vernieuwen geautomatiseerd plaatsvindt
Met het vernieuwen van de oefen laag en het script ervoor als basis maken wij een python scipt om Projecten model te vernieuwen van belang is om te weten dat relatie tussen projecten en clusters n:m is. 
Bij 1 cluster kunnen meerdere projecten zijn. Een project kan meerdere clusters betreffen.

de volgende stappen zijn relevant:
 1a- Controleer de projectinformatie in <uw tabel of view met project data>
 1b- Via Export Table kopier deze view naar tabel Alleprojecten, zodat deze tabel kan worden gekoppeld aan de clusterinformatie
 2a- Haal recent clustermodel op (clusters zijn nodig omdat deze al geocodering hebben en projecten zijn aan clusters gekoppeld)
 2b- Kopieer deze via exportfeatures naar Clustersvoorprojecten neem nu niet alle velden mee.
 3- Via Make query table voeg tabellen Clustervoorprojecten samen met Alleprojecten. Clusternummer is het gemeenschappelijke veld. Genereer nieuwe objectid
 4- Via export features het resultaat kopieren, zodat deze kan worden gedeeld.
 5- Diverse voorbereidingen voor delete en append
 6- Maak tijdelijke bestanden aan, verwijder bestaande data, voeg nieuwe data toe en verwijder de tijdelijke bestanden
25-1-24: Datum vernieuwd komt voortaan uit de view alle_projecten en niet meer uit clustertabel
26-1-24: Via dit script wordt ook de data in de projectenlaag met symbolen vernieuwd. Eerst testen of het werkt op de gewenste manier.
01-2-24: Status van vernieuwen wordt nu via een webhook naar teams gestuurd. 
30-4-24: Het veld omschrijving toegevoegd dit is de lange omschrijving uit de tabel Project_omschrijving
2 aug 2024: Melding naar teams aangepast van connector naar webhook via Power Automate

'''


import os, time, uuid, csv, sys
import arcpy
import pandas as pd
import urllib3
import json, requests

# Start Timer
startTime = time.time()

# Parameters:
#Vervang de locaties door uw eigen locaties op de harde schijf bij het project!!
#Dit is namelijk de locatie van het project en feature layers op de harde schijf.
#Het is aan te bevelen om deze projecten op de C schijf te zetten en niet op One drive of iets anders in de cloud te zetten: Het synchroniseren gaat te landzaam en zal tot foutmeldingen leiden!
Clusterswoonwaard = r"C:\Projecten\Woonwaard_Clusters\Woonwaard_objecten.gdb\WoonwaardClusterModel"
Clustersprojecten = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\Clustersvprojecten"
AlleProjecten = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\AlleProjecten"
Projecten = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\Projecten"
Projecten_nw = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\Projecten_nw"

print("Stap 0 van 6: Script gestart...")
#ophalen data uit de view
import pyodbc

print("Stap 1a samenstellen connectiestring naar sql server")
DRIVER = 'ODBC Driver 18 for SQL Server'
SERVER = '<uw servernaam>'
DATABASE = '<databasenaam>'
USERNAME = '<adminaccount>'
PASSWORD = '<psw>'

print("Testen of tabel Projecten leeg is")
connectionString = f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'
conn = pyodbc.connect(connectionString)
sql_query = pd.read_sql_query("SELECT count(*) FROM <naam van view of tabel met data>",conn)
Aantal = sql_query

print((Aantal == 0).bool())

if (Aantal == 0).bool():
    # Vul hier de juist webhook URL van de werkstroomstap in
    webhook_url = '<vul hier uw Power automate workflow webhook id bij bericht geen data in SQL>'

    # verstuur bericht
    response = requests.post(webhook_url, headers={'Content-Type': 'application/json'})

    sys.exit(0)

print("Projecten is gevuld dus laden zal nu starten")


#Verwijderen van bestaande data vanwege het iedere dag draaien, eerst data van gisteren verwijderen.
if arcpy.Exists(Clustersprojecten):
    arcpy.Delete_management(Clustersprojecten)
if arcpy.Exists(AlleProjecten):
    arcpy.Delete_management(AlleProjecten)

print("Stap 1b data naar csv")
connectionString = f'DRIVER={DRIVER};SERVER={SERVER};DATABASE={DATABASE};UID={USERNAME};PWD={PASSWORD}'
conn = pyodbc.connect(connectionString)
sql_query = pd.read_sql_query("SELECT * FROM arcgis.vw_alle_projecten",conn)
df = pd.DataFrame(sql_query)
df.to_csv (r'C:\csv\projecten\export_projecten.csv', index= False)

print("Stap 1c van 6: Inlezen csv in geodatabase via export table")
newFile = r"C:\csv\projecten\export_projecten.csv"
AlleProjecten = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\AlleProjecten"

out_gdb = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb"
arcpy.conversion.ExportTable(newFile, AlleProjecten)

print("Inlezen csv bestand gereed")

print("Stap 2a van 6: Kopieren van clusterlaag, waarbij een deel van de velden worden meegenomen")
#Define field mapping objects
#fm1, fm2, etc zijn onderdeel van fieldmapping fms
fm1 = arcpy.FieldMap()
fm2 = arcpy.FieldMap()
fm3 = arcpy.FieldMap()
fm5 = arcpy.FieldMap()
fm6 = arcpy.FieldMap()
fm7 = arcpy.FieldMap()
fm8 = arcpy.FieldMap()
fm9 = arcpy.FieldMap()

fms = arcpy.FieldMappings()

#Fields to keep
#adding the fields to their individual field maps
fm1.addInputField(Clusterswoonwaard, "Cluster_nummer")
fm2.addInputField(Clusterswoonwaard, "shape_Length")
fm3.addInputField(Clusterswoonwaard, "shape_Area")
fm5.addInputField(Clusterswoonwaard, "Cluster_naam")
fm6.addInputField(Clusterswoonwaard, "c_gemeente")
fm7.addInputField(Clusterswoonwaard, "CBS_buurt")
fm8.addInputField(Clusterswoonwaard, "CBS_wijk")
fm9.addInputField(Clusterswoonwaard, "Aantal_woningen_in_exploitatie")

#Complete the field map
#adding the components above into the final mapping (fms)   
fms.addFieldMap(fm1)
fms.addFieldMap(fm2)
fms.addFieldMap(fm3)
fms.addFieldMap(fm5)
fms.addFieldMap(fm6)
fms.addFieldMap(fm7)
fms.addFieldMap(fm8)
fms.addFieldMap(fm9)

arcpy.conversion.ExportFeatures(Clusterswoonwaard, Clustersprojecten, "", "", fms)

#variabelen voor make query table
print("Stap 2b van 6: Variabelen voor make query table")
Clustersprojecten = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\Clustersvprojecten"
AlleProjecten = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\AlleProjecten"

arcpy.env.workspace =  r'C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb'
inList = [AlleProjecten, Clustersprojecten]
arcpy.management.CalculateField(
    in_table=Clustersprojecten,
    field="Cluster_nummer",
    expression="""
    left($feature.Cluster_nummer,10)
""",
    expression_type="ARCADE",
    code_block="",
    field_type="TEXT",
    enforce_domains="NO_ENFORCE_DOMAINS"
    )

arcpy.management.CalculateField(
    in_table=AlleProjecten,
    field="Cluster_algemeen",
    expression="""
    left($feature.Cluster_algemeen,10)
""",
    expression_type="ARCADE",
    code_block="",
    field_type="TEXT",
    enforce_domains="NO_ENFORCE_DOMAINS"
    )

Projectinfo = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\Projectinfo"

print("Stap 3 van 6: Make Query Table CLuster en Projecten, via clusternummer")
arcpy.env.workspace =  r'C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb'
arcpy.management.MakeQueryTable(inList, Projectinfo, "ADD_VIRTUAL_KEY_FIELD","", "", "Cluster_nummer = Cluster_algemeen")

print ("Gereed")

arcpy.env.workspace =  r'C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb'
Projectinfo = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\Projectinfo"
ProjectenExport = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\ProjectenExport"

#Verwijderen van bestaande data
if arcpy.Exists(Projecten):
    arcpy.Delete_management(Projecten)
if arcpy.Exists(ProjectenExport):
    arcpy.Delete_management(ProjectenExport)

print("Stap 4a van 6: Resultaat exporteren naar Projecten voor delen naar Online")
arcpy.conversion.ExportFeatures(in_features=Projectinfo, out_features="Projecten")

print ("Gereed")

#Extra stap voor versturen berichten aan rayon export features van nieuwe data naar nieuw
Projecten_nw = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\Projecten_nw"
where_clause="Project_type = 'PO' And Start_jaar > 2023"
if arcpy.Exists(Projecten_nw):
    arcpy.Delete_management(Projecten_nw)
arcpy.conversion.ExportFeatures(Projecten, Projecten_nw, where_clause)


print("Stap 4b van 6: Veld team verwijderen uit het resultaat")
arcpy.env.workspace =  r'C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb'
Projecten = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\Projecten"
in_table = "Projecten"
drop_field = ["Rayon"]
method = "DELETE_FIELDS"
arcpy.management.DeleteField(in_table, drop_field, method)

print("Stap 4c van 6: Toevoegen veld Statusnieuw met eenduidige waarde voor alle projecten")
#aanpassen van status naar een eenduidige waarde zodat dit in het rapport kan worden gebruikt voor filteren en de popup.
arcpy.env.workspace =  r'C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb'
Projecten = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\Projecten"
arcpy.management.CalculateField(
    in_table="Projecten",
    field="StatusNieuw",
    expression="""//  Toekennen tekst aan status van het project voor de diverse bewerkingen
if(left($feature.Status_project,1) == '5'){
  return 'Oplevering';
} else {
  if(Right($feature.Status_project,1) == '7'){
    return 'Oplevering';
  } else {
    if(left($feature.Status_project,1) == '1'){
      return 'Initiatie';
    } else {
      if(Right($feature.Status_project,1) < '5'){
        return 'Initiatie';
    } else {
    if(left($feature.Status_project,1) == '3'){
      return 'Opdracht';
    } else {
      if(Right($feature.Status_project,1) == '5'){
        return 'Opdracht';
    } else {
    if(left($feature.Status_project,1) == '4'){
      return 'Realisatie';
    } else {
      if(Right($feature.Status_project,1) == '6'){
        return 'Realisatie';
    } else {
        return 'Afgerond';
  }}}}}}}}   """,
    expression_type="ARCADE",
    code_block="",
    field_type="TEXT",
    enforce_domains="NO_ENFORCE_DOMAINS"
)

print("Veld status projec is toegevoegd en berekend")
print ("Basis vernieuwen is Gereed")


#Hierna is de code voor het vernieuwen van de feature layer Projecten via Delete en Append methode.
print("Stap 8 updaten van de data online, Projecten")
import arcpy, os, time, uuid
from zipfile import ZipFile
from arcgis.gis import GIS
import arcgis.features

# Overwrite Output
arcpy.env.overwriteOutput = True

# Variabelen
fc = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\Projecten"  # Path to Feature Class
# Het is extreem belangrijk om hier de goede id te plaatsen van de feature layer. 
# Anders kun je oa foutmelding 400 krijgen, mag data niet verwijderen!!
fsItemId = "8363ec89a7974e2b888bb4480f0a7811"                 # Feature Service Item ID van projecten model voor update
featureService = True                                         # True if updating a Feature Service, False if updating a Hosted Table
hostedTable = False                                           # True is updating a Hosted Table, False if updating a Feature Service
layerIndex = 0                                                # Layer Index
disableSync = True                                            # True to disable sync, and then re-enable sync after append, False to not disable sync.  Set to True if sync is not enabled
updateSchema = False                                          # True will remove/add fields from feature service keeping schema in-sync, False will not remove/add fields

arcpy.env.workspace =  r'C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb'
ProjectenExport = r"C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb\ProjectenExport"

if arcpy.Exists(ProjectenExport):
    arcpy.Delete_management(ProjectenExport)

print("Stap 8, 1 van 3 voorbereiden vernieuwen data")

# GIS object aanmaken
print("verbinding maken met ArcGIS Online")
gis = GIS('home')          #

# Maak een variabele UUID voor de geodatabase
gdbId = str(uuid.uuid1())

print("Maak zip bestand")
# Functie om de geodatabase bestand te zippen.
def zipDir(dirPath, zipPath):
#    Zip File Geodatabase
    zipf = ZipFile(zipPath , mode='w')
    gdb = os.path.basename(dirPath)
    for root, _ , files in os.walk(dirPath):
        for file in files:
            if 'lock' not in file:
               filePath = os.path.join(root, file)
               zipf.write(filePath , os.path.join(gdb, file))
    zipf.close()

print("Stap functie zippen is klaar")

print("Aanmaken van een tijdelijk bestand Geodatabase")
gdb = arcpy.CreateFileGDB_management(arcpy.env.scratchFolder, gdbId)[0]

print(gdb)
print("Aanmaken is klaar")

# Exporteren van de feature service naar de tijdelijke geodatabase
new = "ProjectenExport"
fcName = os.path.basename(new)
fcName = fcName.split('.')[-1]
print(fcName)

arcpy.env.workspace =  r'C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb'

Path = format(arcpy.env.scratchFolder)

print(Path, fc)

arcpy.env.workspace =  r'C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb'

print(f"Exporteren van {fcName} naar tijdelijke GDB")
if featureService == True:
    arcpy.conversion.FeatureClassToFeatureClass(fc, gdb, fcName)  

print("Data toegevoegd aan scratch geodb")

# Comprimeer temp FGD naar zip
print("Zipping temp FGD")
zipDir(gdb, gdb + ".zip")

# Upload gezippte bestand Geodatabase
print("Uploading File Geodatabase")
fgd_properties={'title':gdbId, 'tags':'temp file geodatabase', 'type':'File Geodatabase'}
fgd_item = gis.content.add(item_properties=fgd_properties, data=gdb + ".zip")

# Get featureService informatie uit Online
serviceLayer = gis.content.get(fsItemId)
if featureService == True:
    fLyr = serviceLayer.layers[layerIndex]

print("Upload is klaar, is er een view?")    
print(fLyr)

print("Stap 8, 2 van 3 Verwijderen bestaande data")
# Truncate Feature Service
# If views exist, or disableSync = False use delete_features.  OBJECTIDs will not reset
flc = arcgis.features.FeatureLayerCollection(serviceLayer.url, gis)
try:
    if flc.properties.hasViews == True:
        print("Feature Service heeft 1 of meerdere view(s)")
        hasViews = True
except:
    hasViews = False

print(hasViews)
print("Data verwijderen uit de bestaande feature layers en gekoppelde views")
print("Deleting all features")
fLyr.delete_features(where="1=1")

print("Stap 8: 3 van 3, Data online toevoegen via append")
# Append features from featureService class/hostedTable
arcpy.env.workspace =  r'C:\Projecten\WoonwaardProjecten\WoonwaardProjecten.gdb'
nameOflayer = "ProjectenExport"
print("Data toevoegen aan projecten model en views")
print(fgd_item.id)

fLyr.append(item_id=fgd_item.id, upload_format="filegdb", source_table_name=nameOflayer, field_mappings=[], upsert=False)

# Delete Uploaded File Geodatabase
print("Deleting uploaded File Geodatabase")
fgd_item.delete()

# Delete temporary File Geodatabase and zip file
print("Deleting temporary FGD and zip file")
arcpy.Delete_management(gdb)
os.remove(gdb + ".zip")

endTime = time.time()
elapsedTime = round((endTime - startTime) / 60, 2)
print("Script klaar voor Projectendata in {0} minutes".format(elapsedTime))

import requests
import json

# Vul hier de juist webhook URL van de werkstroomstap in
webhook_url = '<vul hier uw Power automate workflow webhook id bij bericht goed bijgewerkt>'

# verstuur bericht
response = requests.post(webhook_url, headers={'Content-Type': 'application/json'})
