from risk.country import *
class Continent:
    def __init__(self, name, countries, extra_points):
        self.name = name
        self.countries = countries
        self.extra_points = extra_points

    def __str__(self):
        return self.name

NorthAmerica = Continent('North America', [Alaska, Alberta, CentralAmerica, EasternUS, Greenland, NorthwestTerritory, Ontario, Quebec, WesternUS], 5)
SouthAmerica = Continent('South America', [Venezuela, Brazil, Peru, Argentina], 2)
Europe = Continent('Europe', [Iceland, GreatBritain, NorthernEurope, Scandinavia, Ukraine, SouthernEurope, WesternEurope], 5)
Africa = Continent('Africa', [NorthAfrica, Egypt, EastAfrica, Congo, SouthAfrica, Madagascar], 3)
Asia = Continent('Asia', [Afghanistan, China, India, Irkutsk, Japan, Kamchatka, MiddleEast, Mongolia, Siam, Siberia, Ural, Yakutsk], 7)

CONTINENTS = [NorthAmerica, SouthAmerica, Europe, Africa, Asia]
