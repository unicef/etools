c = Country.objects.get(name='UAT')
u, _ = User.objects.get_or_create(username='puli', first_name='Puli', last_name='Lab')
u.country = c
u.is_superuser = True
u.is_staff = True
u.set_password('lab')
u.save()
p = u.profile
p.country = c
p.save()
g = Group.objects.get(name='UNICEF User')
u.groups.add(g)
