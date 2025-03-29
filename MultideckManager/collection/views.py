from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.generic import ListView, DetailView
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Q, Sum
from .models import Collection, Decklist, Card, CollectionCard, DecklistCard
from .forms import CollectionForm, CollectionEditForm, DecklistForm, DecklistEditForm
from .services.import_export import ImportExport

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
            unique_cards = collection_cards.filter(quantity__gt=0).count()
            
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
        

class ImportCardsView(View):
    """View for importing cards into a collection."""
    
    def post(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        collection = get_object_or_404(Collection, id=collection_id)
        
        import_type = request.POST.get('import_type')
        skip_unknown = request.POST.get('skip_unknown') == 'true'
        
        # Process the input based on import type
        try:
            if import_type == 'paste':
                card_input = request.POST.get('card_input', '')
                cards_to_import = ImportExport.parse_text_input(card_input)
            else:  # file import
                if 'card_file' not in request.FILES:
                    return JsonResponse({
                        'success': False,
                        'error': 'No file was uploaded.'
                    })
                
                card_file = request.FILES['card_file']
                if card_file.name.endswith('.csv'):
                    cards_to_import = ImportExport.parse_csv_file(card_file)
                else:
                    # Assume it's a plain text file
                    cards_to_import = ImportExport.parse_text_input(card_file.read().decode('utf-8'))
            
            # Process the cards
            result = ImportExport.process_card_import(collection, cards_to_import, skip_unknown)
            return JsonResponse(result)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class ExportCardsView(View):
    """View for exporting cards from a collection."""
    
    def get(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        collection = get_object_or_404(Collection, id=collection_id)
        
        return ImportExport.export_collection_to_csv(collection)
    


class DecklistDetailView(DetailView):
    """View for displaying a single decklist's details."""
    model = Decklist
    template_name = 'collection/decklist_detail.html'
    context_object_name = 'decklist'
    
    def get_object(self):
        collection_id = self.kwargs.get('collection_id')
        decklist_id = self.kwargs.get('pk')
        return get_object_or_404(Decklist, id=decklist_id, collection_id=collection_id)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['collection'] = self.object.collection
        context['edit_form'] = DecklistEditForm(instance=self.object)
        
        # Get cards in this decklist
        mainboard_cards = DecklistCard.objects.filter(decklist=self.object, is_sideboard=False)
        sideboard_cards = DecklistCard.objects.filter(decklist=self.object, is_sideboard=True)
        
        context['mainboard_cards'] = mainboard_cards.select_related('card')
        context['sideboard_cards'] = sideboard_cards.select_related('card')
        
        # Calculate deck stats
        if mainboard_cards.exists() or sideboard_cards.exists():
            # Count cards by type
            card_types = {}
            
            for deck_card in mainboard_cards:
                card = deck_card.card
                if card.type_line:
                    # Get the first major type
                    primary_types = [t.strip() for t in card.type_line.split('—')[0].split()]
                    for primary_type in primary_types:
                        if primary_type in ['Creature', 'Instant', 'Sorcery', 'Artifact', 'Enchantment', 'Planeswalker', 'Land']:
                            if primary_type in card_types:
                                card_types[primary_type] += deck_card.quantity
                            else:
                                card_types[primary_type] = deck_card.quantity
            
            # Get deck status
            status_code, status_message, conflicts = self.object.get_status()
            
            # Package stats
            context['deck_stats'] = {
                'mainboard_count': mainboard_cards.aggregate(Sum('quantity'))['quantity__sum'] or 0,
                'sideboard_count': sideboard_cards.aggregate(Sum('quantity'))['quantity__sum'] or 0,
                'type_counts': card_types,
                'status_code': status_code,
                'status_message': status_message,
                'conflicts': conflicts
            }
        else:
            # Empty deck
            context['deck_stats'] = {
                'mainboard_count': 0,
                'sideboard_count': 0,
                'type_counts': {},
                'status_code': 'inactive' if not self.object.active else 'ok',
                'status_message': 'Inactive' if not self.object.active else 'Active',
                'conflicts': None
            }
        
        return context
    
    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = DecklistEditForm(request.POST, instance=self.object)
        
        if form.is_valid():
            form.save()
            return redirect('decklist_detail', collection_id=self.object.collection_id, pk=self.object.pk)
        
        context = self.get_context_data(object=self.object)
        context['edit_form'] = form
        return render(request, self.template_name, context)


class CreateDecklistView(View):
    """View for creating a new decklist."""
    
    def get(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        collection = get_object_or_404(Collection, id=collection_id)
        
        form = DecklistForm()
        return render(request, 'collection/decklist_create.html', {
            'form': form,
            'collection': collection
        })
    
    def post(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        collection = get_object_or_404(Collection, id=collection_id)
        
        form = DecklistForm(request.POST)
        if form.is_valid():
            decklist = form.save(commit=False)
            decklist.collection = collection
            decklist.save()
            
            return redirect('decklist_detail', collection_id=collection_id, pk=decklist.id)
        
        return render(request, 'collection/decklist_create.html', {
            'form': form,
            'collection': collection
        })


class DeleteDecklistView(View):
    """View for deleting a decklist."""
    
    def post(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        decklist_id = kwargs.get('pk')
        
        decklist = get_object_or_404(Decklist, id=decklist_id, collection_id=collection_id)
        decklist.delete()
        
        return redirect('collection_detail', pk=collection_id)


class DecklistCardSearchView(View):
    """API view for searching cards for a decklist."""
    
    def get(self, request, *args, **kwargs):
        query = request.GET.get('query', '').strip()
        collection_id = kwargs.get('collection_id')
        decklist_id = kwargs.get('decklist_id')
        collection = get_object_or_404(Collection, id=collection_id)
        decklist = get_object_or_404(Decklist, id=decklist_id, collection=collection)
        
        if len(query) < 2:
            return JsonResponse({'results': []})
        
        # Search for cards matching the query
        cards = Card.objects.filter(
            Q(name__icontains=query)
        ).order_by('name')[:20]  # Limit to 20 results
        
        results = []
        for card in cards:
            # Try to get the card's quantity in the collection
            try:
                collection_card = CollectionCard.objects.get(collection=collection, card=card)
                collection_quantity = collection_card.quantity
            except CollectionCard.DoesNotExist:
                collection_quantity = 0
            
            # Try to get the card's quantity in the decklist (mainboard)
            try:
                mainboard_card = DecklistCard.objects.get(decklist=decklist, card=card, is_sideboard=False)
                mainboard_quantity = mainboard_card.quantity
            except DecklistCard.DoesNotExist:
                mainboard_quantity = 0
            
            # Try to get the card's quantity in the decklist (sideboard)
            try:
                sideboard_card = DecklistCard.objects.get(decklist=decklist, card=card, is_sideboard=True)
                sideboard_quantity = sideboard_card.quantity
            except DecklistCard.DoesNotExist:
                sideboard_quantity = 0
            
            results.append({
                'id': card.id,
                'name': card.name,
                'set_code': card.set_code,
                'mana_cost': card.mana_cost,
                'collector_number': card.collector_number,
                'type_line': card.type_line,
                'rarity': card.rarity,
                'collection_quantity': collection_quantity,
                'mainboard_quantity': mainboard_quantity,
                'sideboard_quantity': sideboard_quantity,
                'scryfall_uri': card.scryfall_uri,
            })
        
        return JsonResponse({'results': results})


class UpdateDecklistCardView(View):
    """API view for updating a card's quantity in a decklist."""
    
    def post(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        decklist_id = kwargs.get('decklist_id')
        
        card_id = request.POST.get('card_id')
        is_sideboard = request.POST.get('is_sideboard') == 'true'
        action = request.POST.get('action')  # 'increase', 'decrease', or 'remove'
        
        collection = get_object_or_404(Collection, id=collection_id)
        decklist = get_object_or_404(Decklist, id=decklist_id, collection=collection)
        card = get_object_or_404(Card, id=card_id)
        
        # Get or create the decklist card entry
        decklist_card, created = DecklistCard.objects.get_or_create(
            decklist=decklist,
            card=card,
            is_sideboard=is_sideboard,
            defaults={'quantity': 0}
        )
        
        # Update quantity based on action
        if action == 'increase':
            decklist_card.quantity += 1
        elif action == 'decrease':
                    if decklist_card.quantity > 1:
                        decklist_card.quantity -= 1
                    else:
                        # Remove the card if quantity would be 0
                        decklist_card.delete()
                        return JsonResponse({
                            'success': True,
                            'quantity': 0,
                            'removed': True
                        })
        elif action == 'remove':
            decklist_card.delete()
            return JsonResponse({
                'success': True,
                'quantity': 0,
                'removed': True
            })
        
        decklist_card.save()
        
        return JsonResponse({
            'success': True,
            'quantity': decklist_card.quantity,
            'removed': False
        })


class ImportDecklistView(View):
    """View for importing cards into a decklist."""
    
    def post(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        decklist_id = kwargs.get('decklist_id')
        
        collection = get_object_or_404(Collection, id=collection_id)
        decklist = get_object_or_404(Decklist, id=decklist_id, collection=collection)
        
        import_type = request.POST.get('import_type')
        clear_existing = request.POST.get('clear_existing') == 'true'
        
        # Process the input based on import type
        try:
            from collection.services.decklist_importer import DecklistImporter
            
            if import_type == 'paste':
                deck_input = request.POST.get('deck_input', '')
                cards_to_import = DecklistImporter.parse_text_input(deck_input)
            elif import_type == 'file':
                if 'deck_file' not in request.FILES:
                    return JsonResponse({
                        'success': False,
                        'error': 'No file was uploaded.'
                    })
                
                deck_file = request.FILES['deck_file']
                if deck_file.name.endswith('.csv'):
                    cards_to_import = DecklistImporter.parse_csv_file(deck_file)
                else:
                    # Assume it's a plain text file
                    cards_to_import = DecklistImporter.parse_text_input(deck_file.read().decode('utf-8'))
            elif import_type == 'archidekt':
                deck_id = request.POST.get('archidekt_id', '')
                if not deck_id:
                    return JsonResponse({
                        'success': False,
                        'error': 'No Archidekt deck ID provided.'
                    })
                
                cards_to_import = DecklistImporter.import_from_archidekt(deck_id)
                
                # If the import returns deck metadata, update the decklist
                if 'deck_name' in cards_to_import and not decklist.name:
                    decklist.name = cards_to_import['deck_name']
                if 'deck_description' in cards_to_import and not decklist.description:
                    decklist.description = cards_to_import['deck_description']
                decklist.save()
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid import type.'
                })
            
            # Process the cards
            result = DecklistImporter.import_cards_to_decklist(decklist, cards_to_import, clear_existing)
            return JsonResponse(result)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class ExportDecklistView(View):
    """View for exporting a decklist to various formats."""
    
    def get(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        decklist_id = kwargs.get('decklist_id')
        format_type = request.GET.get('format', 'txt')
        
        collection = get_object_or_404(Collection, id=collection_id)
        decklist = get_object_or_404(Decklist, id=decklist_id, collection=collection)
        
        # Get mainboard and sideboard cards
        mainboard = DecklistCard.objects.filter(decklist=decklist, is_sideboard=False).select_related('card')
        sideboard = DecklistCard.objects.filter(decklist=decklist, is_sideboard=True).select_related('card')
        
        if format_type == 'csv':
            # Create CSV response
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{decklist.name}_decklist.csv"'
            
            writer = csv.writer(response)
            writer.writerow(['Quantity', 'Card Name', 'Set', 'Collector Number', 'Section'])
            
            # Add mainboard cards
            if mainboard.exists():
                writer.writerow(['MAINBOARD'])
                for card in mainboard:
                    writer.writerow([
                        card.quantity,
                        card.card.name,
                        card.card.set_code.upper(),
                        card.card.collector_number,
                        'Mainboard'
                    ])
            
            # Add sideboard cards
            if sideboard.exists():
                writer.writerow(['SIDEBOARD'])
                for card in sideboard:
                    writer.writerow([
                        card.quantity,
                        card.card.name,
                        card.card.set_code.upper(),
                        card.card.collector_number,
                        'Sideboard'
                    ])
            
            return response
        else:
            # Default to text format
            response = HttpResponse(content_type='text/plain')
            response['Content-Disposition'] = f'attachment; filename="{decklist.name}_decklist.txt"'
            
            # Add deck name and description
            response.write(f"// {decklist.name}\n")
            if decklist.description:
                response.write(f"// {decklist.description}\n")
            response.write("\n")
            
            # Add mainboard cards
            if mainboard.exists():
                response.write("MAINBOARD\n")
                for card in mainboard:
                    response.write(f"{card.quantity} {card.card.name}\n")
                response.write("\n")
            
            # Add sideboard cards
            if sideboard.exists():
                response.write("SIDEBOARD\n")
                for card in sideboard:
                    response.write(f"{card.quantity} {card.card.name}\n")
            
            return response


class ToggleDecklistActiveView(View):
    """View for toggling a decklist's active status."""
    
    def post(self, request, *args, **kwargs):
        collection_id = kwargs.get('collection_id')
        decklist_id = kwargs.get('decklist_id')
        
        decklist = get_object_or_404(Decklist, id=decklist_id, collection_id=collection_id)
        decklist.active = not decklist.active
        decklist.save()
        
        return JsonResponse({
            'success': True,
            'active': decklist.active
        })