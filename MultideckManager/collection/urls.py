from django.urls import path
from . import views

urlpatterns = [
    path('', views.CollectionListView.as_view(), name='collection_list'),
    path('collection/<int:pk>/', views.CollectionDetailView.as_view(), name='collection_detail'),
    
    # Decklist routes
    path('collection/<int:collection_id>/decklist/create/', views.CreateDecklistView.as_view(), name='create_decklist'),
    path('collection/<int:collection_id>/decklist/<int:pk>/', views.DecklistDetailView.as_view(), name='decklist_detail'),
    path('collection/<int:collection_id>/decklist/<int:pk>/delete/', views.DeleteDecklistView.as_view(), name='delete_decklist'),
    path('collection/<int:collection_id>/decklist/<int:decklist_id>/toggle-active/', views.ToggleDecklistActiveView.as_view(), name='toggle_decklist_active'),
    
    # Decklist Card Management
    path('collection/<int:collection_id>/decklist/<int:decklist_id>/search-cards/', views.DecklistCardSearchView.as_view(), name='search_decklist_cards'),
    path('collection/<int:collection_id>/decklist/<int:decklist_id>/update-card/', views.UpdateDecklistCardView.as_view(), name='update_decklist_card'),
    
    # Decklist Import/Export
    path('collection/<int:collection_id>/decklist/<int:decklist_id>/import/', views.ImportDecklistView.as_view(), name='import_decklist'),
    path('collection/<int:collection_id>/decklist/<int:decklist_id>/export/', views.ExportDecklistView.as_view(), name='export_decklist'),
    
    # Collection Card Management
    path('collection/<int:collection_id>/search-cards/', views.CardSearchView.as_view(), name='search_cards'),
    path('collection/<int:collection_id>/update-card-quantity/', views.UpdateCardQuantityView.as_view(), name='update_card_quantity'),

    # Collection Import/Export
    path('collection/<int:collection_id>/import-cards/', views.ImportCardsView.as_view(), name='import_cards'),
    path('collection/<int:collection_id>/export-cards/', views.ExportCardsView.as_view(), name='export_cards'),
]