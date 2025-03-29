import os
import json
import requests
import time
import logging
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.db import transaction
from collection.models import Card

logger = logging.getLogger(__name__)

class CardSeeder:
    """
    Service to download and seed the database with MTG cards from Scryfall.
    """
    BULK_DATA_URL = "https://api.scryfall.com/bulk-data"
    DOWNLOAD_DIR = os.path.join(settings.BASE_DIR, 'downloads')
    HEADERS = {
        'User-Agent': 'MultideckManager/1.0',
        'Accept': 'application/json'
    }
    
    def __init__(self, data_type='default_cards'):
        """
        Initialize the card seeder.
        
        Args:
            data_type (str): Type of bulk data to download. Options:
                - 'default_cards': All cards in English or printed language
                - 'oracle_cards': One card per Oracle ID (unique gameplay entity)
                - 'unique_artwork': One card per unique artwork
                - 'all_cards': All cards in all languages (largest file)
        """
        self.data_type = data_type
        os.makedirs(self.DOWNLOAD_DIR, exist_ok=True)
    
    def _get_bulk_data_info(self):
        """Get information about available bulk data files."""
        response = requests.get(self.BULK_DATA_URL, headers=self.HEADERS)
        response.raise_for_status()
        
        data = response.json()
        for item in data.get('data', []):
            if item.get('type') == self.data_type:
                return item
        
        raise ValueError(f"Bulk data type '{self.data_type}' not found")
    
    def _download_file(self, url, filename):
        """
        Download a file with progress tracking.
        
        Args:
            url (str): URL to download from
            filename (str): Path to save the file
        """
        logger.info(f"Downloading {url} to {filename}")
        
        response = requests.get(url, headers=self.HEADERS, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 * 1024  # 1MB chunks
        downloaded = 0
        
        with open(filename, 'wb') as f:
            start_time = time.time()
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Log progress for large downloads
                    if total_size > 0:
                        percent = downloaded / total_size * 100
                        elapsed = time.time() - start_time
                        if elapsed > 0:
                            speed = downloaded / (1024 * 1024 * elapsed)  # MB/s
                            logger.info(f"Downloaded: {downloaded / (1024 * 1024):.1f}MB / "
                                       f"{total_size / (1024 * 1024):.1f}MB "
                                       f"({percent:.1f}%) at {speed:.1f}MB/s")
        
        logger.info(f"Download complete: {filename}")
    
    def download_bulk_data(self):
        """Download the bulk data file from Scryfall."""
        info = self._get_bulk_data_info()
        download_uri = info.get('download_uri')
        updated_at = info.get('updated_at')
        
        timestamp = datetime.fromisoformat(updated_at.replace('Z', '+00:00')).strftime('%Y%m%d%H%M%S')
        filename = f"{self.data_type}_{timestamp}.json"
        filepath = os.path.join(self.DOWNLOAD_DIR, filename)
        
        if os.path.exists(filepath):
            logger.info(f"File already exists: {filepath}")
            return filepath
        
        self._download_file(download_uri, filepath)
        return filepath
    
    def process_cards(self, filepath, batch_size=1000):
        """
        Process cards from the downloaded file and insert them into the database.
        
        Args:
            filepath (str): Path to the downloaded JSON file
            batch_size (int): Number of cards to process in each batch
        """
        logger.info(f"Processing cards from {filepath}")
        
        total_cards = 0
        imported_cards = 0
        skipped_cards = 0
        
        with open(filepath, 'r', encoding='utf-8') as f:
            cards_data = json.load(f)
        
        total_cards = len(cards_data)
        logger.info(f"Found {total_cards} cards in file")
        
        # Process in batches to avoid memory issues
        for i in range(0, total_cards, batch_size):
            batch = cards_data[i:i+batch_size]
            imported, skipped = self._process_batch(batch)
            imported_cards += imported
            skipped_cards += skipped
            
            logger.info(f"Processed {i + len(batch)}/{total_cards} cards. "
                       f"Imported: {imported_cards}, Skipped: {skipped_cards}")
        
        logger.info(f"Import complete. Total cards: {total_cards}, "
                   f"Imported: {imported_cards}, Skipped: {skipped_cards}")
    
    @transaction.atomic
    def _process_batch(self, batch):
        """Process a batch of cards and add them to the database."""
        imported = 0
        skipped = 0
        
        for card_data in batch:
            try:
                # Skip cards without collector numbers or set codes
                if not card_data.get('collector_number') or not card_data.get('set'):
                    skipped += 1
                    continue
                
                # Skip non-card objects like tokens, emblems, etc.
                if card_data.get('object') != 'card':
                    skipped += 1
                    continue
                
                # Create or update card
                card, created = Card.objects.update_or_create(
                    set_code=card_data.get('set'),
                    collector_number=card_data.get('collector_number'),
                    defaults={
                        'name': card_data.get('name', ''),
                        'mana_cost': card_data.get('mana_cost', ''),
                        'cmc': float(card_data.get('cmc', 0)),
                        'type_line': card_data.get('type_line', ''),
                        'oracle_text': card_data.get('oracle_text', ''),
                        'power': card_data.get('power', ''),
                        'toughness': card_data.get('toughness', ''),
                        'loyalty': card_data.get('loyalty', ''),
                        'rarity': card_data.get('rarity', ''),
                        'scryfall_uri': card_data.get('scryfall_uri', ''),
                    }
                )
                
                if created:
                    imported += 1
                else:
                    skipped += 1
            
            except Exception as e:
                logger.error(f"Error processing card: {card_data.get('name', 'Unknown')} - {e}")
                skipped += 1
        
        return imported, skipped
    
    def run(self):
        """Download and process cards."""
        try:
            filepath = self.download_bulk_data()
            self.process_cards(filepath)
            return True
        except Exception as e:
            logger.error(f"Error in card seeder: {e}")
            return False


def seed_cards(data_type='default_cards'):
    """
    Convenience function to seed the database with cards.
    
    Args:
        data_type (str): Type of bulk data to download
    """
    seeder = CardSeeder(data_type=data_type)
    return seeder.run()