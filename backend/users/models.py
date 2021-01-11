from django.contrib.auth.base_user import AbstractBaseUser
from django.db import models
from django.contrib.auth.models import (PermissionsMixin, BaseUserManager)
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class CatenaUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                "Superuser must have is_staff=True."
            )
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "Superuser must have is_superuser=True."
            )
        return self._create_user(email, password, **extra_fields)


class CatenaUser(AbstractBaseUser, PermissionsMixin):

    def __str__(self):
        return self.public_key
    username = None

    email = models.EmailField(_('email address'), unique=True)

    full_name = models.CharField(_('full name'), max_length=256)

    phone_number = models.CharField(_('phone number'), max_length=31, blank=True)

    public_key = models.CharField(_('public key'), max_length=34, blank=False, null=False)

    description = models.TextField(_('Profile Description'), default="")

    refresh_token = models.CharField(_('Refresh Token'), max_length=30, blank=True, null=True)

    has_verified_phone = models.BooleanField(_('phone is verified'), default=False)

    has_verified_gov_id = models.BooleanField(default=False)

    paipass_user_id = models.BigIntegerField(_("Paipass User Id"), unique=True, blank=False, null=False)

    account_type = models.CharField(_('Account Type'), max_length=16, blank=True, null=True)



    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )

    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )

    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    access_token = models.TextField(_("Access Token"), null=True)

    USERNAME_FIELD = 'email'

    objects = CatenaUserManager()
