from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_user_about_me"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                blank=True,
                error_messages={"unique": "A user with that email already exists."},
                max_length=254,
                null=True,
                unique=True,
                verbose_name="email address",
            ),
        ),
        migrations.AddField(
            model_name="user",
            name="phone",
            field=models.CharField(
                blank=True,
                help_text="Phone number in E.164 format.",
                max_length=16,
                null=True,
                unique=True,
                verbose_name="phone number",
            ),
        ),
        migrations.AddIndex(
            model_name="user",
            index=models.Index(fields=["phone"], name="users_phone_e164_idx"),
        ),
        migrations.CreateModel(
            name="PhoneSignupTicket",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "phone",
                    models.CharField(
                        help_text="Verified phone number in E.164 format.",
                        max_length=16,
                    ),
                ),
                (
                    "token_hash",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("used_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "Phone Signup Ticket",
                "verbose_name_plural": "Phone Signup Tickets",
                "db_table": "phone_signup_tickets",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["phone"], name="phone_signup_phone_idx"),
                ],
            },
        ),
    ]
