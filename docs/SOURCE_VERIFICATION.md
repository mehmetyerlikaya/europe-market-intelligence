# Source verification

Checked live on 2026-09-21. Availability describes that check, not a promise that
the public APIs will never revise their data. `config/project.yml` contains the
verified labels; `config/sources.yml` records the actual selected units and years.

## Geography and availability

| Market | NUTS 3 | Eurostat English label | 2024 population/age | 2024 density | 2024 GDP | 2023 GDP |
|---|---|---|---|---|---|---|
| Berlin | DE300 | Berlin | Complete | 4342.6 | Missing | 48700 |
| Hamburg | DE600 | Hamburg | Complete | 2615.6 | Missing | 75000 |
| Munich | DE212 | München, Kreisfreie Stadt | Complete | 4828.6 | Missing | 89900 |
| Vienna | AT130 | Wien | Complete | 5093.5 | Missing | 53400 |
| Prague | CZ010 | Hlavní město Praha | Complete | 2868.7 | 76600 | 75700 |
| Amsterdam | NL32B | Groot-Amsterdam | Complete | 1985.0 | 101600 | 96500 |
| Brussels | BE100 | Arr. de Bruxelles-Capitale/Arr. Brussel-Hoofdstad | Complete | 7827.4 | 76000 | 73100 |
| Paris | FR101 | Paris | Complete | 20147.8 | 123100 | 115300 |

Density units: persons/km². GDP units: `PPS_EU27_2020_HAB` (purchasing power
standard, EU27 from 2020, per inhabitant). This is not the percentage-of-EU-average
unit `PPS_HAB_EU27_2020`. Population completeness covers all four required age
categories: `TOTAL`, `Y_LT15`, `Y15-64`, `Y_GE65`, with `sex=T` and `unit=NR`.

The attempted common 2023 slice had all population and GDP observations but lacked
Amsterdam density for `NL32B`. Checking its full density series returned only 2024.
The older `NL329` returned an empty GDP value object. These checks motivated the
explicit mixed-year configuration; no geography or year is substituted at runtime.

## Reproduce the important checks

The following are official API URLs (JSON-stat responses):

- [Berlin GDP, all units, 2024](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10r_3gdp?lang=EN&time=2024&geo=DE300)
- [2024 GDP in PPS per inhabitant](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10r_3gdp?lang=EN&time=2024&unit=PPS_EU27_2020_HAB)
- [2023 GDP in PPS per inhabitant](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10r_3gdp?lang=EN&time=2023&unit=PPS_EU27_2020_HAB)
- [Amsterdam current-code density history](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_r_d3dens?lang=EN&geo=NL32B&unit=PER_KM2)
- [Amsterdam old-code GDP history](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/nama_10r_3gdp?lang=EN&geo=NL329&unit=PPS_EU27_2020_HAB)
- [2024 population totals and geographic labels](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/demo_r_pjanaggr3?lang=EN&time=2024&sex=T&unit=NR&age=TOTAL)

The runtime requests are restricted to the eight configured regions, and their
full URLs are stored in each raw table. The checked-in Eurostat fixtures retain
the actual selected observations, dimensions, labels, update times and status flags.

## Holidays

Successfully fetched 2026 calendars for AT, BE, CZ, DE, FR and NL from
`https://nagerholidays.com/api/v4/Holidays/{CountryCode}/2026`.
The response fields include `date`, `name`, `countryCode`, `nationalHoliday`,
`subdivisionCodes`, and `holidayTypes`.

[Germany response](https://nagerholidays.com/api/v4/Holidays/DE/2026) includes
regional-only holidays, verifying that the national filter is necessary.
[Austria response](https://nagerholidays.com/api/v4/Holidays/AT/2026) was also
inspected before implementation. All six country responses are saved as fixtures.
