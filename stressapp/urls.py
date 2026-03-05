from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login-redirect/', views.login_redirect, name='login_redirect'),

    # Dashboards
    path('employee-dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('pm-dashboard/', views.pm_dashboard, name='pm_dashboard'),

    # Employee & PM management
    path('add-employee/', views.add_employee, name='add_employee'),
    path('pm-profile/', views.pm_profile, name='pm_profile'),
    path('view-employees/', views.view_employees, name='view_employees'),
    path('view-project-managers/', views.view_project_managers, name='view_project_managers'),

    # Project management
    path('create-project/', views.create_project, name='create_project'),
    path('allocate-employee/', views.allocate_employee, name='allocate_employee'),

    # PM project pages
    path('project/<int:project_id>/', views.project_detail, name='project_detail'),
    path('project-allocations/', views.project_allocations, name='project_allocations'),
    path('project-mental-report/', views.project_mental_report, name='project_mental_report'),

    # ✅ Admin project pages
    path('admin-project-allocations/', views.admin_project_allocations, name='admin_project_allocations'),
    path('admin-project/<int:project_id>/', views.admin_project_detail, name='admin_project_detail'),

    # Auth
    path('login/', views.user_login, name='login'),
    path("logout/", views.logout_view, name="logout"),

    path('view-stress-records/', views.view_stress_records, name='view_stress_records'),
    path('mental-report/', views.project_mental_report, name='mental_report'),

    path('emp/profile/', views.emp_profile, name='emp_profile'),
    path('emp/projects/', views.emp_projects, name='emp_projects'),
    path('emp/stress/', views.emp_stress_form, name='emp_stress_form'),
    path('emp/history/', views.emp_history, name='emp_history'),
]
