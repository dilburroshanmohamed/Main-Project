from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('employee-dashboard/', views.dashboard, name='employee_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('add-employee/', views.add_employee, name='add_employee'),  
    path('pm-dashboard/', views.pm_dashboard, name='pm_dashboard'),
    path('create-project/', views.create_project, name='create_project'),
    path('allocate-employee/', views.allocate_employee, name='allocate_employee'),
    path('pm-profile/', views.pm_profile, name='pm_profile'),
    path('project-allocations/', views.project_allocations, name='project_allocations'),
    path('project-mental-report/', views.project_mental_report, name='project_mental_report'),
    path('login/', views.user_login, name='login'),
    path("logout/", views.logout_view, name="logout"),
]