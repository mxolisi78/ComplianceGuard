from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("start/", views.start, name="start"),
    path("review/<str:thread_id>/", views.review_detail, name="review_detail"),
    path("review/<str:thread_id>/decide/", views.decide, name="decide"),
]