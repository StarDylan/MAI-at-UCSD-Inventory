from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("view_database/", views.view_database, name="view_database"),
    path("view/audit/", views.audit_view, name="audit"),
    path('delete/category/', views.delete_category_list_view, name='delete_category_list_view'),
    path('delete/category/<uuid:uuid>/', views.delete_category, name='delete_category'),
    path('delete/image/', views.delete_image_list_view, name='delete_image_list_view'),

    path('accounts/profile/', views.profile_view, name='profile')
]