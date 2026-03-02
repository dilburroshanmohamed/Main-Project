from django.contrib import admin
from django.urls import path, include
from stressapp import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Django default admin panel
    path('admin/', admin.site.urls),

    # App URLs
    path('', include('stressapp.urls')),

    # Common Login (for both admin & employee)
    path('login/', views.user_login, name='login'),

    path('change-password/', auth_views.PasswordChangeView.as_view(
    template_name='change_password.html',
    success_url='/admin-dashboard/'
), name='change_password'),
]