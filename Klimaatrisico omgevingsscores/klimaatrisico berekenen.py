#------------ script header ------------#
#Let op: Om dit script te runnen is een ArcGIS licentie nodig inclusief de module 'Spatal'. Dit omdat er rasterdata wordt gebruikt voor de berekeningen.

__author__ = "Sander Beukers"
__copyright__ = "Copyright 2023, b.analytics"
__credits__ = ["Klimaateffectatlas.nl", "Dutch Green Building Council"]
__license__ = "This code may be copied or distributed without the express permission of b.analytics for use by housing associations only. Use for commercial purposes is strictly prohibited"
__version__ = "1.0"
__maintainer__ = "Sander Beukers","Margriet de Pender"
__email__ = "sbeukers@banalytics.nl""mdepender@woonwaard.nl"
__status__ = "Final"

'''
Zie readme voor toelichting bij script berekenen klimaatrisico's

'''

#------------ import libraries ------------#

import arcpy, time
from arcpy.sa import *

#------------ check license ------------#
'''
via deze aanroep wordt gecontroleerd of de licentie de module 'Spatial' bevat. Deze licentie is nodig voor de diverse spatial analyses.
Indien ja: check de licentie 'uit' zodat deze niet door een ander kan worden gebruikt. 
Indien nee: Dan zal dit script niet kunnen uitvoeren: De spatial analyses zullen een foutmelding geven.
Deze licentie wordt automatisch 'ingechecked' als het script klaar is
'''

arcpy.CheckOutExtension("spatial")

#------------ set global variables ------------#

arcpy.env.overwriteOutput = True
#Indien via pro
aprx = arcpy.mp.ArcGISProject("CURRENT")       
m = aprx.listMaps("Klimaatrisicokaart")[0]

#Indien niet via Pro: let op Current

dataLocation = r'C:\ArcGIS data\FCAB layers met symbols\\'                  	#naam en locatie van het project
inFeatures = "Woonwaard_EenhedenModel"				                            #the pointlayer with addresses to asses
outFeatures = "FCAB1_omgevingsscores_klimaatrisicos_woonwaard" 	                #the resulting layer
UniqueIdentifier = "Eenheidsnr" 				                                #the unique identifier of the point layer, indicating individual adresses

'''
Basis procedure waarin wordt gekeken of de aangeroepen dataset vrij is van een lock. Deze functie wacht totdat er geen lock meer is.
Dit om te vermijden dat het script wordt afgebroken.
'''
def schemaLock():
    #wait a second, then check if a schema lock is present, if so, sleep for another 5 seconds
    time.sleep(1)
    lockTest = arcpy.TestSchemaLock(outFeatures)
    waitTime = 5
    if lockTest != True:
        print('Schema lock on {} encountered, waiting {} seconds...'.format(outFeatures,waitTime))
        time.sleep(waitTime)
        print('Continuing...')

'''
Basis procedure waarin wordt gekeken of de basisdataset met de woonwaard eenheden bestaat en daarna wordt gekopieerd.
Indien geen data wordt het script afgebroken
'''

def copySourcedata():
    #check if inFeatures exist
    if not arcpy.Exists(inFeatures):
        sys.exit('Data \'{}\' niet gevonden, script geannuleerd.'.format(inFeatures))

    #copy source data
    arcpy.management.CopyFeatures(inFeatures, outFeatures)		#Woonwaard data kopieren naar de uitvoer kaart
    addPandInfo()
    

#------------function to add bouwjaar en identificatie van Woonwaard eenheid to outFeatures ------------#

'''
In deze procedure worden de velden bouwjaar en identificatie (BAG pand id) vanuit BAG-pand naar copy van woonwaard eenheden gekopieerd.
Hiervoor worden eerst de BAG panden opgehaald, daarna worden via selectlayerbylocation de panden geselecteerd die dezelfde locatie hebben als de punten van Woonwaard eenheden
De selectie wordt opgeschoond voor panden die nog niet af zijn.
Resultaat wordt gekopieerd naar een laag in het geheugen.
Vervolgens een Spatial join van woonwaard eenheden en selectie van pand die ook naar een nieuwe laag in het werkgeheugen wordt geschreven.
Tenslotte een join field om bouwjaar en identificatie (=bag id pand) aan de uitvoerlaag toe te voegen via eenheidsnr als sleutelveld.

Alternatief: Mogelijk opschonen van selectie van panden aanpassen door bij kopieren (in vorige procedure) naar laag woonwaard eenheden filter toe te voegen op eenheden in exploitatie (is ook minder data). Wordt dan wel een export features, omdat copy features zo te zien geen filter optie heeft.

'''

