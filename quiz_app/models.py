from django.db import models
from accounts.models import Quiz, Question
# Create your models here.

# In quiz_app/models.py

from django.db import models

# ... Quiz and Question models ...

class Submission(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name="submissions")
    student_name = models.CharField(max_length=100)
    student_email = models.EmailField()
    answers = models.JSONField() # We'll store the selected answers here
    score = models.IntegerField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Submission by {self.student_name} for {self.quiz.title}"