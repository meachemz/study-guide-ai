from django.db import models
from accounts.models import Quiz, Question
# Create your models here.

# In quiz_app/models.py

from django.db import models

# ... Quiz and Question models ...

class Submission(models.Model):
    # This links the Submission back to the Quiz that was taken
    quiz = models.ForeignKey(
        Quiz, 
        related_name='submissions', 
        on_delete=models.CASCADE
    )
    
    # Student's information
    student_name = models.CharField(max_length=255)
    student_email = models.EmailField()
    
    # A JSONField to store the student's answers.
    # The format will be: {'0': 'Answer A', '1': 'Answer C', ...}
    answers = models.JSONField(default=dict)
    
    score = models.PositiveIntegerField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Submission by {self.student_name} for '{self.quiz.title}'"

    class Meta:
        # This makes sure the newest submissions appear at the top
        ordering = ['-submitted_at']