def addPandInfo ():


    #Indien in Pro gebruik dan de volgende code:
    #pandLyr = 'Pand'
    # toelichting: Pand is laag 4 van de feature service (url kopieren naar browser en dan bij layers het nummer)
    #layer_name = "Pand"
    pandLyr = arcpy.MakeFeatureLayer_management("https://basisregistraties.arcgisonline.nl/arcgis/rest/services/BAG/BAGv3/FeatureServer/4",layer_name)
    global tmp_pandSelection
    tmp_pandSelection = r"memory\tmp_pandSelection"
    tmp_outFeatures = r"memory\tmp_outFeatures"
    
    if not arcpy.Exists(pandLyr):  
        sys.exit('Data \'{}\' niet gevonden, script geannuleerd.'.format(pandLyr))
    
    #clear selections on inFeatures and pandLyr, zodat je het script meerdere keren kunt draaien
    arcpy.SelectLayerByAttribute_management(inFeatures, "CLEAR_SELECTION")
    arcpy.SelectLayerByAttribute_management(pandLyr, "CLEAR_SELECTION")

    #create selection in pandLyr
    arcpy.management.SelectLayerByLocation(in_layer=pandLyr, select_features=inFeatures)	#Selecteer de panden die bij de woonwaard woningen horen

    #remove from selection where reden = 'bouw gestart' or 'bouwvergunning verleend'
    arcpy.management.SelectLayerByAttribute(in_layer_or_view=pandLyr, selection_type="REMOVE_FROM_SELECTION", where_clause="status IN ('Bouw gestart', 'Bouwvergunning verleend')")

    #copy result to memory
    arcpy.CopyFeatures_management(pandLyr, tmp_pandSelection)					#geselecteerde panden in kaartlaag naar een laag in het geheugen(dus niet op schijf)

    #spatial join the selection of pandLyr with inFeatures and write to memory			#Voer een spatial join uit voor bag panden en woonwaard panden en schrijf die naar geheugen
    arcpy.analysis.SpatialJoin(inFeatures, tmp_pandSelection, tmp_outFeatures)

    #join field bouwjaar to outFeatures								# Voer een join field uit tussen kaartlaag met omgevingsrisico's op basis van eenheidsnummer
    schemaLock()
    arcpy.management.JoinField(outFeatures, UniqueIdentifier, tmp_outFeatures, UniqueIdentifier, ["identificatie","bouwjaar"])

    #delete tmp_outFeatures
    arcpy.management.Delete(tmp_outFeatures)

