from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('requests/', views.request_list, name='request_list'),
    path('requests/create/', views.create_request, name='create_request'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('request/<int:pk>/export/', views.export_request_pdf, name='export_request_pdf'),
    path('approve/<int:pk>/', views.approve_request, name='approve'),
    path('reject/<int:pk>/', views.reject_request, name='reject'),
    path('reports/', views.reports, name='reports'),
    path('export-csv/', views.export_csv, name='export_csv'),
    path('profile/', views.profile, name='profile'),
    path('management/users/', views.manage_users, name='manage_users'),
    path('management/users/create/', views.create_user, name='create_user'),
    path('management/users/edit/<int:user_id>/', views.edit_user, name='edit_user'),
    path('management/users/delete/<int:pk>/', views.delete_user, name='delete_user'),
    path('management/departments/', views.manage_departments, name='manage_departments'),
    path('management/departments/create/', views.create_department, name='create_department'),
    path('management/departments/delete/<int:pk>/', views.delete_department, name='delete_department'),
    path('management/departments/edit/<int:pk>/', views.edit_department, name='edit_department'),
    path("request-file/<int:pk>/", views.open_request_file, name="open_request_file")
]