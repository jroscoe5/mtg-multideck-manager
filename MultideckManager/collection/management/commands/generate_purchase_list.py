import csv
from collections import defaultdict
from django.core.management.base import BaseCommand, CommandError
from collection.models import Collection, Decklist, DecklistCard, CollectionCard, Card


class Command(BaseCommand):
    help = 'Generate a purchase list for a collection to have 4 copies of all cards in decklists'

    def add_arguments(self, parser):
        parser.add_argument('collection_id', type=int, help='ID of the collection to analyze')
        parser.add_argument(
            '--output',
            default='purchase_list.csv',
            help='Output file path (default: purchase_list.csv)'
        )
        parser.add_argument(
            '--include-inactive',
            action='store_true',
            help='Include cards from inactive decklists'
        )
        parser.add_argument(
            '--target-count',
            type=int,
            default=4,
            help='Target number of copies to have (default: 4)'
        )

    def handle(self, *args, **options):
        collection_id = options['collection_id']
        output_file = options['output']
        include_inactive = options['include_inactive']
        target_count = options['target_count']
        
        try:
            collection = Collection.objects.get(id=collection_id)
        except Collection.DoesNotExist:
            raise CommandError(f'Collection with ID {collection_id} does not exist')
        
        self.stdout.write(f"Analyzing collection: {collection.name}")
        
        # Get all decklists in the collection
        decklists_query = Decklist.objects.filter(collection=collection)
        if not include_inactive:
            decklists_query = decklists_query.filter(active=True)
        
        decklists = list(decklists_query)
        
        if not decklists:
            self.stdout.write(self.style.WARNING('No decklists found in this collection.'))
            return
        
        self.stdout.write(f"Found {len(decklists)} decklists to analyze.")
        
        # Get all cards needed for decklists
        needed_cards = defaultdict(int)
        
        # Track which decklists need each card
        card_usage = defaultdict(list)
        
        # Find the maximum number of each card needed across all decklists
        for decklist in decklists:
            self.stdout.write(f"Processing decklist: {decklist.name}")
            
            # Get all cards in this decklist
            decklist_cards = DecklistCard.objects.filter(decklist=decklist).select_related('card')
            
            # Track cards in this decklist
            decklist_card_counts = defaultdict(int)
            
            for dc in decklist_cards:
                card_id = dc.card_id
                decklist_card_counts[card_id] += dc.quantity
            
            # Update global needed cards with max quantity needed
            for card_id, quantity in decklist_card_counts.items():
                needed_cards[card_id] = max(needed_cards[card_id], quantity)
                card_usage[card_id].append((decklist.name, quantity))
        
        # Get current inventory from collection
        inventory = {}
        collection_cards = CollectionCard.objects.filter(collection=collection).select_related('card')
        
        for cc in collection_cards:
            inventory[cc.card_id] = cc.quantity
        
        # Calculate purchase requirements
        purchase_list = []
        
        for card_id, max_needed in needed_cards.items():
            current_count = inventory.get(card_id, 0)
            
            # If we have infinite copies (-1) or more than target, skip
            if current_count == -1 or current_count >= target_count:
                continue
            
            # Calculate how many we need to purchase
            # We want at least what's needed for decks, but not more than target_count
            target = min(max_needed, target_count)
            to_purchase = max(0, target - current_count)
            
            if to_purchase > 0:
                try:
                    card = Card.objects.get(id=card_id)
                    
                    # Get usage info
                    usage_info = ', '.join([f"{name} ({qty})" for name, qty in card_usage[card_id]])
                    
                    purchase_list.append({
                        'card_id': card_id,
                        'name': card.name,
                        'set_code': card.set_code,
                        'collector_number': card.collector_number,
                        'type_line': card.type_line,
                        'rarity': card.rarity,
                        'to_purchase': to_purchase,
                        'current_count': current_count,
                        'max_needed': max_needed,
                        'usage': usage_info
                    })
                except Card.DoesNotExist:
                    self.stdout.write(self.style.WARNING(f"Card with ID {card_id} not found in database."))
        
        # Sort the purchase list by card name
        purchase_list.sort(key=lambda x: x['name'])
        
        # Write the purchase list to a CSV file
        with open(output_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Card Name', 
                'Set', 
                'Collector Number', 
                'Type', 
                'Rarity', 
                'Quantity to Purchase', 
                'Current Quantity', 
                'Max Needed',
                'Used In'
            ])
            
            for item in purchase_list:
                writer.writerow([
                    item['name'],
                    item['set_code'].upper(),
                    item['collector_number'],
                    item['type_line'] or '',
                    item['rarity'] or '',
                    item['to_purchase'],
                    item['current_count'],
                    item['max_needed'],
                    item['usage']
                ])
        
        total_to_purchase = sum(item['to_purchase'] for item in purchase_list)
        
        self.stdout.write(self.style.SUCCESS(
            f"Purchase list generated with {len(purchase_list)} unique cards, "
            f"{total_to_purchase} total cards to purchase."
        ))
        self.stdout.write(self.style.SUCCESS(f"Output written to: {output_file}"))