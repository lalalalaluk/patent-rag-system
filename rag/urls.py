"""
URL configuration for RAG app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Template views
    path('', views.index_view, name='index'),
    path('query/', views.query_page_view, name='query_page'),
    path('health-page/', views.health_page_view, name='health_page'),

    # API views
    path('api/query/', views.query_view, name='api_query'),
    path('api/health/', views.health_view, name='api_health'),
]
