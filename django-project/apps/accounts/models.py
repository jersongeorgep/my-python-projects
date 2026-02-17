from django.db import models
from django.conf import settings

class Account(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    ACCOUNT_TYPE = [('asset','Asset'),('liability','Liability'),('income','Income'),('expense','Expense')]
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPE)

    def __str__(self):
        return f"{self.code} - {self.name}"

class JournalEntry(models.Model):
    date = models.DateField()
    narration = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    posted = models.BooleanField(default=False)

class JournalLine(models.Model):
    journal = models.ForeignKey(JournalEntry, related_name='lines', on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    debit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=14, decimal_places=2, default=0)