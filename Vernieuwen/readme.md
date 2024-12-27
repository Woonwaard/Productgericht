Deze map bevat diverse scripts die wij hebben gemaakt om onze ArcGIS producten automatisch te kunnen vernieuwen.
Hiervoor hebben wij een kleine windows server in Azure laten inrichten.
Op deze machine staat:
- ArcGIS Pro.
- inrichting om de scripts via de taskscheduler te kunnen draaien.

Alle scripts zijn gebaseerd op een product specfiek ArcGIS Pro project. Deze bevat ook de data die wij naar de online omgeving opsturen.
U zult dus eerst het project moeten aanmaken en daarna de verwijzingen naar locaties en mappen moeten aanpassen naar uw locatie binnen uw project!

De meeste scripts lezen data vanaf vanaf de SQL omgeving in. Hiervoor is per product een aparte map aangemaakt op de server, in deze map wordt door het script het csv bestand aangemaakt.
Iedere map heeft ook een scheme.ini bestand, die ervoor zorgt dat de data juist in ArcGIS wordt ingelezen. Met name text velden worden anders aangemaakt met CHAR(8000).

Ieder script heeft ook een webhook waardoor er naar Power automate een bericht kan worden gestuurd dat een script niet heeft gedraaid wegens geen data of dat een script succesvol is afgerond.
In PowerAutomate hebben wij per product 2 werkstromen aangemaakt:
1: Stuur email indien geen data
2: Stuur bericht naar Teams kanaal omdat data is bijgewerkt.

De scripts zijn gescheduled via de task scheduler op de server via een service account.

De machine staat altijd uit.
Vlak voordat de scripts zijn gepland in de taskscheduler wordt de machine via een taak in Azure aangezet.
Enige tijd nadat de scripts normaal gesproken zijn afgerond, wordt de machine via een andere taak uitgezet en 'gedetached'.

Let op:
- De scripts bevatten nog veel harde verwijzingen naar locaties die u moet aanpassen.
- Wij hebben geen mogelijkheid gevonden om verbinding te maken met de SQL server dan op de manier in dit script. WIj hebben de namen en ww van onze omgeving vervangen door <aanwijzingen>.
- Deze scripts zijn in combinatie eigen werk, maar wel gedeeltelijk samengesteld uit online gevonden functies en mogelijkheden.
- Deze script werken voor ons, maar u zal veel testen nodig hebben om het werkend te krijgen.
