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