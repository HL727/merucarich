from django.core.management.utils import get_random_secret_key

print("SECRET_KEY = '{}'".format(get_random_secret_key()))

localdb = dict(host='localhost', user='root', password='rootroot', port='3306')
dbstr = ', '.join([ "'{}': '{}'".format(k, v) for (k, v) in localdb.items() ])
print("LOCAL_DATABASE = {{{}}}".format(dbstr))

