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
    path('delete/image/<uuid:uuid>/', views.delete_image, name='delete_image'),
    # path('delete/image/<int:id>/', views.delete_image, name='delete_image'),
    path('delete/subcategory/', views.delete_subcategory_list_view, name='delete_subcategory_list_view'),
    path('delete/subcategory/<uuid:uuid>/', views.delete_subcategory, name='delete_subcategory'),

    path('edit/category/<uuid:pk>/', views.CategoryUpdateView.as_view(), name='edit_category'),
    path('edit/item/<uuid:pk>/', views.ItemUpdateView.as_view(), name='edit_item'),

    path('create/category/', views.CategoryCreateView.as_view(), name='create_category'),
    path('create/subcategory/', views.SubcategoryCreateView.as_view(), name='create_subcategory'),

    path('create/item/', views.ItemCreateView.as_view(), name='create_item'),

    path('view/', views.view_database, name='view_database'),
    path('view/all/', views.view_all_items, name='view_all_items'),
    path('view/category/<uuid:uuid>/', views.view_category_items, name='view_category'),
    path('view/subcategory/<uuid:uuid>/', views.view_subcategory_items, name='view_subcategory'),
    path('view/item/<uuid:uuid>/', views.view_item, name='view_item'),

    path('delete/item/<uuid:uuid>/', views.delete_item, name='delete_item'),
    path('restore/item/<uuid:uuid>/', views.restore_item, name='restore_item'),

    path('upload/photo/<uuid:uuid>/', views.upload_photo, name='upload_photo'),

    path('search/check_in/', views.SearchCheckInView.as_view(), name='search_check_in'),
    path('search/check_out/', views.SearchCheckOutView.as_view(), name='search_check_out'),

    path('view/deleted_items', views.view_deleted_items, name='view_deleted_items'),

    path('accounts/profile/', views.profile_view, name='profile'),
    path('accounts/logout/', views.logout_view, name='logout'),

    path('manage/users/', views.manage_users_view, name='manage_users'),
    path('edit/user/<int:pk>/', views.edit_user_role_api, name='edit_user_role'),
    path('view/user/<int:pk>/', views.view_user_profile_view, name='view_user'),
    path('delete/user/<int:pk>/', views.delete_user_view, name='delete_user'),
    path('restore/user/<int:pk>/', views.restore_user_view, name='restore_user'),
    path('create/user/', views.UserCreateView.as_view(), name='create_user'),
    
    
]