#------------ Hittestress ------------#
'''
In deze procedure worden de volgende acties uitgevoerd:
- Het tiff bestand voor Hittestress wordt opgehaald
- Via extractie van de rasterinformatie naar punten wordt een tijdelijk kaartlaag gecreerd, waarin de data van de input (woonwaard) wordt meegenomen naar de temp output.
- Join field van de kaartlaag met klimaatmodel data met de temp output van de vorige stap.
- Hernoem basisveld uit kaartlaag naar de context van het onderdeel (hittestress).
- Verwijderen van de laag temp output.
- Berekenen van index, bruto risico en volgnr op basis van veld 'rastervalue' van het onderdeel. 
- Verwijderen van de laag met het tiff bestand.

'''
def calculateHittestress():
    #set variables
    hittestressLyr = r"Hittestress door warme nachten 2050 Hoog.tif"
    if not arcpy.Exists(hittestressLyr):  
        m.addDataFromPath(dataLocation + hittestressLyr + ".lyrx")
    
    rasterLyr = arcpy.Raster(hittestressLyr)
    tmp_outLyrHittestress = r"memory\tmp_outLyrHittestress"

    #Extract rastervalue from rasterLyr to tmp_outLyrHittestress
    arcpy.sa.ExtractValuesToPoints(inFeatures, rasterLyr, tmp_outLyrHittestress, "NONE", "VALUE_ONLY")

    #join field
    schemaLock()
    arcpy.management.JoinField(outFeatures, UniqueIdentifier, tmp_outLyrHittestress, UniqueIdentifier, "RASTERVALU")
    
    #rename field RASTERVALU
    schemaLock()
    arcpy.management.AlterField(outFeatures, "RASTERVALU", "hittestress_value", "hittestress_value")

    #delete tmp_outLyrHittestress
    arcpy.management.Delete(tmp_outLyrHittestress)

    #calculate field hittestress_index
    schemaLock()
    arcpy.management.CalculateField(

        in_table=outFeatures, 
        field="hittestress_index", 
        expression="""
        var rastervalue = $feature.hittestress_value;
        var ranking = 
        WHEN(
            rastervalue == null, 'Geen', 
            rastervalue <= 0.65, 'minder dan 2 weken', 
            rastervalue <= 0.85, '2-3 weken', 
            rastervalue > 0.85, 'meer dan 3 weken', 
            'Geen'
        );
        return ranking""", 
        expression_type="ARCADE")[0]

    #calculate field hittestress_bruto_risico
    schemaLock()
    arcpy.management.CalculateField(

        in_table=outFeatures, 
        field="hittestress_bruto_risico", 
        expression="""
        var rastervalue = $feature.hittestress_value;
        var ranking = 
        WHEN(
            rastervalue == null, 'Geen', 
            rastervalue <= 0.65, 'Laag', 
            rastervalue <= 0.85, 'Middel', 
            rastervalue > 0.85, 'Hoog', 
            'Geen'
        );
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #calculate field hittestress_sequence
    schemaLock()
    arcpy.management.AddField(outFeatures, "hittestress_sequence", "SHORT")
    
    schemaLock()
    arcpy.management.CalculateField(

        in_table=outFeatures, 
        field="hittestress_sequence", 
        expression="""
        var rastervalue = $feature.hittestress_value;
        var ranking = 
        WHEN(
            rastervalue == null, 0, 
            rastervalue <= 0.65, 1, 
            rastervalue <= 0.85, 2, 
            rastervalue > 0.85, 3, 
            0
        );
        return ranking""", 
        expression_type="ARCADE")[0]

    #remove hittestressLyr
    arcpy.management.Delete(hittestressLyr)

#------------ Droogte ------------#
'''
Droogte bestaat uit 3 subonderwerpen:
1. Natuurbrandgevoeligheid
2. Paalrot
3. Verschilzetting of fundamentsproblemen

Ad 1 Voor onderdeel Natuurbrandgevoeligheid worden de volgende acties uitgevoerd:
- Het tiff bestand voor Natuurbrand wordt opgehaald
- Via extractie van de rasterinformatie naar punten wordt een tijdelijk kaartlaag gecreerd, waarin de data van de input (woonwaard) wordt meegenomen naar de temp output.
- Join field van de kaartlaag met klimaatmodel data met de temp output van de vorige stap.
- Hernoem basisveld uit kaartlaag naar de context van het onderdeel (natuurbrand).
- Verwijderen van de laag met het tiff bestand en van de laag temp output.
- Berekenen van index, bruto risico en volgnr op basis van veld 'rastervalue' van het onderdeel. 

'''

def calculateDroogte():
    
    #set variables
    natuurbrandLyr = r"Natuurbrandgevoeligheid 2050 Hoog.tif"
    tmp_outLyrNatuurbrand = r"memory\tmp_outLyrNatuurbrand"
    
    if not arcpy.Exists(natuurbrandLyr):  
        m.addDataFromPath(dataLocation + natuurbrandLyr + ".lyrx")

    rasterLyr = arcpy.Raster(natuurbrandLyr)

    #Extract rastervalue from rasterLyr to tmp_outLyrHittestress
    arcpy.sa.ExtractValuesToPoints(inFeatures, rasterLyr, tmp_outLyrNatuurbrand, "NONE", "VALUE_ONLY")

    #join field
    schemaLock()
    arcpy.management.JoinField(outFeatures, UniqueIdentifier, tmp_outLyrNatuurbrand, UniqueIdentifier, "RASTERVALU")

    #rename field RASTERVALU
    schemaLock()
    arcpy.management.AlterField(outFeatures, "RASTERVALU", "natuurbrand_value", "natuurbrand_value")
    
    #remove memory layers
    arcpy.management.Delete(natuurbrandLyr)
    arcpy.management.Delete(tmp_outLyrNatuurbrand)

    #Calculate field natuurbrand_value
    schemaLock()
    arcpy.management.CalculateField(

        in_table=outFeatures, 
        field="natuurbrand_index", 
        expression="$feature.natuurbrand_value", 
        expression_type="ARCADE")[0]

    #calculate field natuurbrand_brutorisico
    schemaLock()
    arcpy.management.CalculateField(

        in_table=outFeatures, 
        field="natuurbrand_bruto_risico", 
        expression="""
        var rastervalue = $feature.natuurbrand_value;
        var ranking = 
        WHEN(
            rastervalue == null, 'Geen', 
            rastervalue <= 1, 'Geen', 
            rastervalue <= 2, 'Middel', 
            rastervalue <= 3, 'Hoog', 
            'Geen'
        );
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #calculate field natuurbrand_sequence
    schemaLock()
    arcpy.management.AddField(outFeatures, "natuurbrand_sequence", "SHORT")
    
    schemaLock()
    arcpy.management.CalculateField(

        in_table=outFeatures, 
        field="natuurbrand_sequence", 
        expression="""
        var rastervalue = $feature.natuurbrand_value;
        var ranking = 
        WHEN(
            rastervalue == null, 0, 
            rastervalue <= 1, 0, 
            rastervalue <= 2, 1, 
            rastervalue <= 3, 2, 
            0
        );
        return ranking""", 
        expression_type="ARCADE")[0]

'''
Ad 2 Voor onderdeel Paalrot worden de volgende acties uitgevoerd:
- Het tiff bestand voor Paalrot wordt opgehaald (deze tiff bevat ook de informatie voor verschilzetting)
- Via extractie van de rasterinformatie naar punten wordt een tijdelijk kaartlaag gecreerd, waarin de data van de input (woonwaard) wordt meegenomen naar de temp output.
- Join field van de kaartlaag met klimaatmodel data met de temp output van de vorige stap.
- Hernoem basisveld uit kaartlaag naar de context van het onderdeel (paalrot).
- Berekenen van index, bruto risico en volgnr op basis van veld 'rastervalue' van het onderdeel. 

Tijdelijke berstanden worden niet verwijderd omdat deze data ook nodig is voor bepalen van verschilzetting (gemeenschappelijke data)

'''
    
    #set variabels
    paalrotLyr = r"Risico Paalrot 2050 Hoog"
    tmp_outLyrPaalrot = r"memory\tmp_outLyrPaalrot"
    fieldPaalrot = "sterke_c_2"
    fieldVerschilzetting = "sterke_c_1"

    if not arcpy.Exists(paalrotLyr):  
        m.addDataFromPath(dataLocation + paalrotLyr + ".lyrx")

    #spatial join the selection of pandLyr with inFeatures and write to memory
    arcpy.analysis.SpatialJoin(inFeatures, paalrotLyr, tmp_outLyrPaalrot)

    #join field sterke_c_2 to outFeatures
    schemaLock()
    arcpy.management.JoinField(outFeatures, UniqueIdentifier, tmp_outLyrPaalrot, UniqueIdentifier, fieldPaalrot)

    #rename field sterke_c_2
    schemaLock()
    arcpy.management.AlterField(outFeatures, fieldPaalrot, "paalrot_value", "paalrot_value")
    
    #calculate field paalrot_index
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="indexscore_paalrot", 
        expression="""
        var value = $feature.paalrot_value; 
        var bouwjaar = $feature.bouwjaar; 

        if(bouwjaar > 1975) { 
            var ranking = 'Bouwjaar > 1975' 
        } else {
            var ranking =
            WHEN(
                value == null, 'NoData', 
                value <= 0, 'NoData', 
                value <= 0.8, '> 0 AND < = 0,8', 
                value <= 3, '> 0,8 AND < = 3', 
                value <= 6, '> 3 AND < = 6', 
                value <= 15, '> 6 AND < = 15',
                value <= 100, '> 15 AND < = 100',
                'Geen'
            );
        }
        return ranking""", 
        expression_type="ARCADE")[0]

    #calculate field paalrot_bruto risico
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="paalrot_bruto_risico", 
        expression="""
        var value = $feature.paalrot_value; 
        var bouwjaar = $feature.bouwjaar; 


        if(bouwjaar > 1975) { 
            var ranking = 'nvt' 
        }
        else {
            var ranking = 
            WHEN(
                value == null, 'Geen', 
                value <= 0, 'Geen', 
                value <= 0.8, 'Zeer laag', 
                value <= 3, 'Laag', 
                value <= 6, 'Middel', 
                value <= 15, 'Hoog',
                value <= 100, 'Zeer hoog',
                'Geen'
            );
        }
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #calculate field paalrot_sequece
    schemaLock()
    arcpy.management.AddField(outFeatures, "paalrot_sequence", "SHORT")
    
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="paalrot_sequence", 
        expression="""
        var value = $feature.paalrot_value; 
        var bouwjaar = $feature.bouwjaar; 


        if(bouwjaar > 1975) { 
            var ranking = 0
        }
        else {
            var ranking = 
            WHEN(
                value == null, 1, 
                value <= 0, 1, 
                value <= 0.8, 2, 
                value <= 3, 3, 
                value <= 6, 4, 
                value <= 15, 5,
                value <= 100, 6,
                0
            );
        }
        return ranking""", 
        expression_type="ARCADE")[0]

'''
Ad 3 Voor onderdeel Verschilzetting worden de volgende acties uitgevoerd:
- join field van de kaartlaag met klimaatmodel data met de temp output van de vorige paalrot om de verschilzetting data vast te leggen.
- Hernoem basisveld uit kaartlaag naar de context van het onderdeel (verschilzetting).
- Via extractie van de rasterinformatie naar punten wordt een tijdelijk kaartlaag gecreerd, waarin de data van de input (woonwaard) wordt meegenomen naar de temp output.
- Berekenen van index, bruto risico en volgnr op basis van veld 'rastervalue' van het onderdeel. 
- Verwijderen van de laag met het tiff bestand en van de laag temp output (van paalrot).

'''

    #join field verschilzetting toevoegen
    schemaLock()
    arcpy.management.JoinField(outFeatures, UniqueIdentifier, tmp_outLyrPaalrot, UniqueIdentifier, fieldVerschilzetting)
    
    schemaLock()
    arcpy.management.AlterField(outFeatures, fieldVerschilzetting, "verschilzetting_value", "verschilzetting_value")
        
    #calculate field verschilzetting_index
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="indexscore_verschilzetting", 
        expression="""
        var value = $feature.verschilzetting_value; 
        var ranking =
        WHEN(
            value == null, 'NoData', 
            value <= 0, 'NoData', 
            value <= 1, '> 0 AND < = 1', 
            value <= 5, '> 1 AND < = 5', 
            value <= 10, '> 5 AND < = 10', 
            value <= 25, '> 10 AND < = 25',
            value <= 100, '> 25 AND < = 100',
            'Geen'
        );
        return ranking""", 
        expression_type="ARCADE")[0]

    #calculate field verschilzetting_bruto risico
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="verschilzetting_bruto_risico", 
        expression="""
        var value = $feature.verschilzetting_value; 
        var ranking =
        WHEN(
            value == null, 'Geen', 
            value <= 0, 'Geen', 
            value <= 1, 'Zeer Laag', 
            value <= 5, 'Laag', 
            value <= 10, 'Middel', 
            value <= 25, 'Hoog',
            value <= 100, 'Zeer Hoog',
            'Geen'
        );
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #calculate field verschilzetting_sequence
    schemaLock()
    arcpy.management.AddField(outFeatures, "verschilzetting_sequence", "SHORT")
    
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="verschilzetting_sequence", 
        expression="""
        var value = $feature.verschilzetting_value; 
        var ranking =
        WHEN(
            value == null, 0, 
            value <= 0, 0, 
            value <= 1, 1, 
            value <= 5, 2, 
            value <= 10, 3, 
            value <= 25, 4,
            value <= 100, 5,
            0
        );
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #remove memory layers
    arcpy.management.Delete(paalrotLyr)
    arcpy.management.Delete(tmp_outLyrPaalrot)

'''
Wateroverlast bestaat uit 2 subonderwerpen:
1. Waterdiepte bij hevige neerslag
2. Grondwateroverlast

Ad 1 Voor onderdeel Waterdiepte bij hevige neerslag:
Bij dit onderdeel gaan wij voor de Woonwaard panden bepalen welke dieptes relevant kunnen zijn met een omtrek van 2 meter om een pand.
Daarna wordt deze data 'terugverwerkt' naar de eenheden in het pand.

De volgende acties worden voor Waterdiepte uitgevoerd
- Basis is geselecteerde woonwaard panden (van begin script)
- Een buffer van 2m maken rondom deze panden
- Het tiff bestand voor Waterdiepte wordt opgehaald
- Totalen van rasterwaardes worden berekend voor de intersecties tussen data uit pandenlaag met buffer en het tiff bestand voor waterdiepte.
  Resultaat is een tabel met data.
- Join field van de kaartlaag met klimaatmodel data met de output van de vorige stap via bag identificatie (BAG id van het pand).
- Hernoem basisveld uit kaartlaag naar de context van het onderdeel (natuurbrand).
- Berekenen van index, bruto risico en volgnr op basis van veld 'rastervalue' van het onderdeel. 
- Verwijderen van de tijdelijke laag met het tiff bestand, statistieken tabel en pandlagen.

'''   
 
def calculateWateroverlast():
    
    tmp_pandSelectionBuf = r"memory\tmp_pandSelectionBuf"
    
    #buffer van 2 meter toepassen op tmp_pandSelection
    arcpy.analysis.Buffer(in_features=tmp_pandSelection, out_feature_class=tmp_pandSelectionBuf, buffer_distance_or_field="2 Meters")

    #MAX waterdiepte overbrengen naar tempLyrBuf
    waterdiepteLyr = r"Waterdiepte bij intense neerslag - 1-100 jaar.tif"
    
    if not arcpy.Exists(waterdiepteLyr):  
        m.addDataFromPath(dataLocation + waterdiepteLyr + ".lyrx")
    
    ZoneField = "Identificatie"
    tmp_ZonalStats = r"memory\tmp_ZonalStats"
    ZonalStatisticsAsTable(tmp_pandSelectionBuf, ZoneField, waterdiepteLyr, tmp_ZonalStats, "DATA", "MAXIMUM")

    #MAX waterdiepte overbrengen naar verblijfsobjecten obv pand_id
    inField = "Identificatie"
    joinField = "Identificatie"
    
    schemaLock()
    arcpy.management.JoinField(in_data=outFeatures, in_field=inField, join_table=tmp_ZonalStats, join_field=joinField, fields=["MAX"])[0]
    
    schemaLock()
    arcpy.management.AlterField(outFeatures, "MAX", "waterdiepte_value", "waterdiepte_value")
    
    #calculate field waterdiepte_index
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="indexscore_waterdiepte_regenbui", 
        expression="""
        var rastervalue = $feature.waterdiepte_value; 
        var ranking = 
        WHEN(
            rastervalue == null, 'NoData', 
            rastervalue <= 1, '<= 10cm (1)', 
            rastervalue <= 2, '> 10 - 15 cm (2)', 
            rastervalue <= 3, '> 15 - 20 cm (3)', 
            rastervalue <= 4, '> 20-30 cm (4)', 
            rastervalue <= 5, '> 30 cm (5)', 
            'Geen'
        ); 
        return ranking""", 
        expression_type="ARCADE")[0]

    #calculate field waterdiepte bruto risico
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="waterdiepte_regenbui_bruto_risico", 
        expression="""
        var rastervalue = $feature.waterdiepte_value; 
        var bouwjaar = $feature.bouwjaar;
        if(bouwjaar > 2012){ 
            var ranking = 'Bouwjaar > 2012'; return ranking
        } 
        else { 
            var ranking = 
            WHEN(
                rastervalue == null, 'Geen', 
                rastervalue <= 1, 'Zeer Laag', 
                rastervalue <= 2, 'Laag', 
                rastervalue <= 3, 'Middel', 
                rastervalue <= 4, 'Hoog', 
                rastervalue <= 5, 'Zeer Hoog', 
                'Geen'
            ); 
            return ranking 
        }""", 
        expression_type="ARCADE")[0]
    
    #calculate field waterdiepte sequence
    schemaLock()
    arcpy.management.AddField(outFeatures, "waterdiepte_regenbui_sequence", "SHORT")
    
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="waterdiepte_regenbui_sequence", 
        expression="""
        var rastervalue = $feature.waterdiepte_value; 
        var bouwjaar = $feature.bouwjaar;
        if(bouwjaar > 2012){ 
            var ranking = 0; return ranking
        } 
        else { 
            var ranking = 
            WHEN(
                rastervalue == null, 1, 
                rastervalue <= 1, 2, 
                rastervalue <= 2, 3, 
                rastervalue <= 3, 4, 
                rastervalue <= 4, 5, 
                rastervalue <= 5, 6, 
                0
            ); 
            return ranking 
        }""", 
        expression_type="ARCADE")[0]
    
    #remove memory layers
    arcpy.management.Delete(tmp_pandSelectionBuf)
    arcpy.management.Delete(tmp_pandSelection)
    arcpy.management.Delete(tmp_ZonalStats)
    arcpy.management.Delete(waterdiepteLyr)

'''
Ad 2 Voor onderdeel grondwateroverlast:
Grondwateroverlast wordt bepaald door het combineren van 3 factoren:
Kan op grondwateroverlast, grondwaterstand nu en bodemdaling door ophoging.
Via rastervergelijk met woonwaard woningen wordt de informatie aan de kaartlaag met omgevingsrisico's toegevoegd.

De volgende acties worden voor grondwater overlast uitgevoerd
- De tiff bestand voor grondwateroverlast, grondwaterstand nu en bodemdaling door ophoging worden opgehaald
Onderdeel grondwater overlast uitwerken:
- Data uit het rasterlaag grondwateroverlast exporteren naar punten
- Join field van de puntenkaart van de woonwaard woningen met de punten van de kaart
- Hernoem basisveld uit kaartlaag naar de context van het onderdeel (grondwater).
- Berekenen van index, classificatie op basis van veld 'rastervalue' van het onderdeel grondwateroverlast. 

'''   
    
    #grondwateroverlast variabelen definieren
    tmp_grondwateroverlastLyr = r"memory\tmp_grondwateroverlastLyr"
    tmp_outTableGrondwaterstand = r"memory\tmp_outTableGrondwaterstand"
    tmp_outTableBodemdaling = r"memory\tmp_outTableBodemdaling"
    
    #koppelen tiff bestand grondwateroverlast
    grondwateroverlastLyr = 'Ontwikkeling kans grondwateroverlast 2050 Hoog'
    if not arcpy.Exists(grondwateroverlastLyr):  
        m.addDataFromPath(dataLocation + grondwateroverlastLyr + ".lyrx")

    #koppelen tiff bestand grondwaterstand
    grondwaterstandLyr = "Gemiddelde Hoogste Grondwaterstand Huidig.tif"
    if not arcpy.Exists(grondwaterstandLyr):  
        m.addDataFromPath(dataLocation + grondwaterstandLyr + ".lyrx")

    #koppelen tiff bestand grondwateroverlast
    bodemdalingLyr = "Bodemdaling door ophoging 2020 2050.tif"
    if not arcpy.Exists(bodemdalingLyr):  
        m.addDataFromPath(dataLocation + bodemdalingLyr + ".lyrx")


    #bepalen waardes voor grondwateroverlast
    arcpy.analysis.SpatialJoin(inFeatures, grondwateroverlastLyr, tmp_grondwateroverlastLyr)
    
    schemaLock()
    arcpy.management.JoinField(in_data=outFeatures, in_field=UniqueIdentifier, join_table=tmp_grondwateroverlastLyr, join_field=UniqueIdentifier, fields=["gridcode"])
    
    schemaLock()
    arcpy.management.AlterField(outFeatures, "gridcode", "grondwateroverlast_value", "grondwateroverlast_value")
    
    #calculate field grondwater index
    schemaLock()
    arcpy.management.AddField(outFeatures, "indexscore_grondwateroverlast", "SHORT")
    
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="indexscore_grondwateroverlast", 
        expression="""
        var rastervalue = $feature.grondwateroverlast_value; 
        var ranking = 
        WHEN(
            rastervalue == null, '0', 
            rastervalue <= 1, '0', 
            rastervalue <= 2, '1', 
            rastervalue <= 3, '1', 
            rastervalue <= 4, '1', 
            rastervalue <= 5, '0', 
            '0'
        ); 
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #calculate field grondwateroverlast_classificatie
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="classificatie_grondwateroverlast", 
        expression="""
        var rastervalue = $feature.grondwateroverlast_value; 
        var ranking = 
        WHEN(
            rastervalue == null, 'NoData', 
            rastervalue <= 1, 'Kleine toename kans (1)', 
            rastervalue <= 2, 'Aanmerkelijke toename kans (2)', 
            rastervalue <= 3, 'Grote toename kans (3)', 
            rastervalue <= 4, 'Zeer grote toename kans (4)', 
            rastervalue <= 5, 'Kleine kans door lage grondwaterstand (5)', 
            'Geen'
        ); 
        return ranking""", 
        expression_type="ARCADE")[0]

    #bepalen waardes voor grondwaterstand huidig
