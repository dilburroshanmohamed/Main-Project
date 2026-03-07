from django.contrib import admin
from .models import EmployeeProfile, Project, ProjectAllocation, StressRecord

@admin.register(EmployeeProfile)
class EmployeeProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'employee_id', 'department', 'role')


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'created_by')


from django.contrib import admin
from .models import ProjectAllocation


@admin.register(ProjectAllocation)
class ProjectAllocationAdmin(admin.ModelAdmin):

    list_display = (
        'employee',
        'project',
        'task_role',
        'allocated_hours_per_week',
        'progress',
        'allocated_by',
        'allocated_date'
    )

@admin.register(StressRecord)
class StressRecordAdmin(admin.ModelAdmin):
    list_display = ('user', 'mental_health_score', 'created_at')