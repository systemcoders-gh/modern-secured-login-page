from django.conf import settings


def brand(request):
    return {"is_local_demo": not settings.PRODUCTION, "app_name": "Modern Secured Login Page"}
