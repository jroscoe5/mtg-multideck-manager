from django import forms
from .models import Collection, Decklist, Card, CollectionCard, DecklistCard


class CollectionForm(forms.ModelForm):
    """Form for creating new collections."""
    
    class Meta:
        model = Collection
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 
                                           'placeholder': 'Collection Name'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 
                                                 'placeholder': 'Description (optional)', 
                                                 'rows': 4}),
        }


class CollectionEditForm(forms.ModelForm):
    """Form for editing existing collections."""
    
    class Meta:
        model = Collection
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 
                                                 'rows': 4}),
        }
        
        
        
class DecklistForm(forms.ModelForm):
    """Form for creating new decklists."""
    
    class Meta:
        model = Decklist
        fields = ['name', 'description', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 
                                           'placeholder': 'Decklist Name'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 
                                                 'placeholder': 'Description (optional)', 
                                                 'rows': 4}),
            'active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'}),
        }


class DecklistEditForm(forms.ModelForm):
    """Form for editing existing decklists."""
    
    class Meta:
        model = Decklist
        fields = ['name', 'description', 'active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 
                                                 'rows': 4}),
            'active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'}),
        }


class DecklistCardForm(forms.ModelForm):
    """Form for adding cards to a decklist."""
    
    class Meta:
        model = DecklistCard
        fields = ['card', 'quantity', 'is_sideboard']
        widgets = {
            'card': forms.Select(attrs={'class': 'w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500'}),
            'quantity': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500', 
                                                 'min': '1'}),
            'is_sideboard': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500'}),
        }