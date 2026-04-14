import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('admins', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='admin',
            name='admin_name',
            field=models.CharField(max_length=255, unique=True),
        ),
        migrations.AlterField(
            model_name='admin',
            name='role',
            field=models.CharField(choices=[('teacher', 'Teacher'), ('admin', 'Admin')], max_length=50),
        ),
        migrations.AddField(
            model_name='admin',
            name='failed_login_attempts',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='admin',
            name='is_locked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='admin',
            name='last_login_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='admin',
            name='must_change_password',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='AuthAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('attempted_admin_name', models.CharField(blank=True, max_length=255)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('event_type', models.CharField(choices=[('login_success', 'Login Success'), ('login_failure', 'Login Failure'), ('logout', 'Logout'), ('password_change', 'Password Change'), ('account_unlocked', 'Account Unlocked')], max_length=50)),
                ('details', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('admin', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='admins.admin')),
            ],
            options={
                'db_table': 'auth_audit_logs',
            },
        ),
        migrations.CreateModel(
            name='TokenBlacklist',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jti', models.CharField(max_length=255, unique=True)),
                ('expires_at', models.DateTimeField()),
                ('blacklisted_at', models.DateTimeField(auto_now_add=True)),
                ('admin', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='revoked_tokens', to='admins.admin')),
            ],
            options={
                'db_table': 'token_blacklist',
            },
        ),
        migrations.AddIndex(
            model_name='authauditlog',
            index=models.Index(fields=['attempted_admin_name'], name='idx_auth_audit_name'),
        ),
        migrations.AddIndex(
            model_name='authauditlog',
            index=models.Index(fields=['event_type', 'created_at'], name='idx_auth_audit_event'),
        ),
        migrations.AddIndex(
            model_name='tokenblacklist',
            index=models.Index(fields=['expires_at'], name='idx_token_blacklist_exp'),
        ),
    ]