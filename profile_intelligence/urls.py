from django.urls import path
from profile_intelligence.views import profile_list, profile_search

urlpatterns=[
    path('profiles', profile_list, name='profile-list'),
    path('profiles/search', profile_search, name='profile-search'),
]