'''
- Data uit het rasterlaag grondwaterstand nu samenvatten naar waardes per punt voor woonwaard woningen en toevoegen aan tijdelijke tabel
- Join field omgevingsrisico data met net aangemaakte tijdelijke tabel
- Hernoem basisveld uit kaartlaag naar de context van het onderdeel (grondwaterstand).
- Berekenen van index, classificatie op basis van veld 'rastervalue' van het onderdeel grondwaterstand. 

'''   

    Sample(grondwaterstandLyr,outFeatures,tmp_outTableGrondwaterstand)
    joinField = 'Gemiddelde_Hoogste_Grondwaterstand_Huidig_Band_1'
    
    schemaLock()
    arcpy.management.JoinField(in_data=outFeatures, in_field='OBJECTID', join_table=tmp_outTableGrondwaterstand, join_field=outFeatures, fields=joinField)
    
    schemaLock()
    arcpy.management.AlterField(outFeatures, "Gemiddelde_Hoogste_Grondwaterstand_Huidig_Band_1", "grondwaterstand_value", "grondwaterstand_value")
    
    #Calculate indexscore grondwaterstand
    schemaLock()
    arcpy.management.AddField(outFeatures, "indexscore_grondwaterstand", "SHORT")
    
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="indexscore_grondwaterstand",
        expression="""
        var rastervalue = $feature.grondwaterstand_value; 
        var ranking = 
        WHEN(
            rastervalue == null, '0', 
            rastervalue <= 1, '1', 
            rastervalue > 1, '0', 
            '0'
        ); 
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #Calculate classificatie grondwaterstand
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="classificatie_grondwaterstand",
        expression="""
        var rastervalue = $feature.grondwaterstand_value; 
        var ranking = 
        WHEN(
            rastervalue == null, 'NoData', 
            rastervalue <= 1, '<= 1m', 
            rastervalue > 1, '> 1m', '0'
        ); 
        return ranking""", 
        expression_type="ARCADE")[0]

    #bepalen waarde voor bodemdaling
'''
- Data uit het rasterlaag bodemdaling door ophoging samenvatten naar waardes per punt voor woonwaard woningen en toevoegen aan tijdelijke tabel
- Join field omgevingsrisico data met net aangemaakte tijdelijke tabel
- Hernoem basisveld uit kaartlaag naar de context van het onderdeel (bodemdaling).
- Berekenen van index, classificatie op basis van veld 'rastervalue' van het onderdeel bodemdaling. 

''' 
    Sample(bodemdalingLyr,outFeatures,tmp_outTableBodemdaling)
    joinField = 'Bodemdaling_door_ophoging_2020_2050_Band_1'
    
    schemaLock()
    arcpy.management.JoinField(in_data=outFeatures, in_field='OBJECTID', join_table=tmp_outTableBodemdaling, join_field=outFeatures, fields=joinField)
    
    schemaLock()
    arcpy.management.AlterField(outFeatures, "Bodemdaling_door_ophoging_2020_2050_Band_1", "bodemdaling_value", "bodemdaling_value")
    
    #Calculate indexscore bodemdaling
    schemaLock()
    arcpy.management.AddField(outFeatures, "indexscore_bodemdaling", "SHORT")
    
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="indexscore_bodemdaling", 
        expression="""
        var rastervalue = $feature.bodemdaling_value; 
        var ranking = 
        WHEN(
            rastervalue == null, '0', 
            rastervalue <= 0.5, '0', 
            rastervalue > 0.5, '1', '0'
        ); 
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #Calculate classificatie bodemdaling
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="classificatie_bodemdaling",
        expression="""
        var rastervalue = $feature.bodemdaling_value; 
        var ranking = 
        WHEN(
            rastervalue == null, 'NoData', 
            rastervalue <= 0.5, '<= 50cm', 
            rastervalue > 0.5, '> 50cm', '0'
        ); 
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #Calculate total indexscore
'''
Berekenen van de totale bruto risico's voor grondwateroverlast:
- Berekenen van bruto risico grondwateroverlast, volgnr op basis van de totalen .
- Opschonen van de diverse tijdelijke kaartlagen 

''' 
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="totale_indexscore_grondwateroverlast", 
        expression="""$feature.indexscore_grondwateroverlast + $feature.indexscore_grondwaterstand + $feature.indexscore_bodemdaling""", 
        expression_type="ARCADE")[0]
    
    #Calculate totaal indexscore grondwateroverlast
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="grondwateroverlast_bruto_risico", 
        expression="""
        var rastervalue = $feature.totale_indexscore_grondwateroverlast; 
        var ranking = 
        WHEN(
            rastervalue == null, 'Geen',
            rastervalue <= 0, 'Geen', 
            rastervalue <= 1, 'Laag', 
            rastervalue <= 2, 'Middel',
            rastervalue <= 3, 'Hoog', 
            '0'
        ); 
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #Calculate totale grondwateroverlast sequence
    schemaLock()
    arcpy.management.AddField(outFeatures, "grondwateroverlast_sequence", "SHORT")
    
    schemaLock()
    arcpy.management.CalculateField(
        
        in_table=outFeatures, 
        field="grondwateroverlast_sequence", 
        expression="""
        var rastervalue = $feature.totale_indexscore_grondwateroverlast; 
        var ranking = 
        WHEN(
            rastervalue == null, 0,
            rastervalue <= 0, 0, 
            rastervalue <= 1, 1, 
            rastervalue <= 2, 2,
            rastervalue <= 3, 3, 
            0
        ); 
        return ranking""", 
        expression_type="ARCADE")[0]

    #clear memory
    arcpy.management.Delete(grondwateroverlastLyr)
    arcpy.management.Delete(grondwaterstandLyr)
    arcpy.management.Delete(bodemdalingLyr)
    arcpy.management.Delete(tmp_grondwateroverlastLyr)
    arcpy.management.Delete(tmp_outTableGrondwaterstand)
    arcpy.management.Delete(tmp_outTableBodemdaling)

