from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.register_view, name='register'),
    path('auth/login/', views.login_view, name='login'),
    path('auth/logout/', views.logout_view, name='logout'),

    # Main editor
    path('', views.editor_view, name='editor'),

    # Dataset API
    path('api/upload/', views.upload_dataset, name='upload_dataset'),
    path('api/datasets/', views.list_datasets, name='list_datasets'),
    path('api/dataset/<int:dataset_id>/', views.get_dataset, name='get_dataset'),
    path('api/dataset/<int:dataset_id>/delete/', views.delete_dataset, name='delete_dataset'),
    path('api/dataset/<int:dataset_id>/save/', views.save_dataset, name='save_dataset'),
    path('api/dataset/<int:dataset_id>/history/', views.get_analysis_history, name='analysis_history'),

    # Analysis API
    path('api/analyze/', views.run_analysis, name='run_analysis'),
    path('api/chart/', views.generate_chart, name='generate_chart'),
    path('api/export/', views.export_output, name='export_output'),
]
