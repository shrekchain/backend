from . import password, google

AUTH_SYSTEMS = {"password": password, "google": google}


def can_check_constraint(auth_system):
    return hasattr(AUTH_SYSTEMS[auth_system], "check_constraint")


def can_list_categories(auth_system):
    return hasattr(AUTH_SYSTEMS[auth_system], "list_categories")
