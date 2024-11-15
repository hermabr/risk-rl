from __future__ import annotations

# keep owner reference? might simplify things when choosing
# defining state space for RL later
class Country:
    def __init__(self, name, continent:str):
        self.name = name
        self.continent = continent
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


    def __repr__(self):
        return self.name

Alaska             = Country('Alaska', 'North America')
Alberta            = Country('Alberta', 'North America')
CentralAmerica     = Country('Central America', 'North America')
EasternUS          = Country('Eastern US', 'North America')
Greenland          = Country('Greenland', 'North America')
NorthwestTerritory = Country('Northwest Territory', 'North America')
Ontario            = Country('Ontario', 'North America')
Quebec             = Country('Quebec', 'North America')
WesternUS          = Country('Western US', 'North America')
Venezuela          = Country('Venezuela', 'South America')
Brazil             = Country('Brazil', 'South America')
Peru               = Country('Peru', 'South America')
Argentina          = Country('Argentina', 'South America')
Iceland            = Country('Iceland', 'Europe')
GreatBritain       = Country('Great Britain', 'Europe')
NorthernEurope     = Country('Northern Europe', 'Europe')
Scandinavia        = Country('Scandinavia', 'Europe')
Ukraine            = Country('Ukraine', 'Europe')
SouthernEurope     = Country('Southern Europe', 'Europe')
WesternEurope      = Country('Western Europe', 'Europe')
NorthAfrica        = Country('North Africa', 'Africa')
Egypt              = Country('Egypt', 'Africa')
EastAfrica         = Country('East Africa', 'Africa')
Congo              = Country('Congo', 'Africa')
SouthAfrica        = Country('South Africa', 'Africa')
Madagascar         = Country('Madagascar', 'Africa')
Afghanistan        = Country('Afghanistan', 'Asia')
China              = Country('China', 'Asia')
India              = Country('India', 'Asia')
Irkutsk            = Country('Irkutsk', 'Asia')
Japan              = Country('Japan', 'Asia')
Kamchatka          = Country('Kamchatka', 'Asia')
MiddleEast         = Country('Middle East', 'Asia')
Mongolia           = Country('Mongolia', 'Asia')
Siam               = Country('Siam', 'Asia')
Siberia            = Country('Siberia', 'Asia')
Ural               = Country('Ural', 'Asia')
Yakutsk            = Country('Yakutsk', 'Asia')
Indonesia          = Country('Indonesia', 'Australia')
NewGuinea          = Country('New Guinea', 'Australia')
WesternAustralia   = Country('Western Australia', 'Australia')
EasternAustralia   = Country('Eastern Australia', 'Australia')

COUNTRIES = [Alaska, Alberta, CentralAmerica, EasternUS, Greenland, NorthwestTerritory, Ontario, Quebec, WesternUS, Venezuela, Brazil, Peru, Argentina, Iceland, GreatBritain, NorthernEurope, Scandinavia, Ukraine, SouthernEurope, WesternEurope, NorthAfrica, Egypt, EastAfrica, Congo, SouthAfrica, Madagascar, Afghanistan, China, India, Irkutsk, Japan, Kamchatka, MiddleEast, Mongolia, Siam, Siberia, Ural, Yakutsk, Indonesia, NewGuinea, WesternAustralia, EasternAustralia]
