from __future__ import annotations
from typing import List

class Country:
    def __init__(self, name: str):
        self.name = name
        self.continent: Continent = None
        self._army = None

    @property
    def army(self) -> Army:
        return self._army

    @army.setter
    def army(self, value):
        self._army = value

    def __str__(self):
        soldiers = self.army.n_soldiers if self.army else 0
        return f"{self.name}({soldiers})"

    def __eq__(self, other):
        if isinstance(other, Country):
            return self.name == other.name
        return False

    def __lt__(self, other):
        return self.name < other.name
        
    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return self.name

class Continent:
    def __init__(self, name: str, countries: List[Country], extra_points: int):
        self.name = name
        self.countries = countries
        self.extra_points = extra_points

    def __str__(self):
        return self.name

continent_countries = {
    'NorthAmerica': [
        'Alaska', 'Alberta', 'CentralAmerica', 'EasternUS', 'Greenland',
        'NorthwestTerritory', 'Ontario', 'Quebec', 'WesternUS'
    ],
    'SouthAmerica': ['Venezuela', 'Brazil', 'Peru', 'Argentina'],
    'Europe': [
        'Iceland', 'GreatBritain', 'NorthernEurope', 'Scandinavia',
        'Ukraine', 'SouthernEurope', 'WesternEurope'
    ],
    'Africa': [
        'NorthAfrica', 'Egypt', 'EastAfrica', 'Congo', 'SouthAfrica', 'Madagascar'
    ],
    'Asia': [
        'Afghanistan', 'China', 'India', 'Irkutsk', 'Japan', 'Kamchatka',
        'MiddleEast', 'Mongolia', 'Siam', 'Siberia', 'Ural', 'Yakutsk'
    ],
    'Australia': [
        'Indonesia', 'NewGuinea', 'WesternAustralia', 'EasternAustralia'
    ]
}

continent_extra_points = {
    'NorthAmerica': 5,
    'SouthAmerica': 2,
    'Europe': 5,
    'Africa': 3,
    'Asia': 7,
    'Australia': 2
}

country_instances = {}

for country_name in sum(continent_countries.values(), []):
    country_instances[country_name] = Country(country_name)

continent_instances = []

for continent_name, country_names in continent_countries.items():
    countries = [country_instances[name] for name in country_names]
    continent = Continent(
        name=continent_name,
        countries=countries,
        extra_points=continent_extra_points[continent_name]
    )
    for country in countries:
        country.continent = continent
    continent_instances.append(continent)

for var_name, country in country_instances.items():
    globals()[var_name] = country

COUNTRIES = list(country_instances.values())
CONTINENTS = continent_instances
