import logging
from django.core.management.base import BaseCommand
from collection.services.card_seeder import CardSeeder

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Seeds the database with Magic: The Gathering cards from Scryfall'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            default='oracle_cards',
            choices=['default_cards', 'oracle_cards', 'unique_artwork', 'all_cards'],
            help='Type of bulk data to download'
        )

    def handle(self, *args, **options):
        data_type = options['type']
        
        self.stdout.write(f"Seeding database with {data_type} from Scryfall...")
        
        try:
            seeder = CardSeeder(data_type=data_type)
            success = seeder.run()
            
            if success:
                self.stdout.write(self.style.SUCCESS('Successfully seeded the database with cards!'))
            else:
                self.stdout.write(self.style.ERROR('Card seeding failed.'))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))