from django.db import models
import random
import string

def generate_access_code():
    """Generates a unique 5-character uppercase alphanumeric code."""
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        if not Quiz.objects.filter(access_code=code).exists():
            return code

class Quiz(models.Model):
    title = models.CharField(max_length=200)
    class_name = models.CharField(max_length=100, blank=True, null=True)
    access_code = models.CharField(max_length=5, unique=True, default=generate_access_code)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} ({self.access_code})"

class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()
    # Options will be stored as a simple JSON list: ["Option A", "Option B", ...]
    options = models.JSONField()
    # The index of the correct option in the `options` list
    correct_index = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.text