# services/decklist_importer.py
import csv
import io
import re
import requests
from typing import Dict, List, Tuple, Any, Optional
from django.db import transaction

from collection.models import Decklist, Card, DecklistCard


class DecklistImporter:
    """Service class for importing cards into a decklist."""
    
    @staticmethod
    def parse_text_input(text: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse text input with cards, separating mainboard and sideboard.
        
        Args:
            text (str): Text containing card data
            
        Returns:
            Dict: Dictionary with 'mainboard' and 'sideboard' lists of cards
        """
        mainboard = []
        sideboard = []
        
        current_section = 'mainboard'
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check for section headers
            # temporarily remove special characters
            cleaned = re.sub(r'[^\w\s]', '', line)
            if cleaned.upper() == 'MAINBOARD' or cleaned.upper() == 'MAIN':
                current_section = 'mainboard'
                continue
            elif cleaned.upper() == 'SIDEBOARD' or cleaned.upper() == 'SIDE':
                current_section = 'sideboard'
                continue
            
            # Try to match the line with different formats
            # Format 1: "2 Lightning Bolt"
            quantity_name_match = re.match(r'^(\d+)\s+(.+)$', line)
            # Format 2: "Lightning Bolt (2)"
            name_quantity_match = re.match(r'^(.+)\s+\((\d+)\)$', line)
            # Format 3: "Lightning Bolt"
            name_only_match = re.match(r'^([^0-9]+)$', line)
            # Format 4: "4 Candy Trail (WOE) 243"
            quantity_name_set_number_match = re.match(r'^(\d+)\s+(.+)\s+\(([A-Z0-9]+)\)\s+([A-Za-z0-9\-]+)$', line)
            
            card_data = None
            if quantity_name_set_number_match:
                quantity = int(quantity_name_set_number_match.group(1))
                name = quantity_name_set_number_match.group(2).strip()
                set_code = quantity_name_set_number_match.group(3)
                collector_number = quantity_name_set_number_match.group(4)
                card_data = {'name': name, 'quantity': quantity}
            elif quantity_name_match:
                quantity = int(quantity_name_match.group(1))
                name = quantity_name_match.group(2).strip()
                card_data = {'name': name, 'quantity': quantity}
            elif name_quantity_match:
                name = name_quantity_match.group(1).strip()
                quantity = int(name_quantity_match.group(2))
                card_data = {'name': name, 'quantity': quantity}
            elif name_only_match:
                name = name_only_match.group(1).strip()
                card_data = {'name': name, 'quantity': 1}
            
            if card_data:
                if current_section == 'mainboard':
                    # check if card is already in mainboard
                    existing_card = next((card for card in mainboard if card['name'].lower() == card_data['name'].lower()), None)
                    if existing_card:
                        existing_card['quantity'] += card_data['quantity']
                    else:
                        mainboard.append(card_data)
                else:
                    # check if card is already in sideboard
                    existing_card = next((card for card in sideboard if card['name'].lower() == card_data['name'].lower()), None)
                    if existing_card:
                        existing_card['quantity'] += card_data['quantity']
                    else:
                        sideboard.append(card_data)
        
        return {'mainboard': mainboard, 'sideboard': sideboard}
    
    @staticmethod
    def parse_csv_file(file) -> Dict[str, List[Dict[str, Any]]]:
        """
        Parse CSV file with cards, looking for mainboard and sideboard sections.
        
        Args:
            file: File object containing CSV data
            
        Returns:
            Dict: Dictionary with 'mainboard' and 'sideboard' lists of cards
        """
        mainboard = []
        sideboard = []
        
        current_section = 'mainboard'
        decoded_file = file.read().decode('utf-8')
        csv_reader = csv.reader(io.StringIO(decoded_file))
        
        for row in csv_reader:
            if not row:
                continue
            
            # Check for section headers
            first_cell = row[0].strip().upper() if row else ""
            if first_cell == 'MAINBOARD' or first_cell == 'MAIN':
                current_section = 'mainboard'
                continue
            elif first_cell == 'SIDEBOARD' or first_cell == 'SIDE':
                current_section = 'sideboard'
                continue
            
            # Check if the row has at least 2 columns (quantity, name)
            if len(row) >= 2:
                try:
                    quantity = int(row[0].strip())
                    name = row[1].strip()
                    
                    card_data = {'name': name, 'quantity': quantity}
                    
                    if current_section == 'mainboard':
                        mainboard.append(card_data)
                    else:
                        sideboard.append(card_data)
                except (ValueError, IndexError):
                    # If first column is not a number, assume it's the name with quantity 1
                    name = row[0].strip()
                    card_data = {'name': name, 'quantity': 1}
                    
                    if current_section == 'mainboard':
                        mainboard.append(card_data)
                    else:
                        sideboard.append(card_data)
            else:
                # If there's only one column, assume it's the name with quantity 1
                name = row[0].strip()
                card_data = {'name': name, 'quantity': 1}
                
                if current_section == 'mainboard':
                    mainboard.append(card_data)
                else:
                    sideboard.append(card_data)
        
        return {'mainboard': mainboard, 'sideboard': sideboard}
    
    @staticmethod
    def import_from_archidekt(deck_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Placeholder for importing from Archidekt's API.
        
        Args:
            deck_id: The Archidekt deck ID
            
        Returns:
            Dict: Dictionary with 'mainboard' and 'sideboard' lists of cards
        """
        # This is a placeholder implementation
        # In a real implementation, we would use Archidekt's API
        
        try:
            # For now, just return an empty deck structure
            result = {
                'mainboard': [],
                'sideboard': [],
                'deck_name': f"Archidekt Deck #{deck_id}",
                'deck_description': "Imported from Archidekt"
            }
            
            # In a real implementation, we would:
            # 1. Make API call to Archidekt
            # 2. Parse the response
            # 3. Extract mainboard and sideboard cards
            
            # Example API endpoint (not guaranteed to work)
            # response = requests.get(f"https://archidekt.com/api/decks/{deck_id}/")
            
            # For now, just return the placeholder
            return result
            
        except Exception as e:
            raise Exception(f"Error importing from Archidekt: {str(e)}")
    
    @staticmethod
    @transaction.atomic
    def import_cards_to_decklist(decklist: Decklist, card_data: Dict[str, List[Dict[str, Any]]], 
                                clear_existing: bool = False) -> Dict[str, Any]:
        """
        Import cards into a decklist.
        
        Args:
            decklist: Decklist model instance
            card_data: Dictionary with 'mainboard' and 'sideboard' lists of cards
            clear_existing: Whether to clear existing cards before import
            
        Returns:
            Dict: Result of the import operation
        """
        mainboard = card_data.get('mainboard', [])
        sideboard = card_data.get('sideboard', [])
        
        added_mainboard = []
        added_sideboard = []
        skipped_cards = []
        warnings = []
        
        # Clear existing cards if requested
        if clear_existing:
            DecklistCard.objects.filter(decklist=decklist).delete()
        
        # Process mainboard
        for card_info in mainboard:
            result = DecklistImporter._process_card(decklist, card_info, False)
            if result['success']:
                added_mainboard.append(result['card_data'])
            else:
                skipped_cards.append({**result['card_data'], 'reason': result['reason']})
                warnings.append(f"Skipped mainboard card: {card_info['name']} - {result['reason']}")
        
        # Process sideboard
        for card_info in sideboard:
            result = DecklistImporter._process_card(decklist, card_info, True)
            if result['success']:
                added_sideboard.append(result['card_data'])
            else:
                skipped_cards.append({**result['card_data'], 'reason': result['reason']})
                warnings.append(f"Skipped sideboard card: {card_info['name']} - {result['reason']}")
        
        return {
            'success': True,
            'added_mainboard_count': len(added_mainboard),
            'added_sideboard_count': len(added_sideboard),
            'skipped_count': len(skipped_cards),
            'added_mainboard': added_mainboard,
            'added_sideboard': added_sideboard,
            'skipped_cards': skipped_cards,
            'warnings': warnings
        }
    
    @staticmethod
    def _process_card(decklist: Decklist, card_info: Dict[str, Any], is_sideboard: bool) -> Dict[str, Any]:
        """
        Process a single card for import into a decklist.
        
        Args:
            decklist: Decklist model instance
            card_info: Dictionary with card name and quantity
            is_sideboard: Whether the card is part of the sideboard
            
        Returns:
            Dict: Result of processing the card
        """
        name = card_info['name']
        quantity = card_info['quantity']
        
        # Skip empty names
        if not name:
            return {
                'success': False,
                'card_data': {'name': name, 'quantity': quantity, 'is_sideboard': is_sideboard},
                'reason': 'Empty card name'
            }
        
        # Try to find the card in the database
        cards = Card.objects.filter(name__iexact=name)
        
        if not cards.exists():
            return {
                'success': False,
                'card_data': {'name': name, 'quantity': quantity, 'is_sideboard': is_sideboard},
                'reason': 'Card not found in database'
            }
        
        # Get latest printing of the card
        card = cards.order_by('-set_code').first()
        
        # Check if card is already in decklist
        decklist_card, created = DecklistCard.objects.get_or_create(
            decklist=decklist,
            card=card,
            is_sideboard=is_sideboard,
            defaults={'quantity': quantity}
        )
        
        # If card exists, update quantity
        if not created:
            decklist_card.quantity = quantity
            decklist_card.save()
        
        return {
            'success': True,
            'card_data': {
                'name': card.name,
                'quantity': quantity,
                'is_sideboard': is_sideboard,
                'set_code': card.set_code,
                'collector_number': card.collector_number
            }
        }