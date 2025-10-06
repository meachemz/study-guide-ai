# In quiz_app/admin.py
import csv
from django.http import HttpResponse
from django.contrib import admin
from .models import Quiz, Question, Submission

# --- This is the new function that handles the CSV export ---
def export_to_csv(modeladmin, request, queryset):
    # Set up the response to be a downloadable CSV file
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="submissions.csv"'
    
    # Create a CSV writer
    writer = csv.writer(response)
    
    # Write the header row
    writer.writerow(['Quiz Title', 'Student Name', 'Email', 'Score', 'Submitted At'])
    
    # Write the data rows
    for submission in queryset:
        writer.writerow([
            submission.quiz.title,
            submission.student_name,
            submission.student_email,
            submission.score,
            submission.submitted_at.strftime('%Y-%m-%d %H:%M:%S') # Format the date
        ])
        
    return response

# Give the action a user-friendly name in the admin
export_to_csv.short_description = "Export Selected Submissions to CSV"
# ----------------------------------------------------------------

class SubmissionInline(admin.TabularInline):
    model = Submission
    extra = 0
    readonly_fields = ('student_name', 'student_email', 'score', 'submitted_at')

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ('title', 'access_code', 'created_at')
    inlines = [QuestionInline, SubmissionInline]

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'student_email', 'quiz', 'score', 'submitted_at')
    list_filter = ('quiz', 'submitted_at')
    actions = [export_to_csv] # <-- Add the new action here