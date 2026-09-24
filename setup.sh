#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "🏆 KLK Management System — Setup"
echo "================================="

[ -d "venv" ] || python3 -m venv venv
source venv/bin/activate

pip install -q -r requirements.txt

cp -n .env.example .env 2>/dev/null || true

python manage.py makemigrations --no-input 2>&1 | grep -v "^$" | head -20
python manage.py migrate --no-input

python manage.py shell -c "
from beneficiaries.models import County
counties = [('Mombasa','KE001'),('Kwale','KE002'),('Kilifi','KE003'),('Tana River','KE004'),('Lamu','KE005'),('Garissa','KE007'),('Nairobi','KE047'),('Kisumu','KE042'),('Nakuru','KE032'),('Meru','KE012'),('Machakos','KE016'),('Nyeri','KE019'),('Kakamega','KE037'),('Uasin Gishu','KE027'),('Bungoma','KE039'),('Kiambu','KE022'),('Murang a','KE021'),('Embu','KE014'),('Kirinyaga','KE020'),('Nyandarua','KE018'),('Laikipia','KE031'),('Samburu','KE025'),('Turkana','KE023'),('West Pokot','KE024'),('Trans Nzoia','KE026'),('Nandi','KE029'),('Baringo','KE030'),('Elgeyo Marakwet','KE028'),('Kericho','KE035'),('Bomet','KE036'),('Narok','KE033'),('Kajiado','KE034'),('Vihiga','KE038'),('Busia','KE040'),('Siaya','KE041'),('Homa Bay','KE043'),('Migori','KE044'),('Kisii','KE045'),('Nyamira','KE046'),('Isiolo','KE011'),('Marsabit','KE010'),('Mandera','KE009'),('Wajir','KE008'),('Tharaka Nithi','KE013'),('Kitui','KE015'),('Makueni','KE017'),('Taita Taveta','KE006')]
for name, code in counties:
    County.objects.get_or_create(code=code, defaults={'name': name})
print(f'  Counties: {County.objects.count()}')

import datetime
from academics.models import AcademicYear
for y in [2022,2023,2024,2025,2026]:
    AcademicYear.objects.get_or_create(year=str(y), defaults={'start_date':datetime.date(y,1,15),'end_date':datetime.date(y,11,15),'is_current': y==2025})
print(f'  Academic years: {AcademicYear.objects.count()}')

from finance.models import BudgetCategory
for cat in ['School Fees','Uniform & Supplies','Transport','Medical','Extra Tuition','University Fees','Living Allowance','Stationery','Exam Fees']:
    BudgetCategory.objects.get_or_create(name=cat)

from users.models import User
if not User.objects.filter(username='admin').exists():
    u = User.objects.create_superuser('admin','admin@klk.org','klk2024admin',role='admin',first_name='System',last_name='Admin')
    u.portal = 'admin'
    u.account_status = 'approved'
    u.save()
    print('  Admin: admin / klk2024admin')
else:
    print('  Admin user exists')
"

echo ""
echo "✅ Setup complete!"
echo "   python manage.py runserver"
echo "   Login: admin / klk2024admin"
