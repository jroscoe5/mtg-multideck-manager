import csv
import io
import re
from typing import Dict, List, Tuple, Any, Optional
from django.db import transaction
from django.db.models import QuerySet
from django.http import HttpResponse

from collection.models import Collection, Card, CollectionCard


class ImportExport:
    """Service class for handling collection operations like import and export."""
    
    @staticmethod
    def parse_text_input(text: str) -> List[Dict[str, Any]]:
        """
        Parse text input with cards in format: quantity card_name.
        
        Args:
            text (str): Text containing card data
            
        Returns:
            List[Dict]: List of cards with name and quantity
        """
        cards_to_import = []
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Try to match the line with different formats
            # Format 1: "2 Lightning Bolt"
            quantity_name_match = re.match(r'^(\d+)\s+(.+)$', line)
            # Format 2: "Lightning Bolt (2)"
            name_quantity_match = re.match(r'^(.+)\s+\((\d+)\)$', line)
            # Format 3: "Lightning Bolt"
            name_only_match = re.match(r'^([^0-9]+)$', line)
            
            if quantity_name_match:
                quantity = int(quantity_name_match.group(1))
                name = quantity_name_match.group(2).strip()
                cards_to_import.append({'name': name, 'quantity': quantity})
            elif name_quantity_match:
                name = name_quantity_match.group(1).strip()
                quantity = int(name_quantity_match.group(2))
                cards_to_import.append({'name': name, 'quantity': quantity})
            elif name_only_match:
                name = name_only_match.group(1).strip()
                cards_to_import.append({'name': name, 'quantity': 1})
        
        return cards_to_import
    
    @staticmethod
    def parse_csv_file(file) -> List[Dict[str, Any]]:
        """
        Parse CSV file with cards.
        
        Args:
            file: File object containing CSV data
            
        Returns:
            List[Dict]: List of cards with name and quantity
        """
        cards_to_import = []
        decoded_file = file.read().decode('utf-8')
        csv_reader = csv.reader(io.StringIO(decoded_file))
        
        for row in csv_reader:
            if not row:
                continue
            
            # Check if the row has at least 2 columns (quantity, name)
            if len(row) >= 2:
                try:
                    quantity = int(row[0].strip())
                    name = row[1].strip()
                    cards_to_import.append({'name': name, 'quantity': quantity})
                except (ValueError, IndexError):
                    # If first column is not a number, assume it's the name with quantity 1
                    cards_to_import.append({'name': row[0].strip(), 'quantity': 1})
            else:
                # If there's only one column, assume it's the name with quantity 1
                cards_to_import.append({'name': row[0].strip(), 'quantity': 1})
        
        return cards_to_import
    
    @staticmethod
    @transaction.atomic
    def process_card_import(collection: Collection, cards_to_import: List[Dict[str, Any]], 
                           skip_unknown: bool = False) -> Dict[str, Any]:
        """
        Process cards to import and add them to the collection.
        
        Args:
            collection: Collection model instance
            cards_to_import: List of cards with name and quantity
            skip_unknown: Whether to skip unknown cards or report them as warnings
            
        Returns:
            Dict: Result containing success status, added cards, skipped cards, and warnings
        """
        added_cards = []
        skipped_cards = []
        warnings = []
        
        for card_data in cards_to_import:
            name = card_data['name']
            quantity = card_data['quantity']
            
            # Skip empty names
            if not name:
                continue
            
            # Try to find the card in the database
            cards = Card.objects.filter(name__iexact=name)
            
            if not cards.exists():
                # If card not found, add to skipped list
                skipped_cards.append({
                    'name': name,
                    'quantity': quantity,
                    'reason': 'Card not found in database'
                })
                
                if not skip_unknown:
                    warnings.append(f"Card not found: {name}")
                
                continue
            
            # Get latest printing of the card
            card = cards.order_by('-set_code').first()
            
            # Check if card is already in collection
            collection_card, created = CollectionCard.objects.get_or_create(
                collection=collection,
                card=card,
                defaults={'quantity': 0}
            )
            
            # Update quantity (skip if the card is marked as infinite)
            if collection_card.quantity != -1:
                collection_card.quantity += quantity
                collection_card.save()
            
            added_cards.append({
                'name': card.name,
                'quantity': quantity,
                'set_code': card.set_code,
                'collector_number': card.collector_number
            })
        
        return {
            'success': True,
            'added_count': len(added_cards),
            'skipped_count': len(skipped_cards),
            'added_cards': added_cards,
            'skipped_cards': skipped_cards,
            'warnings': warnings
        }
    
    @staticmethod
    def export_collection_to_csv(collection: Collection) -> HttpResponse:
        """
        Export collection cards to a CSV file.
        
        Args:
            collection: Collection model instance
            
        Returns:
            HttpResponse: CSV response with collection data
        """
        # Get all cards in the collection
        collection_cards = CollectionCard.objects.filter(
            collection=collection
        ).select_related('card')
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{collection.name}_cards.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Quantity', 'Card Name', 'Set', 'Collector Number', 'Type'])
        
        for cc in collection_cards:
            quantity = "Infinite" if cc.quantity == -1 else cc.quantity
            writer.writerow([
                quantity,
                cc.card.name,
                cc.card.set_code.upper(),
                cc.card.collector_number,
                cc.card.type_line or ''
            ])
        
        return response