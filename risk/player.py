class Player:
    def __init__(self, name):
        self.name = name
        self.countries = []
        self.soldiers = 0

    def add_country(self, country):
        self.countries.append(country)

    def remove_country(self, country):
        self.countries.remove(country)

    def __str__(self):
        return self.name
