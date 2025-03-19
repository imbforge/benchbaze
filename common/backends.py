from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import AnonymousUser, Group
from django.contrib.auth.signals import user_login_failed
from django.core.mail import mail_admins, send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from mozilla_django_oidc.auth import OIDCAuthenticationBackend

User = get_user_model()
OIDC_ALLOWED_GROUPS = getattr(settings, "OIDC_ALLOWED_GROUPS", [])
OIDC_ALLOWED_USER_EMAILS = getattr(settings, "OIDC_ALLOWED_USER_EMAILS", [])
SITE_TITLE = getattr(settings, "SITE_TITLE", "Lab DB")
SITE_ADMIN_EMAIL_ADDRESSES = getattr(settings, "SITE_ADMIN_EMAIL_ADDRESSES", [])
OIDC_UPN_FIELD_NAME = getattr(settings, "OIDC_UPN_FIELD_NAME", "upn")
OIDC_PROVIDER_NAME = getattr(settings, "OIDC_PROVIDER_NAME", "")
ALLOWED_HOSTS = getattr(settings, "ALLOWED_HOSTS", [])

User = get_user_model()


class CaseInsensitiveAuthenticationBackend(ModelBackend):
    """
    Custom authentication that is case insensitive for User.USERNAME_FIELD
    Modified from https://stackoverflow.com/questions/70713647
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return
        try:
            user = User._default_manager.get(
                **{f"{User.USERNAME_FIELD}__iexact": username}
            )
        except User.DoesNotExist:
            User().set_password(password)
            return
        if user.check_password(password) and self.user_can_authenticate(user):
            return user


class OwnOIDCAuthenticationBackend(OIDCAuthenticationBackend):
    def user_belongs_to_groups(self, user_groups, groups):
        """Check if any group assigned to a user, -> user_groups, is found
        in a list of groups, -> groups, which should be a str of comma
        separated group names"""

        return any(g in user_groups for g in groups)

    def get_or_create_user(self, access_token, id_token, payload):
        # Check whether user is allowed to log in, if not return
        # AnonymousUser. Easier to do it here than in verify_claims
        # because we need to return a user that can be recognized in
        # authenticate
        user_info = self.get_userinfo(access_token, id_token, payload)
        user_email = user_info.get("email", "").lower()
        user_groups = user_info.get("role", [])
        if not (
            self.user_belongs_to_groups(user_groups, OIDC_ALLOWED_GROUPS)
            or user_email in OIDC_ALLOWED_USER_EMAILS
        ):
            messages.warning(
                self.request,
                f"Your user is valid but not yet allowed to access the {SITE_TITLE}.",
            )
            user = AnonymousUser()
            user.email = user_email
            return user

        return super().get_or_create_user(access_token, id_token, payload)

    def filter_users_by_claims(self, claims):
        oidc_id = claims.get("sub")

        # If a unique identifier (= sub) is available use it to try getting the User
        # sub should match the oidc_id field for user
        if oidc_id:
            users = self.UserModel.objects.filter(oidc_id=oidc_id)
            if users:
                return users

        # Otherwise try with upn
        username = self.get_username(claims)
        if username:
            try:
                users = self.UserModel.objects.filter(username=username)
                if len(users) == 0:
                    raise Exception
                return users
            except Exception:
                # If everything fails, try the regular filter_users_by_claims
                return super().filter_users_by_claims(claims)

        return self.UserModel.objects.none()

    def send_email_new_user(self, user):
        """Send an email to the lab managers and the site admin when a new user is created
        automatically via the OIDC backend"""

        # URL for the change page of the newly created users
        user_admin_change_url = self.request.build_absolute_uri(
            reverse("admin:common_user_change", args=(user.id,))
        )
        message = render_to_string(
            "admin/common/send_email_new_user.txt",
            {
                "user": user,
                "url": user_admin_change_url,
                "provider": OIDC_PROVIDER_NAME,
                "site_title": SITE_TITLE,
            },
        )

        # Recipient list, all lab managers plus the site admin
        recipients = User.objects.filter(
            is_active=True,
            is_superuser=False,
            is_pi=False,
            groups__name="Lab manager",
        ).values_list("first_name", "email")
        recipients = list(recipients) + SITE_ADMIN_EMAIL_ADDRESSES

        try:
            send_mail(
                "A new user was just automatically created",
                message,
                None,
                [e[1] for e in recipients],
                fail_silently=False,
            )
        except Exception:
            mail_admins(
                "Error sending email about new user creation",
                message,
                fail_silently=True,
            )

    def create_user(self, claims):
        """Return object for a newly created user account."""

        # Get relevant claims, if available
        email = claims.get("email", "")
        first_name = claims.get("given_name", "")
        last_name = claims.get("family_name", "")
        oidc_id = claims.get("sub")

        # Create username
        username = self.get_username(claims)

        # Create user and update the corresponding user's identifier
        # with the value of sub
        user = self.UserModel.objects.create_user(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            oidc_id=oidc_id if oidc_id else None,
        )
        # Do not allow user to reset password
        user.set_unusable_password()
        user.save()

        # A user must have at least one group. Therefore assign
        # the group with the fewest permissions, Guest, to the user
        guest_group = Group.objects.filter(name="Guest")
        user.groups.add(*guest_group)

        self.send_email_new_user(user)

        return user

    def update_user(self, user, claims):
        """Update existing user with new claims, if necessary save, and return user"""

        # Get relevant claims, if available
        email = claims.get("email", "")
        first_name = claims.get("given_name", "")
        last_name = claims.get("family_name", "")
        oidc_id = claims.get("sub")

        # Update fields
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.set_unusable_password()  # Set password to unusable, just in case
        user.save()

        if not user.oidc_id and oidc_id:
            user.oidc_id = oidc_id
            user.save()

        return user

    def get_username(self, claims):
        """Generate username based on claims."""

        # Get username from upn => e.g. 'username@Uni-Mainz.De', default to regular
        # behaviour when upn is not available
        upn = claims.get(OIDC_UPN_FIELD_NAME)
        username = upn.split("@")[0].lower()
        if username:
            return username

        return super().get_username(claims)

    def authenticate(self, request, **kwargs):
        user = super().authenticate(request, **kwargs)

        # if user is AnonymousUser, assume that it means that the
        # upstream user trying to log in is not allowed to do so, thus
        # fire user_login_failed. AnonymousUser cannot be logged in
        # because is_active is set to False
        if user and getattr(user, "is_anonymous", False):
            user_login_failed.send(
                sender=__name__,
                credentials={"username": getattr(user, "email", "")},
                request=request,
            )

        return user
