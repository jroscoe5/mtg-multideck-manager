from django.contrib import admin
from django.db.models import Count, Sum, Q
from .models import Card, Collection, CollectionCard, Decklist, DecklistCard


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ('name', 'set_code', 'collector_number', 'mana_cost', 'cmc', 'type_line', 'rarity')
    list_filter = ('set_code', 'rarity')
    search_fields = ('name', 'oracle_text', 'type_line')
    readonly_fields = ('set_code', 'collector_number')
    
    def get_queryset(self, request):
        # Optimize query with prefetch/select related if needed
        return super().get_queryset(request)


class CollectionCardInline(admin.TabularInline):
    model = CollectionCard
    extra = 1
    autocomplete_fields = ['card']


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ('name', 'card_count', 'decklist_count', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    inlines = [CollectionCardInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            card_count=Sum('collectioncard__quantity'),
            decklist_count=Count('decklists')
        )
    
    def card_count(self, obj):
        # Handle None for collections with no cards
        return obj.card_count if obj.card_count else 0
    card_count.admin_order_field = 'card_count'
    card_count.short_description = 'Total Cards'
    
    def decklist_count(self, obj):
        return obj.decklist_count
    decklist_count.admin_order_field = 'decklist_count'
    decklist_count.short_description = 'Decklists'


class DecklistCardInline(admin.TabularInline):
    model = DecklistCard
    extra = 1
    autocomplete_fields = ['card']
    fields = ('card', 'quantity', 'is_sideboard')


@admin.register(Decklist)
class DecklistAdmin(admin.ModelAdmin):
    list_display = ('name', 'collection', 'mainboard_count', 'sideboard_count', 'created_at', 'updated_at')
    list_filter = ('collection',)
    search_fields = ('name', 'description')
    inlines = [DecklistCardInline]
    
    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            mainboard_count=Sum('decklistcard__quantity', 
                               filter=Q(decklistcard__is_sideboard=False)),
            sideboard_count=Sum('decklistcard__quantity', 
                               filter=Q(decklistcard__is_sideboard=True))
        )
    
    def mainboard_count(self, obj):
        return obj.mainboard_count if obj.mainboard_count else 0
    mainboard_count.admin_order_field = 'mainboard_count'
    mainboard_count.short_description = 'Main (Cards)'
    
    def sideboard_count(self, obj):
        return obj.sideboard_count if obj.sideboard_count else 0
    sideboard_count.admin_order_field = 'sideboard_count'
    sideboard_count.short_description = 'Side (Cards)'


@admin.register(CollectionCard)
class CollectionCardAdmin(admin.ModelAdmin):
    list_display = ('card', 'collection', 'quantity')
    list_filter = ('collection',)
    search_fields = ('card__name',)
    autocomplete_fields = ['card']


@admin.register(DecklistCard)
class DecklistCardAdmin(admin.ModelAdmin):
    list_display = ('card', 'decklist', 'quantity', 'is_sideboard')
    list_filter = ('decklist', 'is_sideboard')
    search_fields = ('card__name', 'decklist__name')
    autocomplete_fields = ['card']