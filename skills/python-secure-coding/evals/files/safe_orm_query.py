# Safe control fixture: parameterized ORM query. Review should not flag SQL injection.
from django.contrib.auth import get_user_model

User = get_user_model()


def user_search(q: str):
    return list(User.objects.filter(email__icontains=q).values_list("id", "email"))
