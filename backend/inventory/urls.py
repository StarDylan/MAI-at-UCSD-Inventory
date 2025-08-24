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
    # path('delete/image/<int:id>/', views.delete_image, name='delete_image'),
    path('delete/subcategory/', views.delete_subcategory_list_view, name='delete_subcategory_list_view'),
    path('delete/subcategory/<uuid:uuid>/', views.delete_subcategory, name='delete_subcategory'),

    path('edit/category/<uuid:uuid>/', views.edit_category, name='edit_category'),

    path('accounts/profile/', views.profile_view, name='profile')
]