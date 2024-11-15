from risk.country import Country

class Player:
    def __init__(self, name):
        self.name = name
        self.countries = []
        self.unassigned_soldiers = 0

    def add_country(self, country: Country):
        self.countries.append(country)

    def remove_country(self, country: Country):
        self.countries.remove(country)

    def __str__(self):
        return self.name

    def print_summary(self):
        for i, country in enumerate(self.countries):
            print(f"{i + 1}: {country} (Current soldiers: {country.army.n_soldiers})")
        