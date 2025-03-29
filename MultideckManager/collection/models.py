from django.db import models
from django.core.validators import MinValueValidator


class Card(models.Model):
    """
    Represents a unique Magic: The Gathering card in the collection.
    """
    name = models.CharField(max_length=255)
    set_code = models.CharField(max_length=10)
    collector_number = models.CharField(max_length=10)
    mana_cost = models.CharField(max_length=50, blank=True, null=True)
    cmc = models.FloatField(default=0)
    type_line = models.CharField(max_length=255, blank=True, null=True)
    oracle_text = models.TextField(blank=True, null=True)
    power = models.CharField(max_length=10, blank=True, null=True)
    toughness = models.CharField(max_length=10, blank=True, null=True)
    loyalty = models.CharField(max_length=10, blank=True, null=True)
    rarity = models.CharField(max_length=20, blank=True, null=True)
    scryfall_uri = models.URLField(max_length=255, blank=True, null=True)
    
    class Meta:
        unique_together = ['set_code', 'collector_number']
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.set_code} #{self.collector_number})"


class Collection(models.Model):
    """
    Represents a collection of Magic: The Gathering cards and decklists.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    cards = models.ManyToManyField(Card, through='CollectionCard')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name


class CollectionCard(models.Model):
    """
    Intermediary model to associate cards with collections and track quantities.
    """
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=0, help_text="Use -1 to represent infinite quantity (e.g., for basic lands)")
    
    class Meta:
        unique_together = ['collection', 'card']
    
    def __str__(self):
        return f"{self.quantity}x {self.card.name} in {self.collection.name}"


class Decklist(models.Model):
    """
    Represents a Magic: The Gathering decklist with cards and their quantities.
    """
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE, related_name='decklists')
    cards = models.ManyToManyField(Card, through='DecklistCard')
    active = models.BooleanField(default=True, help_text="Indicates if this deck is intended to be physically constructed")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def can_be_built(self):
        """
        Checks if the deck can be built with the cards in the collection.
        Returns tuple: (can_be_built, conflict_info)
        
        conflict_info is a dictionary with information about missing cards or conflicts
        """
        if not self.active:
            return (True, None)
            
        collection = self.collection
        # Get all cards in this decklist
        decklist_cards = self.decklistcard_set.all().select_related('card')
        
        # Get the quantities of cards in the collection
        collection_cards = {cc.card_id: cc.quantity for cc in 
                           CollectionCard.objects.filter(collection=collection)}
        
        # Check if all cards in the deck are available in sufficient quantities
        conflicts = []
        
        # Keep track of used cards to detect conflicts with other active decklists
        used_cards = {}
        
        for deck_card in decklist_cards:
            card_id = deck_card.card_id
            needed_quantity = deck_card.quantity
            
            # Track usage of this card
            used_cards[card_id] = needed_quantity
            
            # Check if card exists in collection
            if card_id not in collection_cards:
                conflicts.append({
                    'card': deck_card.card,
                    'needed': needed_quantity,
                    'available': 0,
                    'type': 'missing'
                })
            elif collection_cards[card_id] != -1 and collection_cards[card_id] < needed_quantity:
                # Not enough of this card (-1 means infinite)
                conflicts.append({
                    'card': deck_card.card,
                    'needed': needed_quantity,
                    'available': collection_cards[card_id],
                    'type': 'insufficient'
                })
        
        # Check for conflicts with other active decklists
        other_decklists = Decklist.objects.filter(
            collection=collection, 
            active=True
        ).exclude(id=self.id)
        
        # Calculate card usage across all active decklists
        all_deck_usage = {}
        for deck in other_decklists:
            for deck_card in deck.decklistcard_set.all():
                card_id = deck_card.card_id
                if card_id in all_deck_usage:
                    all_deck_usage[card_id] += deck_card.quantity
                else:
                    all_deck_usage[card_id] = deck_card.quantity
        
        # Check for conflicts based on total card usage
        for card_id, quantity in used_cards.items():
            if card_id in all_deck_usage:
                total_needed = quantity + all_deck_usage[card_id]
                
                # If card in collection and quantity is not infinite
                if card_id in collection_cards and collection_cards[card_id] != -1:
                    if total_needed > collection_cards[card_id]:
                        # Conflict with other decks
                        try:
                            card = Card.objects.get(id=card_id)
                            conflicts.append({
                                'card': card,
                                'needed': total_needed,
                                'available': collection_cards.get(card_id, 0),
                                'current_deck_needs': quantity,
                                'other_decks_need': all_deck_usage[card_id],
                                'type': 'conflict'
                            })
                        except Card.DoesNotExist:
                            pass
        
        can_be_built = len(conflicts) == 0
        
        return (can_be_built, conflicts if conflicts else None)
    
    def get_status(self):
        """
        Returns the deck's status based on conflicts and active state.
        Returns a tuple of (status_code, message, details)
        
        Status codes:
        - inactive: Deck is not active
        - ok: Deck is active and has no conflicts
        - conflict: Deck is active but has conflicts with other active decks
        - error: Deck cannot be built with the available cards
        """
        if not self.active:
            return ('inactive', 'Inactive', None)
            
        can_be_built, conflicts = self.can_be_built()
        
        if can_be_built:
            return ('ok', 'Active', None)
            
        if not conflicts:
            return ('ok', 'Active', None)
            
        # Check if any conflicts are of type 'missing' or 'insufficient'
        error_conflicts = [c for c in conflicts if c['type'] in ('missing', 'insufficient')]
        conflict_conflicts = [c for c in conflicts if c['type'] == 'conflict']
        
        if error_conflicts:
            return ('error', 'Error', error_conflicts)
        elif conflict_conflicts:
            return ('conflict', 'Conflict', conflict_conflicts)
        else:
            return ('ok', 'Active', None)


class DecklistCard(models.Model):
    """
    Intermediary model to associate cards with decklists and track quantities.
    """
    decklist = models.ForeignKey(Decklist, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.PROTECT)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)], help_text="Minimum quantity is 1")
    is_sideboard = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['decklist', 'card', 'is_sideboard']
    
    def __str__(self):
        location = "Sideboard" if self.is_sideboard else "Mainboard"
        return f"{self.quantity}x {self.card.name} in {self.decklist.name} ({location})"