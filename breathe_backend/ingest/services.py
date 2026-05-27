import uuid
from decimal import Decimal
from datetime import datetime
from django.db import transaction
from .models import Tenant, DataSource, RawRow, NormRow, DataIssue, AuditTrail

EF = {
    'DIESEL': Decimal('10.18'),
    'NATURAL_GAS': Decimal('5.3'),
    'ELECTRICITY': Decimal('0.385'),
    'FLIGHT_SHORT': Decimal('0.25'),
    'FLIGHT_LONG': Decimal('0.15'),
    'HOTEL': Decimal('15.0'),
    'RAIL': Decimal('0.04'),
}

def parse_dt(ds):
    for f in ('%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y'):
        try:
            return datetime.strptime(ds.strip(), f).date()
        except:
            pass
    raise ValueError(f"Invalid date format: {ds}")

def get_dec(v, df=None):
    if v is None or str(v).strip() == '':
        if df is not None:
            return df
        raise ValueError("Missing numeric value")
    try:
        return Decimal(str(v).replace(',', '').strip())
    except:
        raise ValueError(f"Invalid numeric value: {v}")

def log_audit(t, nr, act, usr, old=None, new=None):
    AuditTrail.objects.create(
        tenant=t,
        row=nr,
        action=act,
        usr=usr,
        old_val=old,
        new_val=new
    )

def handle_issue(t, nr, code, sev, msg):
    nr.status = 'FLAGGED'
    nr.save()
    DataIssue.objects.create(
        tenant=t,
        row=nr,
        code=code,
        severity=sev,
        msg=msg
    )

class SapPipeline:
    @staticmethod
    @transaction.atomic
    def process(t, ds, rec, usr):
        rr = RawRow.objects.create(tenant=t, src=ds, payload=rec, status='PROCESSING')
        try:
            beleg = rec.get('beleg_id') or rec.get('invoice_id')
            kraftstoff = (rec.get('kraftstoff') or rec.get('fuel_type', '')).upper()
            menge_str = rec.get('menge') or rec.get('quantity')
            einheit = (rec.get('einheit') or rec.get('unit', '')).upper()
            datum_str = rec.get('datum') or rec.get('date')

            if not all([beleg, kraftstoff, menge_str, einheit, datum_str]):
                raise ValueError("Missing required fields for SAP record")

            qty = get_dec(menge_str)
            act_date = parse_dt(datum_str)

            if kraftstoff == 'DIESEL':
                scope = 'SCOPE_1'
                cat = 'mobile_combustion'
                fact = EF['DIESEL']
            elif kraftstoff in ('NATURAL_GAS', 'ERDGAS'):
                scope = 'SCOPE_1'
                cat = 'stationary_combustion'
                fact = EF['NATURAL_GAS']
                kraftstoff = 'NATURAL_GAS'
            else:
                scope = 'SCOPE_3'
                cat = 'purchased_goods_services'
                fact = Decimal('1.2')

            if einheit in ('L', 'LITER', 'LITERS') and kraftstoff == 'DIESEL':
                qty_gal = qty * Decimal('0.264172')
                norm_unit = 'GAL'
            elif einheit in ('GAL', 'GALLON', 'GALLONS'):
                qty_gal = qty
                norm_unit = 'GAL'
            elif einheit in ('THERM', 'THERMS'):
                qty_gal = qty
                norm_unit = 'THERM'
            elif einheit in ('KWH', 'METER'):
                qty_gal = qty
                norm_unit = 'KWH'
            else:
                qty_gal = qty
                norm_unit = einheit

            norm_val = qty_gal * fact

            nr = NormRow.objects.create(
                tenant=t,
                raw=rr,
                src=ds,
                scope=scope,
                category=cat,
                raw_val=qty,
                raw_unit=einheit,
                norm_val=norm_val,
                norm_unit='kgCO2e',
                em_factor=fact,
                act_date=act_date,
                status='PENDING'
            )

            if qty < 0:
                handle_issue(t, nr, 'NEGATIVE_VALUE', 'ERROR', "Fuel quantity cannot be negative")
            if kraftstoff == 'DIESEL' and qty_gal > 10000:
                handle_issue(t, nr, 'SUSPICIOUS_SPIKE', 'WARNING', "Fuel purchase exceeds 10,000 Gallons")
            if norm_unit not in ('GAL', 'THERM'):
                handle_issue(t, nr, 'UNSUPPORTED_UNIT', 'WARNING', f"Non-standard SAP fuel unit: {einheit}")

            rr.status = 'SUCCESS'
            rr.save()
            log_audit(t, nr, 'CREATE', usr, new={'id': str(nr.id), 'val': float(norm_val)})
            return nr

        except Exception as e:
            rr.status = 'FAILED'
            rr.err = str(e)
            rr.save()
            raise e

