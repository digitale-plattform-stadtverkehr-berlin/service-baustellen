# Baustellen-Service

Service um Verkehrsmeldungen aus Concert über die OCIT-C Schnittstelle auszulesen und als GeoJSON in der Azure-Cloud abzulegen.

Die Abfrage der Daten und schreiben der GeoJSON Datei erfolgt einmal pro Stunde. 

## Parameter

Einige Zugangsdaten müssen über Systemvariablen konfiguriert werden.
Wenn der Service als Docker-Container läuft können diese als Umgebungsvariablen in Docker gesetzt werden. 

* **OCIT_USER** / **OCIT_PASSWORD** - Zugangsdaten der OCIT-C Schnittstelle
* **AZURE_CONN_STR** - Verbindungsdaten des Azure-Speicherkonto
* **AZURE_CONTAINER_NAME** - Name des Zielcontainers (Blob-Container) im Azure-Speicherkonto
* **AZURE_BLOB_NAME** - Pfad und Name der Zieldatei innerhalb des Blob-Containers

Der Zugriff auf die OCIT-C Schnittstelle erfolgt über die nicht öffentliche Domain `vizconcs2.concert.viz`. 
Diese ist über die Hosts-Datei auf die IP abzubilden. 

## Anpassen

Wenn der Service in einer anderen Umgebung genutzt werden soll, sind einige Angaben gegebenenfalls im Code anzupassen.

* Domain der OCIT-C Schnittstelle - Aktuell `vizconcs2.concert.viz`
* Koordinatensystem in Concert - Aktuell `EPSG:25833`
* Der objectType für die OCIT-C Abfrage - Aktuell `TrafficMessage_RoadWorks` und `TrafficMessage_Incidents`

## Docker Image bauen und in GitHub Registry pushen

```bash
> docker build -t docker.pkg.github.com/digitale-plattform-stadtverkehr-berlin/service-baustellen/service-baustellen:<TAG> .
> docker push docker.pkg.github.com/digitale-plattform-stadtverkehr-berlin/service-baustellen/service-baustellen:<TAG>
```
