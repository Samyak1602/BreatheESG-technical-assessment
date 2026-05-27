import uuid
from django.db import models
from django.contrib.auth.models import User

class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

class DataSource(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    src_type = models.CharField(max_length=50)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

class RawRow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    src = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    payload = models.JSONField()
    status = models.CharField(max_length=20, default='PENDING')
    err = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class NormRow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    raw = models.OneToOneField(RawRow, on_delete=models.SET_NULL, null=True, blank=True)
    src = models.ForeignKey(DataSource, on_delete=models.CASCADE)
    scope = models.CharField(max_length=10)
    category = models.CharField(max_length=100)
    raw_val = models.DecimalField(max_digits=18, decimal_places=6)
    raw_unit = models.CharField(max_length=50)
    norm_val = models.DecimalField(max_digits=18, decimal_places=6)
    norm_unit = models.CharField(max_length=10, default='kgCO2e')
    em_factor = models.DecimalField(max_digits=12, decimal_places=6, null=True, blank=True)
    act_date = models.DateField()
    status = models.CharField(max_length=20, default='PENDING')
    audited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    audited_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class DataIssue(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    row = models.ForeignKey(NormRow, on_delete=models.CASCADE, related_name='issues')
    code = models.CharField(max_length=50)
    severity = models.CharField(max_length=10, default='WARNING')
    msg = models.TextField()
    resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class AuditTrail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    row = models.ForeignKey(NormRow, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action = models.CharField(max_length=20)
    usr = models.ForeignKey(User, on_delete=models.PROTECT)
    old_val = models.JSONField(null=True, blank=True)
    new_val = models.JSONField(null=True, blank=True)
    tstamp = models.DateTimeField(auto_now_add=True)

