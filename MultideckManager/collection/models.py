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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def can_be_built(self):
        """
        Checks if the deck can be built with the cards in the collection.
        """
        # This will be implemented with the logic for checking card availability
        pass


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