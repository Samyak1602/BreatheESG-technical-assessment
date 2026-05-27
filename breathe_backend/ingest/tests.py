from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework import status
from .models import Tenant, DataSource, RawRow, NormRow, DataIssue

class PipelineTests(TestCase):
    def setUp(self):
        self.cl = APIClient()
        self.t = Tenant.objects.create(name='Test Tenant', slug='test-tenant')
        self.usr = User.objects.create(username='system_analyst', is_staff=True)
        self.ds_sap = DataSource.objects.create(tenant=self.t, name='SAP Import', src_type='SAP')
        self.ds_ut = DataSource.objects.create(tenant=self.t, name='Utility Import', src_type='UTILITY')
        self.ds_nv = DataSource.objects.create(tenant=self.t, name='Navan Import', src_type='NAVAN')
        self.h = {'HTTP_X_TENANT_ID': str(self.t.id)}

    def test_sap_pipeline(self):
        p1 = {'invoice_id': 'SAP-101', 'fuel_type': 'diesel', 'quantity': '100', 'unit': 'gal', 'date': '2026-05-27'}
        res = self.cl.post('/api/ingest/sap/', p1, format='json', **self.h)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(NormRow.objects.count(), 1)
        nr = NormRow.objects.first()
        self.assertEqual(nr.scope, 'SCOPE_1')
        self.assertEqual(float(nr.norm_val), 100 * float(nr.em_factor))
        self.assertEqual(nr.issues.count(), 0)

        p2 = {'invoice_id': 'SAP-102', 'fuel_type': 'diesel', 'quantity': '15000', 'unit': 'gal', 'date': '2026-05-27'}
        res = self.cl.post('/api/ingest/sap/', p2, format='json', **self.h)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(NormRow.objects.count(), 2)
        nr2 = NormRow.objects.order_by('created_at').last()
        self.assertEqual(nr2.status, 'FLAGGED')
        self.assertEqual(nr2.issues.filter(code='SUSPICIOUS_SPIKE').count(), 1)

    def test_utility_pipeline(self):
        p1 = {'account': 'UT-888', 'meter': 'M-001', 'start_date': '2026-04-01', 'end_date': '2026-04-30', 'usage_kwh': '500', 'unit': 'kwh'}
        res = self.cl.post('/api/ingest/utility/', p1, format='json', **self.h)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        nr = NormRow.objects.first()
        self.assertEqual(nr.scope, 'SCOPE_2')
        self.assertEqual(nr.category, 'purchased_electricity')
        self.assertEqual(float(nr.norm_val), 500 * float(nr.em_factor))

        p2 = {'account': 'UT-888', 'meter': 'M-001', 'start_date': '2026-04-01', 'end_date': '2026-04-30', 'usage_kwh': '-10', 'unit': 'kwh'}
        res = self.cl.post('/api/ingest/utility/', p2, format='json', **self.h)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        nr2 = NormRow.objects.order_by('created_at').last()
        self.assertEqual(nr2.status, 'FLAGGED')
        self.assertEqual(nr2.issues.filter(code='NEGATIVE_VALUE').count(), 1)

    def test_navan_pipeline(self):
        p1 = {'booking_id': 'NAV-999', 'travel_type': 'flight', 'distance_km': '800', 'date': '2026-05-27'}
        res = self.cl.post('/api/ingest/navan/', p1, format='json', **self.h)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        nr = NormRow.objects.first()
        self.assertEqual(nr.scope, 'SCOPE_3')
        self.assertEqual(float(nr.em_factor), 0.15)
        self.assertEqual(float(nr.norm_val), 800 * 0.15)

