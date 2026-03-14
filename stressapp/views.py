from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Avg
import joblib, os

from .models import StressRecord, EmployeeProfile, Project, ProjectAllocation

# 🔹 Load ML model
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model = joblib.load(os.path.join(BASE_DIR, "stress_model.pkl"))
scaler = joblib.load(os.path.join(BASE_DIR, "scaler.pkl"))

# 🔹 Home Page
def home(request):
    return render(request, 'admin_home.html')

# 🔹 Login
def user_login(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.is_superuser or user.is_staff:
                return redirect('/admin-dashboard/')

            profile = EmployeeProfile.objects.filter(user=user).first()
            if profile:
                if profile.role == 'PM':
                    return redirect('/pm-dashboard/')
                elif profile.role == 'EMP':
                    return redirect('/employee-dashboard/')
            return redirect('/')
        else:
            error = "Invalid credentials"
    return render(request, 'login.html', {'error': error})

# 🔹 Admin Dashboard
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('/')

    employees = EmployeeProfile.objects.all()
    projects = Project.objects.all()
    allocations = ProjectAllocation.objects.all()
    records = StressRecord.objects.all()

    total_employees = employees.count()
    total_projects = projects.count()
    total_allocations = allocations.count()
    avg_score = records.aggregate(Avg('mental_health_score'))['mental_health_score__avg']
    high_risk_records = StressRecord.objects.filter(mental_health_score__lt=40)

    return render(request, 'admin_dashboard.html', {
        'employees': employees,
        'records': records,   # ✅ ADD THIS LINE
        'total_employees': total_employees,
        'total_projects': total_projects,
        'total_allocations': total_allocations,
        'avg_score': avg_score,
        'high_risk_records': high_risk_records
    })

# 🔹 PM Dashboard
@login_required
def pm_dashboard(request):

    profile = EmployeeProfile.objects.filter(user=request.user).first()

    if not profile or profile.role != 'PM':
        if request.user.is_superuser:
            return redirect('/admin-dashboard/')
        return redirect('/')

    projects = Project.objects.filter(created_by=request.user)

    project_data = []

    for project in projects:

        allocations = ProjectAllocation.objects.filter(project=project)

        # ⭐ NEW: calculate project progress
        total_progress = 0
        count = allocations.count()

        for alloc in allocations:
            total_progress += alloc.progress

        project_progress = 0
        if count > 0:
            project_progress = total_progress / count

        # ⭐ keep all old data + add progress
        project_data.append({
            'project': project,
            'allocations': allocations,
            'employee_count': count,
            'total_hours': sum(alloc.allocated_hours_per_week for alloc in allocations),
            'progress': project_progress
        })

    return render(request, 'pm/pm_dashboard.html', {
        'project_data': project_data
    })





# 🔹 PM Profile
@login_required
def pm_profile(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if not profile or profile.role != 'PM':
        return redirect('/')
    return render(request, 'pm/pm_profile.html', {'profile': profile})

# 🔹 Add Employee
@login_required
def add_employee(request):
    if not request.user.is_superuser:
        return redirect('/')
    message = None
    if request.method == 'POST':
        user = User.objects.create_user(
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        EmployeeProfile.objects.create(
            user=user,
            employee_id=request.POST.get('employee_id'),
            full_name=request.POST.get('full_name'),
            age=request.POST.get('age'),
            gender=request.POST.get('gender'),
            department=request.POST.get('department'),
            job_role=request.POST.get('job_role'),
            work_experience=request.POST.get('work_experience'),
            role=request.POST.get('role')
        )
        message = "Employee Registered Successfully"
    return render(request, 'add_emp.html', {'message': message})

# 🔹 Employee Dashboard
@login_required
def employee_dashboard(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if not profile or profile.role != 'EMP':
        return redirect('/')

    allocations = ProjectAllocation.objects.filter(employee=profile)
    total_allocated_hours = sum(a.allocated_hours_per_week for a in allocations)

    score, status, recommendation = None, None, None
    if request.method == 'POST':
        workload_score = float(request.POST.get('workload_score'))
        job_satisfaction = float(request.POST.get('job_satisfaction'))
        sleep_hours = float(request.POST.get('sleep_hours'))
        physical_activity = float(request.POST.get('physical_activity'))
        caffeine = float(request.POST.get('caffeine'))
        stress_level = float(request.POST.get('stress_level'))

        input_data = [[
            total_allocated_hours,
            workload_score,
            job_satisfaction,
            sleep_hours,
            physical_activity,
            caffeine,
            stress_level
        ]]
        input_scaled = scaler.transform(input_data)
        score = model.predict(input_scaled)[0]

        if score < 40:
            status = "High Risk"
            recommendation = "You are under high stress. Reduce workload, improve sleep, reduce caffeine, and consider taking leave."
        elif score < 70:
            status = "Medium Risk"
            recommendation = "Moderate stress detected. Improve sleep schedule and increase physical activity."
        else:
            status = "Healthy"
            recommendation = "Good mental health. Maintain work-life balance and healthy routine."

        StressRecord.objects.create(
            user=request.user,
            work_hours_per_week=total_allocated_hours,
            workload_score=workload_score,
            job_satisfaction=job_satisfaction,
            sleep_hours=sleep_hours,
            physical_activity_hrs=physical_activity,
            caffeine_intake=caffeine,
            stress_level=stress_level,
            mental_health_score=score
        )

    records = StressRecord.objects.filter(user=request.user).order_by('-created_at')
    chart_labels = [r.created_at.strftime("%Y-%m-%d") for r in records[::-1]]
    chart_scores = [r.mental_health_score for r in records[::-1]]

    return render(request, 'emp/emp_dashboard.html', {
        'profile': profile,
        'allocations': allocations,
        'total_allocated_hours': total_allocated_hours,
        'score': score,
        'status': status,
        'recommendation': recommendation,
        'records': records,
        'chart_labels': chart_labels,
        'chart_scores': chart_scores
    })

# 🔹 Project Management
@login_required
def create_project(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if not profile or profile.role != 'PM':
        return redirect('/')
    if request.method == 'POST':
        Project.objects.create(
            project_name=request.POST.get('project_name'),
            project_description=request.POST.get('project_description'),
            max_employees=request.POST.get('max_employees'),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            created_by=request.user
        )
        return redirect('/pm-dashboard/')
    return render(request, 'pm/create_project.html')

@login_required
def allocate_employee(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if not profile or profile.role != 'PM':
        return redirect('/')
    employees = EmployeeProfile.objects.filter(role='EMP')
    projects = Project.objects.filter(created_by=request.user)
    error = None
    if request.method == 'POST':
        project_id = request.POST.get('project')
        selected_employees = request.POST.getlist('employees')
        project = Project.objects.get(id=project_id)
        current_count = ProjectAllocation.objects.filter(project=project).count()
        if current_count + len(selected_employees) > project.max_employees:
            error = f"Only {project.max_employees - current_count} slots remaining!"
        else:
            for emp_id in selected_employees:
                employee = EmployeeProfile.objects.get(id=emp_id)
                hours = request.POST.get(f'hours_{emp_id}')
                task = request.POST.get(f'task_{emp_id}')
                if hours:
                    ProjectAllocation.objects.create(
                        employee=employee,
                        project=project,
                        allocated_hours_per_week=hours,
                        task_role=task,
                        allocated_by=request.user
                    )
            return redirect('/project-allocations/')
    return render(request, 'pm/allocate_employee.html', {
        'employees': employees,
        'projects': projects,
        'error': error
    })

# 🔹 Project Allocations (Admin + PM)
@login_required
def project_allocations(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if request.user.is_superuser:
        projects = Project.objects.all()
    elif profile and profile.role == 'PM':
        projects = Project.objects.filter(created_by=request.user)
    else:
        return redirect('/')

    project_data = []
    for project in projects:
        allocations = ProjectAllocation.objects.filter(project=project)
        total_hours = sum(a.allocated_hours_per_week for a in allocations)
        project_data.append({
            'project': project,
            'allocations': allocations,
            'total_hours': total_hours,
            'employee_count': allocations.count()
        })
    return render(request, 'pm/project_allocations.html', {'project_data': project_data})

# 🔹 Project Detail
@login_required
def project_detail(request, project_id):
    profile = EmployeeProfile.objects.filter(user=request.user).first()

    if request.user.is_superuser:
        project = get_object_or_404(Project, id=project_id)
    elif profile and profile.role == 'PM':
        project = get_object_or_404(Project, id=project_id, created_by=request.user)
    else:
        return redirect('/')

    allocations = ProjectAllocation.objects.filter(project=project)
    total_hours = sum(a.allocated_hours_per_week for a in allocations)

    return render(request, 'pm/project_detail.html', {
        'project': project,
        'allocations': allocations,
        'total_hours': total_hours,
        'employee_count': allocations.count()
    })

# 🔹 Project Mental Report (PM only)
@login_required
def project_mental_report(request):

    profile = EmployeeProfile.objects.filter(user=request.user).first()

    if not profile or profile.role != 'PM':
        return redirect('/')

    # Get projects created by this PM
    projects = Project.objects.filter(created_by=request.user)

    # Get employees allocated to these projects
    allocations = ProjectAllocation.objects.filter(project__in=projects)

    employees = [a.employee.user for a in allocations]

    # Get stress records of those employees
    records = StressRecord.objects.filter(user__in=employees).order_by('-created_at')

    return render(request, 'pm/project_mental_report.html', {
        'records': records
    })



# 🔹 Logout
def logout_view(request):
    logout(request)
    return redirect('login')

# 🔹 View Employees (Admin only)
@login_required
def view_employees(request):
    if not request.user.is_superuser:
        return redirect('/')
    employees = EmployeeProfile.objects.filter(role='EMP')
    return render(request, 'view_emp.html', {'employees': employees})

# 🔹 View Project Managers (Admin only)
@login_required
def view_project_managers(request):
    if not request.user.is_superuser:
        return redirect('/')
    managers = EmployeeProfile.objects.filter(role='PM')
    return render(request, 'view_pm.html', {'managers': managers})

# 🔹 Login Redirect (role-based)
@login_required
def login_redirect(request):
    if request.user.is_superuser:
        return redirect('/admin-dashboard/')
    else:
        profile = EmployeeProfile.objects.filter(user=request.user).first()
        if profile and profile.role == 'PM':
            return redirect('/pm-dashboard/')
        elif profile and profile.role == 'EMP':
            return redirect('/employee-dashboard/')
        else:
            return redirect('/')



@login_required
def admin_project_allocations(request):
    if not request.user.is_superuser:
        return redirect('/')

    projects = Project.objects.all()
    project_data = []
    for project in projects:
        allocations = ProjectAllocation.objects.filter(project=project)
        total_hours = sum(a.allocated_hours_per_week for a in allocations)
        project_data.append({
            'project': project,
            'allocations': allocations,
            'total_hours': total_hours,
            'employee_count': allocations.count()
        })

    return render(request, 'admin_project_allocation.html', {
        'project_data': project_data
    })


@login_required
def admin_project_detail(request, project_id):
    if not request.user.is_superuser:
        return redirect('/')

    project = get_object_or_404(Project, id=project_id)
    allocations = ProjectAllocation.objects.filter(project=project)
    total_hours = sum(a.allocated_hours_per_week for a in allocations)

    return render(request, 'admin_project_details.html', {
        'project': project,
        'allocations': allocations,
        'total_hours': total_hours,
        'employee_count': allocations.count()
    })



@login_required
def view_stress_records(request):
    if not request.user.is_superuser:
        return redirect('/')

    records = StressRecord.objects.select_related('user').order_by('-created_at')
    return render(request, 'view_stress_records.html', {'records': records})



@login_required
def emp_profile(request):
    profile = EmployeeProfile.objects.get(user=request.user)
    return render(request, 'emp/emp_profile.html', {'profile': profile})

@login_required
def emp_projects(request):
    allocations = ProjectAllocation.objects.filter(employee__user=request.user)
    total_hours = sum(a.allocated_hours_per_week for a in allocations)
    return render(request, 'emp/emp_projects.html', {
        'allocations': allocations,
        'total_allocated_hours': total_hours
    })



    

from django.db.models import Sum

@login_required
def emp_stress_form(request):

    profile = EmployeeProfile.objects.get(user=request.user)

    allocations = ProjectAllocation.objects.filter(employee=profile)

    allocations = ProjecstAllocation.objects.filter(
    employee=profile,
    project__status__in=['pending', 'in_progress']
)


    total_allocated_hours = allocations.aggregate(
        Sum('allocated_hours_per_week')
    )['allocated_hours_per_week__sum'] or 0

    score = status = recommendation = None

    if request.method == 'POST':

        work_exp = profile.work_experience
        work_hours = total_allocated_hours
        remote = request.POST.get("remote_work")
        workload = request.POST.get("workload_score")
        satisfaction = request.POST.get("job_satisfaction")
        sleep = request.POST.get("sleep_hours")
        activity = request.POST.get("physical_activity_hrs")
        caffeine = request.POST.get("caffeine_intake")
        stress = request.POST.get("stress_level")

        score = (float(workload)*2 + float(stress)*2 - float(satisfaction)
                 + float(caffeine)*0.5 - float(sleep) + float(activity)*0.5)

        if score < 40:
            status = "High Risk"
            recommendation = "Please consult HR or counselor"

        elif score < 70:
            status = "Medium Risk"
            recommendation = "Maintain balance"

        else:
            status = "Healthy"
            recommendation = "Keep up your good habits"

        StressRecord.objects.create(
            user=request.user,
            work_experience=work_exp,
            work_hours_per_week=work_hours,
            remote_work=remote,
            workload_score=workload,
            job_satisfaction=satisfaction,
            sleep_hours=sleep,
            physical_activity_hrs=activity,
            caffeine_intake=caffeine,
            stress_level=stress,
            mental_health_score=score
        )

    return render(request, 'emp/emp_stress_form.html', {
        'profile': profile,
        'total_allocated_hours': total_allocated_hours,
        'score': score,
        'status': status,
        'recommendation': recommendation
    })










@login_required
def emp_history(request):
    records = StressRecord.objects.filter(user=request.user).order_by('-created_at')
    avg_score = records.aggregate(Avg('mental_health_score'))['mental_health_score__avg']
    return render(request, 'emp/emp_history.html', {
        'records': records,
        'personal_avg': avg_score
    })




@login_required
def update_progress(request, allocation_id):

    allocation = ProjectAllocation.objects.get(id=allocation_id)

    if request.method == "POST":

        progress = request.POST.get('progress')

        if progress:
            allocation.progress = int(progress)
            allocation.save()

    return redirect('/emp/projects/')



from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from .models import Project, ProjectAllocation, EmployeeProfile


@login_required
def pm_project_progress(request):

    profile = EmployeeProfile.objects.filter(user=request.user).first()

    if not profile or profile.role != "PM":
        return redirect('/')

    projects = Project.objects.filter(created_by=request.user)

    project_data = []

    for project in projects:

        allocations = ProjectAllocation.objects.filter(project=project)

        avg_progress = allocations.aggregate(avg=Avg('progress'))['avg'] or 0

        project_data.append({
            'project': project,
            'allocations': allocations,
            'progress': avg_progress
        })

    return render(request, 'pm/project_progress.html', {
        'project_data': project_data
    })








from django.db.models import Avg
from django.contrib.auth.decorators import login_required
from .models import Project, ProjectAllocation

@login_required
def admin_project_progress(request):

    projects = Project.objects.all()

    pending_projects = []
    processing_projects = []
    completed_projects = []

    for project in projects:

        allocations = ProjectAllocation.objects.filter(project=project)

        # calculate overall progress
        avg_progress = allocations.aggregate(avg=Avg('progress'))['avg'] or 0

        project_data = {
            'project': project,
            'allocations': allocations,
            'progress': round(avg_progress,2)
        }

        if avg_progress == 0:
            pending_projects.append(project_data)

        elif avg_progress < 100:
            processing_projects.append(project_data)

        else:
            completed_projects.append(project_data)

    return render(request,'admin/admin_project_progress.html',{
        'pending_projects': pending_projects,
        'processing_projects': processing_projects,
        'completed_projects': completed_projects
    })


from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from .models import EmployeeProfile, ProjectAllocation


@login_required
def emp_project_progress(request):

    profile = EmployeeProfile.objects.filter(user=request.user).first()

    if not profile or profile.role != "EMP":
        return redirect('/')

    allocations = ProjectAllocation.objects.filter(employee=profile)

    projects = {}

    for alloc in allocations:

        project = alloc.project

        if project not in projects:

            all_alloc = ProjectAllocation.objects.filter(project=project)

            total_progress = 0
            count = all_alloc.count()

            for a in all_alloc:
                total_progress += a.progress

            avg_progress = total_progress / count if count > 0 else 0

            project_data = {
                'project': project,
                'allocations': all_alloc,
                'progress': avg_progress
            }

            projects[project] = project_data

    pending_projects = []
    processing_projects = []
    completed_projects = []

    for data in projects.values():

        if data['progress'] == 0:
            pending_projects.append(data)

        elif data['progress'] < 100:
            processing_projects.append(data)

        else:
            completed_projects.append(data)

    return render(request, 'emp/emp_project_progress.html', {
        'pending_projects': pending_projects,
        'processing_projects': processing_projects,
        'completed_projects': completed_projects
    })






@login_required
def edit_employee(request, emp_id):

    if not request.user.is_superuser:
        return redirect('/')

    employee = get_object_or_404(EmployeeProfile, id=emp_id)

    if request.method == 'POST':
        employee.full_name = request.POST.get('full_name')
        employee.department = request.POST.get('department')
        employee.job_role = request.POST.get('job_role')
        employee.work_experience = request.POST.get('experience')

        employee.save()

        return redirect('view_employees')

    return render(request, 'admin/edit_emp.html', {'employee': employee})






@login_required
def delete_employee(request, emp_id):

    if not request.user.is_superuser:
        return redirect('/')

    employee = EmployeeProfile.objects.get(id=emp_id)

    # delete user (this deletes employee profile automatically)
    employee.user.delete()

    return redirect('/view-employees/')





@login_required
def edit_pm(request, pm_id):

    if not request.user.is_superuser:
        return redirect('/')

    pm = get_object_or_404(EmployeeProfile, id=pm_id)

    if request.method == 'POST':
        pm.full_name = request.POST.get('full_name')
        pm.department = request.POST.get('department')
        pm.job_role = request.POST.get('job_role')
        pm.work_experience = request.POST.get('experience')

        pm.save()

        return redirect('view_project_managers')

    return render(request, 'admin/edit_pm.html', {'pm': pm})




@login_required
def delete_pm(request, pm_id):

    if not request.user.is_superuser:
        return redirect('/')

    pm = get_object_or_404(EmployeeProfile, id=pm_id)

    # delete user + profile
    pm.user.delete()

    return redirect('view_project_managers')