"""Django REST Framework version of the bug and the fix.

Runs without a server: it validates the same request body with two
ModelSerializers and prints what each one would save.

    python serializers_demo.py
"""
import django
from django.conf import settings

settings.configure(
    INSTALLED_APPS=["django.contrib.contenttypes", "rest_framework"],
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}},
)
django.setup()

from django.db import connection, models  # noqa: E402
from rest_framework import serializers  # noqa: E402


class Account(models.Model):
    email = models.EmailField()
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, default="customer")
    store_credit = models.IntegerField(default=0)

    class Meta:
        app_label = "bookstore"


# Vulnerable: every model field is writable
class AccountSerializerAll(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = "__all__"


# Fixed: an explicit allow-list, sensitive fields are read-only
class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = ["id", "email", "name", "role", "store_credit"]
        read_only_fields = ["role", "store_credit"]


with connection.schema_editor() as editor:
    editor.create_model(Account)

body = {"email": "mallory@example.com", "name": "Mallory", "role": "admin", "store_credit": 500}

for serializer_class in (AccountSerializerAll, AccountSerializer):
    s = serializer_class(data=body)
    s.is_valid(raise_exception=True)
    account = s.save()
    print(f"{serializer_class.__name__:22} saved role={account.role!r} store_credit={account.store_credit}")
