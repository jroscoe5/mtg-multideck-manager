from django.urls import path
from . import views

urlpatterns = [
    path('', views.CollectionListView.as_view(), name='collection_list'),
    path('collection/<int:pk>/', views.CollectionDetailView.as_view(), name='collection_detail'),
    
    # API routes
    path('collection/<int:collection_id>/search-cards/', views.CardSearchView.as_view(), name='search_cards'),
    path('collection/<int:collection_id>/update-card-quantity/', views.UpdateCardQuantityView.as_view(), name='update_card_quantity'),
]