# Intentionally vulnerable fixture for security-review evals. Do not deploy.
from django.http import JsonResponse
from django.db import connection


def user_search(request):
    q = request.GET.get("q", "")
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT id, email FROM auth_user WHERE email LIKE '%{q}%'")
        rows = cursor.fetchall()
    return JsonResponse({"users": rows})
