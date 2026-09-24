#!/usr/bin/env bash
# ============================================================
# KLK v2.0 PATCH — Run this to apply all fixes and restart
# ============================================================
set -e
cd "$(dirname "$0")"

echo "🔧 KLK Management System — Applying patches..."
echo ""

# Activate virtualenv if present
[ -d "venv" ] && source venv/bin/activate

# Run fresh migrations (models were updated)
echo "📦 Running migrations..."
python manage.py makemigrations --no-input 2>&1 || true
python manage.py migrate --no-input

# Re-seed data (idempotent)
echo "🌍 Refreshing seed data..."
python manage.py shell -c "
from beneficiaries.models import County
counties = [
  ('Mombasa','KE001'),('Kwale','KE002'),('Kilifi','KE003'),('Tana River','KE004'),('Lamu','KE005'),
  ('Taita Taveta','KE006'),('Garissa','KE007'),('Wajir','KE008'),('Mandera','KE009'),('Marsabit','KE010'),
  ('Isiolo','KE011'),('Meru','KE012'),('Tharaka Nithi','KE013'),('Embu','KE014'),('Kitui','KE015'),
  ('Machakos','KE016'),('Makueni','KE017'),('Nyandarua','KE018'),('Nyeri','KE019'),('Kirinyaga','KE020'),
  ('Muranga','KE021'),('Kiambu','KE022'),('Turkana','KE023'),('West Pokot','KE024'),('Samburu','KE025'),
  ('Trans Nzoia','KE026'),('Uasin Gishu','KE027'),('Elgeyo Marakwet','KE028'),('Nandi','KE029'),
  ('Baringo','KE030'),('Laikipia','KE031'),('Nakuru','KE032'),('Narok','KE033'),('Kajiado','KE034'),
  ('Kericho','KE035'),('Bomet','KE036'),('Kakamega','KE037'),('Vihiga','KE038'),('Bungoma','KE039'),
  ('Busia','KE040'),('Siaya','KE041'),('Kisumu','KE042'),('Homa Bay','KE043'),('Migori','KE044'),
  ('Kisii','KE045'),('Nyamira','KE046'),('Nairobi','KE047')
]
created = 0
for name, code in counties:
    _, c = County.objects.get_or_create(code=code, defaults={'name': name})
    if c: created += 1
print(f'  ✅ {County.objects.count()} counties ({created} new)')

import datetime
from academics.models import AcademicYear
for y in [2022,2023,2024,2025,2026]:
    AcademicYear.objects.get_or_create(year=str(y), defaults={
        'start_date': datetime.date(y,1,15),
        'end_date': datetime.date(y,11,15),
        'is_current': y==2025
    })
print(f'  ✅ {AcademicYear.objects.count()} academic years')

from finance.models import BudgetCategory
for cat in ['School Fees','Uniform & Supplies','Transport','Medical','Extra Tuition','University Fees','Living Allowance','Stationery']:
    BudgetCategory.objects.get_or_create(name=cat)
print(f'  ✅ {BudgetCategory.objects.count()} budget categories')

from users.models import User
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin','admin@klk.org','klk2024admin',role='admin',first_name='System',last_name='Admin')
    print('  ✅ Admin user created: admin / klk2024admin')
else:
    print('  ℹ️  Admin user already exists')
"

echo ""
echo "✅ Patch applied successfully!"
echo ""
echo "🚀 Start backend:   python manage.py runserver"
echo "🔑 Login:           admin / klk2024admin"
echo "🌐 Admin panel:     http://localhost:8000/admin"
echo "📡 API root:        http://localhost:8000/api/"
