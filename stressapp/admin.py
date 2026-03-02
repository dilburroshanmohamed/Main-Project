from django.contrib import admin
from .models import EmployeeProfile, Project, ProjectAllocation, StressRecord

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'employee_id', 'department', 'role')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'created_by')


@admin.register(ProjectAllocation)
class ProjectAllocationAdmin(admin.ModelAdmin):
    list_display = ('employee', 'project', 'allocated_hours_per_week')


@admin.register(StressRecord)
class StressRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'mental_health_score', 'created_at')