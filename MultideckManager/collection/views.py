from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Sum
from .models import Collection, Decklist, Card, CollectionCard, DecklistCard
from .forms import CollectionForm, CollectionEditForm


class CollectionListView(ListView):
    """View for listing and creating collections."""
    model = Collection
    template_name = 'collection/collection_list.html'
    context_object_name = 'collections'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CollectionForm()
        return context
    
    def post(self, request, *args, **kwargs):
        form = CollectionForm(request.POST)
        if form.is_valid():
            collection = form.save()
            
            # Add the 5 basic lands as infinite cards
            basic_lands = ["Plains", "Island", "Swamp", "Mountain", "Forest"]
            for land_name in basic_lands:
                # Try to find a basic land card in the database - get the most recent printing
                try:
                    land_card = Card.objects.filter(name=land_name, type_line__icontains="Basic Land").order_by('-set_code').first()
                    if land_card:
                        CollectionCard.objects.create(
                            collection=collection,
                            card=land_card,
                            quantity=-1  # -1 represents infinite quantity
                        )
                except Exception as e:
                    # Log the error but continue with the other lands
                    print(f"Error adding basic land {land_name}: {e}")
            
            return redirect('collection_list')
        
        # If form is invalid, re-render the page with the form
        context = self.get_context_data()
        context['form'] = form
        return render(request, self.template_name, context)


class CollectionDetailView(DetailView):
    """View for displaying a single collection's details."""
    model = Collection
    template_name = 'collection/collection_detail.html'
    context_object_name = 'collection'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['edit_form'] = CollectionEditForm(instance=self.object)
        context['active_tab'] = self.request.GET.get('tab', 'cards')  # Default to cards tab
        
        # Get collection cards with quantities
        collection_cards = CollectionCard.objects.filter(collection=self.object)
        context['collection_cards'] = collection_cards
        
        # Get decklists in this collection
        context['decklists'] = Decklist.objects.filter(collection=self.object)
        
        # Calculate collection statistics
        if collection_cards.exists():
            # Total card count (sum of quantities)
            total_cards = collection_cards.exclude(quantity=-1).aggregate(Sum('quantity'))['quantity__sum'] or 0
            
            # Count infinite cards separately
            infinite_cards = collection_cards.filter(quantity=-1).count()
            
            # Get unique cards count
            unique_cards = collection_cards.count()
            
            # Color distribution
            card_colors = {
                'W': 0,  # White
                'U': 0,  # Blue
                'B': 0,  # Black
                'R': 0,  # Red
                'G': 0,  # Green
                'C': 0   # Colorless
            }
            
            import re
            
            for cc in collection_cards:
                # Extract colors from mana_cost using regex
                if cc.card.mana_cost:
                    # Count each instance of a color in the mana cost
                    # Format example: {2}{R}{R}{G}{G}
                    quantity = cc.quantity if cc.quantity != -1 else 1  # Count infinite cards as 1 for distribution
                    
                    # Check for color symbols in mana cost
                    for color in ['W', 'U', 'B', 'R', 'G']:
                        # Count how many of this color symbol appears in the mana cost
                        color_count = cc.card.mana_cost.count('{' + color + '}')
                        if color_count > 0:
                            card_colors[color] += quantity
                    
                    # Check for colorless mana
                    if re.search(r'{\d+}', cc.card.mana_cost):
                        card_colors['C'] += quantity
                    
                    # Check for colorless cards (artifacts, etc.) with only generic mana
                    if not any('{' + color + '}' in cc.card.mana_cost for color in ['W', 'U', 'B', 'R', 'G']):
                        card_colors['C'] += quantity
                else:
                    # Cards with no mana cost are considered colorless
                    quantity = cc.quantity if cc.quantity != -1 else 1
                    card_colors['C'] += quantity
            
            # Convert color codes to readable names
            color_names = {
                'W': 'White',
                'U': 'Blue',
                'B': 'Black',
                'R': 'Red',
                'G': 'Green',
                'C': 'Colorless'
            }
            
            # Filter out colors with 0 count
            color_distribution = {color_names[color]: count for color, count in card_colors.items() if count > 0}
            
            # Card types distribution
            type_counts = {}
            for cc in collection_cards:
                quantity = cc.quantity if cc.quantity != -1 else 1
                
                # Extract primary type from type_line
                if cc.card.type_line:
                    # Get the first major type (e.g., "Creature" from "Creature — Human Wizard")
                    primary_types = [t.strip() for t in cc.card.type_line.split('—')[0].split()]
                    for primary_type in primary_types:
                        # Focus on major card types
                        if primary_type in ['Creature', 'Instant', 'Sorcery', 'Artifact', 'Enchantment', 'Planeswalker', 'Land']:
                            if primary_type in type_counts:
                                type_counts[primary_type] += quantity
                            else:
                                type_counts[primary_type] = quantity
            
            # Card with highest quantity
            highest_quantity_card = None
            highest_quantity = 0
            
            for cc in collection_cards.exclude(quantity=-1):
                if cc.quantity > highest_quantity:
                    highest_quantity = cc.quantity
                    highest_quantity_card = cc.card
            
            # If no card has a quantity higher than 0, or all cards are infinite
            if not highest_quantity_card:
                # Try to find any infinite card
                infinite_card = collection_cards.filter(quantity=-1).first()
                if infinite_card:
                    highest_quantity_card = infinite_card.card
                    highest_quantity = "∞"
            
            # Package all stats
            context['collection_stats'] = {
                'total_cards': total_cards,
                'infinite_cards': infinite_cards,
                'unique_cards': unique_cards,
                'color_distribution': color_distribution,
                'type_counts': type_counts,
                'highest_quantity_card': highest_quantity_card,
                'highest_quantity': highest_quantity
            }
        else:
            # Empty collection
            context['collection_stats'] = {
                'total_cards': 0,
                'infinite_cards': 0,
                'unique_cards': 0,
                'color_distribution': {},
                'type_counts': {},
                'highest_quantity_card': None,
                'highest_quantity': 0
            }
            
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CollectionEditForm(request.POST, instance=self.object)
        
        if form.is_valid():
            form.save()
            return redirect('collection_detail', pk=self.object.pk)
        
        context = self.get_context_data(object=self.object)
        context['edit_form'] = form
        return render(request, self.template_name, context)
