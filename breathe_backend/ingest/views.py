from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Tenant, DataSource, RawRow, NormRow, DataIssue, AuditTrail
from .services import SapPipeline, UtilityPipeline, NavanPipeline, log_audit

def res_t(req):
    tid = req.headers.get('X-Tenant-ID')
    if tid:
        return Tenant.objects.get(id=tid)
    t, _ = Tenant.objects.get_or_create(slug='default-tenant', defaults={'name': 'Default Tenant'})
    return t

def res_u(req):
    if req.user and req.user.is_authenticated:
        return req.user
    u, _ = User.objects.get_or_create(username='system_analyst', defaults={'is_staff': True})
    return u

def get_src(t, name, stype):
    ds, _ = DataSource.objects.get_or_create(tenant=t, src_type=stype, defaults={'name': name})
    return ds

@api_view(['POST'])
def ingest_sap(req):
    t = res_t(req)
    u = res_u(req)
    ds = get_source=get_src(t, 'SAP Fuel Import', 'SAP')
    recs = req.data if isinstance(req.data, list) else [req.data]
    res_list = []
    for r in recs:
        try:
            nr = SapPipeline.process(t, ds, r, u)
            res_list.append({'id': str(nr.id), 'status': nr.status, 'emissions': float(nr.norm_val)})
        except Exception as e:
            res_list.append({'error': str(e), 'payload': r})
    return Response({'processed': len(recs), 'results': res_list}, status=status.HTTP_200_OK)

@api_view(['POST'])
def ingest_utility(req):
    t = res_t(req)
    u = res_u(req)
    ds = get_src(t, 'Utility Meter Import', 'UTILITY')
    recs = req.data if isinstance(req.data, list) else [req.data]
    res_list = []
    for r in recs:
        try:
            nr = UtilityPipeline.process(t, ds, r, u)
            res_list.append({'id': str(nr.id), 'status': nr.status, 'emissions': float(nr.norm_val)})
        except Exception as e:
            res_list.append({'error': str(e), 'payload': r})
    return Response({'processed': len(recs), 'results': res_list}, status=status.HTTP_200_OK)

@api_view(['POST'])
def ingest_navan(req):
    t = res_t(req)
    u = res_u(req)
    ds = get_src(t, 'Navan API Import', 'NAVAN')
    recs = req.data if isinstance(req.data, list) else [req.data]
    res_list = []
    for r in recs:
        try:
            nr = NavanPipeline.process(t, ds, r, u)
            res_list.append({'id': str(nr.id), 'status': nr.status, 'emissions': float(nr.norm_val)})
        except Exception as e:
            res_list.append({'error': str(e), 'payload': r})
    return Response({'processed': len(recs), 'results': res_list}, status=status.HTTP_200_OK)

@api_view(['GET'])
def list_normalized(req):
    t = res_t(req)
    rows = NormRow.objects.filter(tenant=t).order_index=NormRow.objects.filter(tenant=t).order_by('-created_at')
    res_data = []
    for r in rows:
        issues = [{'code': i.code, 'severity': i.severity, 'msg': i.msg} for i in r.issues.all()]
        audit_logs = [{'action': a.action, 'usr': a.usr.username, 'tstamp': a.tstamp.isoformat()} for a in r.audit_logs.all()]
        res_data.append({
            'id': str(r.id),
            'source': r.src.name,
            'source_type': r.src.src_type,
            'scope': r.scope,
            'category': r.category,
            'raw_val': float(r.raw_val),
            'raw_unit': r.raw_unit,
            'norm_val': float(r.norm_val),
            'norm_unit': r.norm_unit,
            'em_factor': float(r.em_factor) if r.em_factor else None,
            'act_date': r.act_date.isoformat(),
            'status': r.status,
            'audited_at': r.audited_at.isoformat() if r.audited_at else None,
            'issues': issues,
            'audit': audit_logs
        })
    return Response(res_data, status=status.HTTP_200_OK)

@api_view(['POST'])
def approve_row(req, pk):
    t = res_t(req)
    u = res_u(req)
    nr = get_object_or_404(NormRow, id=pk, tenant=t)
    if nr.status == 'AUDITED':
        return Response({'error': 'Row is already locked and audited'}, status=status.HTTP_400_BAD_REQUEST)
    old_status = nr.status
    nr.status = 'APPROVED'
    nr.save()
    log_audit(t, nr, 'APPROVE', u, old={'status': old_status}, new={'status': 'APPROVED'})
    return Response({'id': str(nr.id), 'status': nr.status}, status=status.HTTP_200_OK)

@api_view(['POST'])
def flag_row(req, pk):
    t = res_t(req)
    u = res_u(req)
    nr = get_object_or_404(NormRow, id=pk, tenant=t)
    if nr.status == 'AUDITED':
        return Response({'error': 'Row is already locked and audited'}, status=status.HTTP_400_BAD_REQUEST)
    code = req.data.get('code', 'ANALYST_FLAG')
    msg = req.data.get('msg', 'Flagged by analyst for manual review')
    old_status = nr.status
    nr.status = 'FLAGGED'
    nr.save()
    DataIssue.objects.create(tenant=t, row=nr, code=code, severity='WARNING', msg=msg)
    log_audit(t, nr, 'FLAG', u, old={'status': old_status}, new={'status': 'FLAGGED', 'issue_code': code, 'issue_msg': msg})
    return Response({'id': str(nr.id), 'status': nr.status}, status=status.HTTP_200_OK)

@api_view(['POST'])
def lock_row(req, pk):
    t = res_t(req)
    u = res_u(req)
    nr = get_object_or_404(NormRow, id=pk, tenant=t)
    if nr.status == 'AUDITED':
        return Response({'error': 'Row is already audited'}, status=status.HTTP_400_BAD_REQUEST)
    old_status = nr.status
    nr.status = 'AUDITED'
    nr.audited_by = u
    nr.audited_at = timezone.now()
    nr.save()
    log_audit(t, nr, 'LOCK', u, old={'status': old_status}, new={'status': 'AUDITED'})
    return Response({'id': str(nr.id), 'status': nr.status}, status=status.HTTP_200_OK)

@api_view(['PATCH'])
def edit_row(req, pk):
    t = res_t(req)
    u = res_u(req)
    nr = get_object_or_404(NormRow, id=pk, tenant=t)
    if nr.status == 'AUDITED':
        return Response({'error': 'Row is already locked and audited'}, status=status.HTTP_400_BAD_REQUEST)
    
    old_val = float(nr.raw_val)
    old_unit = nr.raw_unit
    
    new_val_str = req.data.get('raw_val')
    new_unit = req.data.get('raw_unit')
    
    if new_val_str is not None:
        nr.raw_val = Decimal(str(new_val_str))
    if new_unit is not None:
        nr.raw_unit = str(new_unit)
        
    nr.norm_val = nr.raw_val * (nr.em_factor or Decimal('1.0'))
    nr.save()
    
    log_audit(t, nr, 'EDIT', u, 
              old={'raw_val': old_val, 'raw_unit': old_unit}, 
              new={'raw_val': float(nr.raw_val), 'raw_unit': nr.raw_unit, 'norm_val': float(nr.norm_val)})
              
    return Response({'id': str(nr.id), 'raw_val': float(nr.raw_val), 'norm_val': float(nr.norm_val)}, status=status.HTTP_200_OK)

@api_view(['GET'])
def health_check(req):
    try:
        Tenant.objects.exists()
        return Response({'status': 'healthy', 'db': 'connected'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'status': 'unhealthy', 'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
