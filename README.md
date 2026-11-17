# PC LED Beheer

E�n venster om alle RGB-verlichting van je pc te besturen: moederbord, RAM,
CPU-koeler, videokaart, ledstrips en meer. Gebouwd op
[OpenRGB](https://openrgb.org) (via de SDK Server), dus het werkt met
honderden apparaten van veel verschillende merken.

## Functies
- Alle apparaten in een lijst, één of meerdere tegelijk selecteren
- Kleurkiezer en helderheid
- Hardware-modi van het apparaat (Static, Breathing, enz.)
- Software-effecten: regenboog, ademen, kleurwissel
- Profielen opslaan en laden (JSON)

## Gebruiken (exe)
1. Download `PC-LED-Beheer.exe` bij **Releases**.
2. Installeer en start [OpenRGB](https://openrgb.org) -> tabblad **SDK Server** -> **Start Server**.
3. Sluit andere RGB-software (iCUE, Armoury Crate, MSI Center, ...).
4. Start `PC-LED-Beheer.exe` en klik op *Verbinden / Vernieuwen*.

> Windows SmartScreen kan waarschuwen omdat de exe niet digitaal is ondertekend.
> Kies *Meer info* -> *Toch uitvoeren*. De broncode staat hier, en de exe wordt
> door GitHub Actions gebouwd uit deze code.

## Draaien vanaf de broncode
```bash
pip install -r requirements.txt
python pc_led_beheer.py
```

## Zelf een exe bouwen
Lokaal (Windows): dubbelklik `build.bat`. Het resultaat staat in `dist\PC-LED-Beheer.exe`.

Via GitHub:
- Elke push naar `main` bouwt de exe. Je vindt hem onder **Actions** -> run -> **Artifacts**.
- Een release met exe maak je zo:
  ```bash
  git tag v1.0.0
  git push origin v1.0.0
  ```
  De workflow bouwt dan automatisch de exe en zet hem bij **Releases**.

## Problemen
- *Kan niet verbinden*: staat de SDK Server in OpenRGB aan (poort 6742)?
- Apparaat ontbreekt: start OpenRGB als administrator, of het apparaat wordt (nog) niet ondersteund.
- Leds reageren niet: sluit de RGB-software van de fabrikant.

## Licentie
MIT, zie `LICENSE`. Vergeet je naam niet in te vullen.
