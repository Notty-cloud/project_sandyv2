from rest_framework.permissions import BasePermission


class RoleLevelPermission(BasePermission):
    message = 'You do not have permission to access this resource.'

    def has_permission(self, request, view):
        admin = getattr(request, 'user', None)
        if not admin or not getattr(admin, 'is_authenticated', False):
            self.message = 'Authentication required.'
            return False

        required_roles = set(getattr(view, 'required_roles', []))
        minimum_authorization_level = getattr(view, 'minimum_authorization_level', 1)

        if required_roles and admin.role not in required_roles:
            self.message = 'Your role does not grant access to this route.'
            return False

        if admin.authorization_level < minimum_authorization_level:
            self.message = f'Authorization level {minimum_authorization_level}+ required.'
            return False

        return True