"""Słownik imion dla anonimizatora: najczęstsze imiona w Polsce, ich zdrobnienia i imiona ukraińskie.

Spisany z ogólnej wiedzy, bez wglądu w dane użytkowników. Imię spoza słownika anonimizator może wykryć
tylko z kontekstu („Dla …”, „Od …”, numer rachunku przed nazwą, adres po niej).
Porównanie odbywa się na tekście bez polskich znaków i wielkości liter (`fold`).
"""

FEMALE = """
Ada Adela Adrianna Agata Agnieszka Aleksandra Alicja Alina Amelia Anastazja Aneta Angelika Anita Anna
Antonina Apolonia Barbara Beata Bogumiła Bogusława Bożena Bronisława Celina Czesława Dagmara Danuta Daria
Dominika Dorota Edyta Eliza Elżbieta Emilia Ewa Ewelina Felicja Gabriela Genowefa Grażyna Halina Hanna
Helena Henryka Honorata Ilona Irena Iwona Izabela Jadwiga Janina Joanna Jolanta Józefa Julia Julianna Justyna
Kamila Karina Karolina Katarzyna Kinga Klara Klaudia Kornelia Krystyna Laura Lena Leokadia Liliana Lucyna
Ludmiła Łucja Magdalena Maja Malwina Małgorzata Marcelina Maria Marianna Marlena Marta Martyna Marzena
Michalina Milena Mirosława Monika Nadia Natalia Nikola Nina Oliwia Olga Paula Paulina Patrycja Regina Renata
Roksana Róża Sabina Sandra Stanisława Stefania Sylwia Szymona Tamara Teresa Urszula Wanda Weronika Wiesława
Wiktoria Wioletta Zdzisława Zofia Zuzanna Żaneta
"""

MALE = """
Adam Adrian Albert Aleksander Andrzej Antoni Arkadiusz Artur Bartłomiej Bartosz Bernard Błażej Bogdan
Bogumił Bogusław Bolesław Bronisław Cezary Czesław Damian Daniel Dariusz Dawid Dominik Edward Emil Eugeniusz
Fabian Filip Franciszek Fryderyk Gabriel Grzegorz Gustaw Henryk Hubert Ignacy Igor Ireneusz Jacek Jakub Jan
Janusz Jarosław Jerzy Józef Julian Juliusz Kacper Kamil Karol Kazimierz Konrad Krystian Krzysztof Leon Leszek
Lech Ludwik Łukasz Maciej Maksymilian Marcel Marcin Marek Mariusz Mateusz Michał Mieczysław Mikołaj Miłosz
Mirosław Natan Nikodem Norbert Oskar Patryk Paweł Piotr Przemysław Radosław Rafał Remigiusz Robert Roman
Ryszard Sebastian Seweryn Sławomir Stanisław Stefan Szymon Tadeusz Tomasz Tymon Tymoteusz Waldemar Wacław
Wiesław Wiktor Witold Władysław Włodzimierz Wojciech Zbigniew Zdzisław Zenon Zygmunt
"""

DIMINUTIVES = """
Ania Asia Basia Beatka Bożenka Danka Dorotka Ela Ewka Ewunia Gosia Grażynka Hania Iza Jadzia Joasia Jola
Julka Kasia Kasieńka Krysia Lusia Madzia Magda Marysia Martusia Ola Olka Renia Tereska Ula Wiesia Zosia Zuzia
Aga Agusia Natka Monia Kamilka Wika Kuba Bartek Tomek Wojtek Jacuś Janek Jaś Józek Kazik Krzyś Marcinek
Maciek Mietek Mirek Olek Paweł Piotrek Przemek Radek Rysiek Sławek Staś Stasiek Szymek Tadek Witek Władek
Zbyszek Zdzisiek Franek Antek Leszek Darek Grzesiek Heniek Jurek Kamilek Krzysiek Michałek Romek Wiesiek
"""

UKRAINIAN = """
Andrii Bohdan Dmytro Ivan Mykola Mykhailo Oleh Oleksandr Oleksii Petro Serhii Taras Vasyl Volodymyr Yurii
Anastasiia Daria Halyna Iryna Kateryna Khrystyna Liudmyla Mariia Nataliia Oksana Olena Olha Svitlana Tetiana
Valentyna Viktoriia Yuliia
"""

FIRST_NAMES = frozenset(
    name for block in (FEMALE, MALE, DIMINUTIVES, UKRAINIAN) for name in block.split()
)