class CardSearchView(View):
    """API view for searching cards and getting quantities in a collection."""
    def get(self, request, *args, **kwargs):
        query = request.GET.get('query', '').strip()
        collection_id = kwargs.get('collection_id')
        collection = get_object_or_404(Collection, id=collection_id)
        
        if len(query) < 2:
            return JsonResponse({'results': []})
        
        # Search for cards matching the query
        cards = Card.objects.filter(
            Q(name__icontains=query)
        ).order_by('name')[:20]  # Limit to 20 results
        
        results = []
        for card in cards:
            # Try to get the card's quantity in this collection
            try:
                collection_card = CollectionCard.objects.get(collection=collection, card=card)
                quantity = collection_card.quantity
            except CollectionCard.DoesNotExist:
                quantity = 0
                
            results.append({
                'id': card.id,
                'name': card.name,
                'set_code': card.set_code,
                'mana_cost': card.mana_cost,
                'collector_number': card.collector_number,
                'type_line': card.type_line,
                'rarity': card.rarity,
                'quantity': quantity,
                'scryfall_uri': card.scryfall_uri,
            })
        
        return JsonResponse({'results': results})


class UpdateCardQuantityView(View):
    """API view for updating a card's quantity in a collection."""
    def post(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        card_id = request.POST.get('card_id')
        action = request.POST.get('action')  # 'increase' or 'decrease'
        
        collection = get_object_or_404(Collection, id=collection_id)
        card = get_object_or_404(Card, id=card_id)
        
        # Get or create the collection card entry
        collection_card, created = CollectionCard.objects.get_or_create(
            collection=collection,
            card=card,
            defaults={'quantity': 0}
        )
        
        # Update quantity based on action
        if action == 'increase':
            if collection_card.quantity != -1:  # Don't increase if already infinite
                collection_card.quantity += 1
        elif action == 'decrease':
            if collection_card.quantity > 0:  # Don't go below 0
                collection_card.quantity -= 1
            # Don't decrease if infinite (-1)
        
        collection_card.save()
        
        return JsonResponse({
            'success': True,
            'quantity': collection_card.quantity
        })