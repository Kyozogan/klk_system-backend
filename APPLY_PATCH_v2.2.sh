#!/usr/bin/env bash
# KLK v2.2 — Apply changes
set -e
cd "$(dirname "$0")"
echo "🏆 KLK v2.2 — Applying patch…"

source venv/bin/activate 2>/dev/null || true

python manage.py makemigrations --no-input 2>&1 | grep -v "^$" | head -20
python manage.py migrate --no-input

python manage.py shell -c "
# Seed / update data
from beneficiaries.models import County
counties=[('Mombasa','KE001'),('Kwale','KE002'),('Kilifi','KE003'),('Tana River','KE004'),('Lamu','KE005'),('Taita Taveta','KE006'),('Garissa','KE007'),('Wajir','KE008'),('Mandera','KE009'),('Marsabit','KE010'),('Isiolo','KE011'),('Meru','KE012'),('Tharaka Nithi','KE013'),('Embu','KE014'),('Kitui','KE015'),('Machakos','KE016'),('Makueni','KE017'),('Nyandarua','KE018'),('Nyeri','KE019'),('Kirinyaga','KE020'),('Muranga','KE021'),('Kiambu','KE022'),('Turkana','KE023'),('West Pokot','KE024'),('Samburu','KE025'),('Trans Nzoia','KE026'),('Uasin Gishu','KE027'),('Elgeyo Marakwet','KE028'),('Nandi','KE029'),('Baringo','KE030'),('Laikipia','KE031'),('Nakuru','KE032'),('Narok','KE033'),('Kajiado','KE034'),('Kericho','KE035'),('Bomet','KE036'),('Kakamega','KE037'),('Vihiga','KE038'),('Bungoma','KE039'),('Busia','KE040'),('Siaya','KE041'),('Kisumu','KE042'),('Homa Bay','KE043'),('Migori','KE044'),('Kisii','KE045'),('Nyamira','KE046'),('Nairobi','KE047')]
for name,code in counties:
    County.objects.get_or_create(code=code,defaults={'name':name})
print(f'  Counties: {County.objects.count()}')

import datetime
from academics.models import AcademicYear
for y in [2022,2023,2024,2025,2026]:
    AcademicYear.objects.get_or_create(year=str(y),defaults={'start_date':datetime.date(y,1,15),'end_date':datetime.date(y,11,15),'is_current':y==2025})

from finance.models import BudgetCategory
for cat in ['School Fees','Uniform & Supplies','Transport','Medical','Extra Tuition','University Fees','Living Allowance','Stationery','Exam Fees']:
    BudgetCategory.objects.get_or_create(name=cat)

from users.models import User
if not User.objects.filter(username='admin').exists():
    u=User.objects.create_superuser('admin','admin@klk.org','klk2024admin',role='admin',first_name='System',last_name='Admin')
    u.portal='admin'; u.account_status='approved'; u.save()
    print('  Admin created: admin / klk2024admin')
else:
    u=User.objects.get(username='admin')
    u.portal='admin'; u.account_status='approved'; u.role='admin'; u.save()
    print('  Admin updated: admin / klk2024admin')
"

echo ""
echo "✅ Patch v2.2 applied!"
echo ""
echo "🔑 Admin portal:   http://localhost:5173/login   (admin / klk2024admin)"
echo "🎓 Scholar portal: http://localhost:5173/portal"
echo "🌐 Django admin:   http://localhost:8000/admin"
echo ""
echo "🚀 python manage.py runserver"