class UtilityPipeline:
    @staticmethod
    @transaction.atomic
    def process(t, ds, rec, usr):
        rr = RawRow.objects.create(tenant=t, src=ds, payload=rec, status='PROCESSING')
        try:
            acc = rec.get('account') or rec.get('account_number')
            meter = rec.get('meter') or rec.get('meter_number')
            start = rec.get('start_date') or rec.get('billing_start_date')
            end = rec.get('end_date') or rec.get('billing_end_date')
            usage = rec.get('usage_kwh') or rec.get('usage')
            unit = (rec.get('unit') or 'KWH').upper()

            if not all([acc, meter, start, end, usage]):
                raise ValueError("Missing required fields for Utility record")

            qty = get_dec(usage)
            d_start = parse_dt(start)
            d_end = parse_dt(end)

            if d_end <= d_start:
                raise ValueError("Billing end date must be after start date")

            qty_kwh = qty
            if unit in ('MWH', 'MEGAWATT_HOURS'):
                qty_kwh = qty * Decimal('1000')
            elif unit not in ('KWH', 'KILOWATT_HOURS'):
                qty_kwh = qty

            fact = EF['ELECTRICITY']
            norm_val = qty_kwh * fact

            nr = NormRow.objects.create(
                tenant=t,
                raw=rr,
                src=ds,
                scope='SCOPE_2',
                category='purchased_electricity',
                raw_val=qty,
                raw_unit=unit,
                norm_val=norm_val,
                norm_unit='kgCO2e',
                em_factor=fact,
                act_date=d_end,
                status='PENDING'
            )

            days = (d_end - d_start).days
            if days > 45:
                handle_issue(t, nr, 'BILLING_PERIOD_SPIKE', 'WARNING', f"Billing period is unusually long ({days} days)")
            if qty < 0:
                handle_issue(t, nr, 'NEGATIVE_VALUE', 'ERROR', "Electricity usage cannot be negative")
            if qty_kwh > 50000:
                handle_issue(t, nr, 'SUSPICIOUS_SPIKE', 'WARNING', "Monthly electricity usage exceeds 50,000 kWh")
            if unit not in ('KWH', 'MWH'):
                handle_issue(t, nr, 'UNSUPPORTED_UNIT', 'WARNING', f"Non-standard utility unit: {unit}")

            rr.status = 'SUCCESS'
            rr.save()
            log_audit(t, nr, 'CREATE', usr, new={'id': str(nr.id), 'val': float(norm_val)})
            return nr

        except Exception as e:
            rr.status = 'FAILED'
            rr.err = str(e)
            rr.save()
            raise e

class NavanPipeline:
    @staticmethod
    @transaction.atomic
    def process(t, ds, rec, usr):
        rr = RawRow.objects.create(tenant=t, src=ds, payload=rec, status='PROCESSING')
        try:
            bid = rec.get('booking_id')
            ttype = (rec.get('travel_type') or rec.get('type', '')).upper()
            date_str = rec.get('booking_date') or rec.get('date')

            if not all([bid, ttype, date_str]):
                raise ValueError("Missing required fields for Navan record")

            act_date = parse_dt(date_str)
            qty = Decimal('0')
            raw_unit = 'N/A'
            fact = Decimal('0')
            cat = 'business_travel'

            if ttype == 'FLIGHT':
                dist = get_dec(rec.get('distance_km') or rec.get('distance'), 0)
                raw_unit = 'KM'
                qty = dist
                fact = EF['FLIGHT_LONG'] if dist >= 500 else EF['FLIGHT_SHORT']
                norm_val = dist * fact
            elif ttype == 'HOTEL':
                nights = get_dec(rec.get('hotel_nights') or rec.get('nights'), 0)
                raw_unit = 'NIGHTS'
                qty = nights
                fact = EF['HOTEL']
                norm_val = nights * fact
            elif ttype == 'RAIL':
                dist = get_dec(rec.get('distance_km') or rec.get('distance'), 0)
                raw_unit = 'KM'
                qty = dist
                fact = EF['RAIL']
                norm_val = dist * fact
            else:
                qty = get_dec(rec.get('quantity') or rec.get('amount'), 1)
                raw_unit = rec.get('unit') or 'UNIT'
                fact = Decimal('0.1')
                norm_val = qty * fact

            nr = NormRow.objects.create(
                tenant=t,
                raw=rr,
                src=ds,
                scope='SCOPE_3',
                category=cat,
                raw_val=qty,
                raw_unit=raw_unit,
                norm_val=norm_val,
                norm_unit='kgCO2e',
                em_factor=fact,
                act_date=act_date,
                status='PENDING'
            )

            if qty < 0:
                handle_issue(t, nr, 'NEGATIVE_VALUE', 'ERROR', f"Navan {ttype} quantity cannot be negative")
            if ttype == 'FLIGHT' and qty > 15000:
                handle_issue(t, nr, 'SUSPICIOUS_SPIKE', 'WARNING', "Flight distance exceeds 15,000 km")
            elif ttype == 'HOTEL' and qty > 30:
                handle_issue(t, nr, 'SUSPICIOUS_SPIKE', 'WARNING', "Hotel stay exceeds 30 nights")

            rr.status = 'SUCCESS'
            rr.save()
            log_audit(t, nr, 'CREATE', usr, new={'id': str(nr.id), 'val': float(norm_val)})
            return nr

        except Exception as e:
            rr.status = 'FAILED'
            rr.err = str(e)
            rr.save()
            raise e
