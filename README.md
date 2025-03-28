# mtg-multideck-manager
 Local tool for tracking Magic the Gathering collection and decks


### Installation and Setup

Requires a python3 installation. Might also require some form of mysql.
##### From project root directory run:

`python3 -m venv .env`

`source .env/bin/activate`

`pip install -r requirements.txt`

`cd MultideckManager`

`python manage.py migrate`

`python manage.py runserver`

##### Seed card database from Scyfall

`python manage.py seed_cards`