'''
Overstroming bestaat uit 2 subonderwerpen:
1. Waterdiepte
2. Overstromingskans

Ad 1 : Waterdiepte bij overstroming
De volgende acties worden voor Waterdiepte uitgevoerd
- De tiff bestanden voor Maximale waterdiepte en plaatsgebonden overstromingskans worden opgehaald
- Data uit het rasterlaag waterdiepte exporteren naar punten in een tijdelijke laag
- Join field van de kaartlaag met klimaatmodel data met de output van de vorige stap.
- Hernoem basisveld uit kaartlaag naar de context van het onderdeel (waterdiepte).
- Berekenen van index, bruto risico en volgnr op basis van veld 'rastervalue' van het onderdeel. 

'''  
    def calculateOverstroming():

    #variabelen
    #koppelen tiff bestand maximale waterdiepte   
    waterdiepteLyr = "MaximaleWaterdiepteNederland.tif"
    if not arcpy.Exists(waterdiepteLyr):  
        m.addDataFromPath(dataLocation + waterdiepteLyr + ".lyrx")
    tmp_waterdiepteLyr = r"memory\tmp_waterdiepteLyr"

    #koppelen tiff bestand plaatsgebonden overstromingskans   
    overstromingLyr = "Plaatsgebonden overstromingskans 2050 20cm.tif"
    if not arcpy.Exists(overstromingLyr):  
        m.addDataFromPath(dataLocation + overstromingLyr + ".lyrx")
    tmp_overstromingLyr = r"memory\tmp_overstromingLyr"

    #exporteren van rasterinformatie naar de punten van de woonwaard woningen in een tijdelijke laag    
    arcpy.sa.ExtractValuesToPoints(inFeatures, waterdiepteLyr, tmp_waterdiepteLyr, "NONE", "VALUE_ONLY")
    
    schemaLock()
    arcpy.management.JoinField(in_data=outFeatures, in_field=UniqueIdentifier, join_table=tmp_waterdiepteLyr, join_field=UniqueIdentifier, fields=["RASTERVALU"])
    
    schemaLock()
    arcpy.management.AlterField(outFeatures, "RASTERVALU", "waterdiepteoverstroming_value", "waterdiepteoverstroming_value")
    
    #Calculate maximale waterdiepte index
    schemaLock()
    arcpy.management.CalculateField(
        in_table=outFeatures, 
        field="indexscore_waterdiepteoverstroming", 
        expression="""
        var value = $feature.waterdiepteoverstroming_value; 
        var ranking = 
            WHEN(
                value == null, 'NoData', 
                value < 0, 'NoData', 
                value <= 0.2, '< = 0.2 m', 
                value <= 1, '> 0.2 - 1 m', 
                value <= 2.6, '> 1 m - 2,6 m', 
                value > 2.6, '> 2.6 m', 
                'NoData'
            );
        return ranking""", 
        expression_type="ARCADE")[0]

    #Calculate maximale waterdiepte bruto risico
    schemaLock()
    arcpy.management.CalculateField(
        in_table=outFeatures, 
        field="waterdiepteoverstroming_bruto_risico", 
        expression="""
        var value = $feature.waterdiepteoverstroming_value; 
        var ranking = 
            WHEN(
                value == null, 'Geen', 
                value < 0, 'Geen', 
                value <= 0.2, 'Zeer laag', 
                value <= 1, 'Laag', 
                value <= 2.6, 'Middel', 
                value > 2.6, 'Hoog', 
                'Geen'
            );
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #Calculate maximale waterdiepte sequence
    schemaLock()
    arcpy.management.AddField(outFeatures, "waterdiepteoverstroming_sequence", "SHORT")
    
    schemaLock()
    arcpy.management.CalculateField(
        in_table=outFeatures, 
        field="waterdiepteoverstroming_sequence", 
        expression="""
        var value = $feature.waterdiepteoverstroming_value; 
        var ranking = 
            WHEN(
                value == null, 0, 
                value < 0, 0, 
                value <= 0.2, 1, 
                value <= 1, 2, 
                value <= 2.6, 3, 
                value > 2.6, 4, 
                0
            );
        return ranking""", 
        expression_type="ARCADE")[0]

'''
Ad 2 : Plaatsgebonden overstromingskans
De volgende acties worden voor overstromingskans uitgevoerd
- Data uit het rasterlaag overstromingskans exporteren naar punten in een tijdelijke laag
- Join field van de kaartlaag met klimaatmodel data met de output van de vorige stap.
- Hernoem basisveld uit kaartlaag naar de context van het onderdeel (overstromingskans).
- Berekenen van index, bruto risico en volgnr op basis van veld 'rastervalue' van het onderdeel. 
- Verwijderen van de tijdelijke lagen met de tiff bestanden en tussenlagen.

'''  

    Sample(overstromingLyr,inFeatures,tmp_overstromingLyr)
    joinField = 'Plaatsgebonden_overstromingskans_2050_20cm_Band_1'
    
    schemaLock()
    arcpy.management.JoinField(outFeatures, "OBJECTID", tmp_overstromingLyr, inFeatures, joinField)
    
    schemaLock()
    arcpy.management.AlterField(outFeatures ,joinField, "overstroming_value", "overstroming_value")
    
    #Calculate plaatsgebonden overstromingskans index
    schemaLock()
    arcpy.management.CalculateField(
        in_table=outFeatures, 
        field="indexscore_plaatsgebonden_overstromingskans", 
        expression="""var value = $feature.overstroming_value; 
        var ranking = 
        WHEN(
            value == null, 'NoData', 
            value <= 2.0, 'Zeer kleine kans tot extreem kleine kans: > 1/3.000 per jaar', 
            value <= 3.0, 'Kleine kans: > 1/300 tot 1/3000 per jaar', 
            value <= 4.0, 'Middelgrote kans: > 1/30 tot 1/300 per jaar', 
            value <= 5.0, 'Grote kans: > 1/30 per jaar', 
            'Geen'
        );
        return ranking""", 
        expression_type="ARCADE")[0]

    #Calculate plaatsgebonden overstromingskans bruto risico
    schemaLock()
    arcpy.management.CalculateField(
        in_table=outFeatures, 
        field="plaatsgebonden_overstromingskans_bruto_risico", 
        expression="""var value = $feature.overstroming_value; 
        var ranking = 
        WHEN(
            value == null, 'Geen', 
            value <= 2.0, 'Zeer laag', 
            value <= 3.0, 'Laag', 
            value <= 4.0, 'Middel', 
            value <= 5.0, 'Hoog', 
            'Geen'
        );
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #Calculate plaatsgebonden overstromingskans volgnr
    schemaLock()
    arcpy.management.AddField(outFeatures, "plaatsgebonden_overstromingskans_sequence", "SHORT")
    
    schemaLock()
    arcpy.management.CalculateField(
        in_table=outFeatures, 
        field="plaatsgebonden_overstromingskans_sequence", 
        expression="""var value = $feature.overstroming_value; 
        var ranking = 
        WHEN(
            value == null, 0, 
            value <= 2.0, 1, 
            value <= 3.0, 2, 
            value <= 4.0, 3, 
            value <= 5.0, 4, 
            0
        );
        return ranking""", 
        expression_type="ARCADE")[0]
    
    #clear memory
    arcpy.management.Delete(waterdiepteLyr)
    arcpy.management.Delete(tmp_waterdiepteLyr)
    arcpy.management.Delete(overstromingLyr)
    arcpy.management.Delete(tmp_overstromingLyr)

'''
Uitvoeren van de script vind plaats, door de regels hieronder 'van commentaar af te halen'.
Hierdoor worden alle procedures/functies hierboven uitgevoerd.

'''

#copySourcedata()
#calculateHittestress()
#calculateDroogte()
#calculateWateroverlast()
#calculateOverstroming()