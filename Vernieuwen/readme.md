Deze map bevat script die wij hebben gemaakt om onze ArcGIS producten automatisch te kunnen vernieuwen.
Hiervoor hebben wij een kleine windows server in Azure laten inrichten.
Op deze machine staat:
- ArcGIS Pro.
- inrichting om de scripts via de taskscheduler te kunnen draaien.

De meeste scripts lezen data vanaf vanaf de SQL omgeving in. Hiervoor is per product een aparte map aangemaakt op de server, in deze map wordt door het script het csv bestand aangemaakt.
Iedere map heeft ook een scheme.ini bestand, die ervoor zorgt dat de data juist in ArcGIS wordt ingelezen. Met name text velden worden anders aangemaakt met CHAR(8000).

Ieder script heeft ook een webhook waardoor er naar Power automate een bericht kan worden gestuurd dat een script niet heeft gedraaid wegens geen data of dat een script succesvol is afgerond.
In PowerAutomate hebben wij per product 2 werkstromen aangemaakt:
1: Stuur email indien geen data
2: Stuur bericht naar Teams kanaal omdat data is bijgewerkt.

De scripts zijn gescheduled via de task scheduler op de server via een service account.
