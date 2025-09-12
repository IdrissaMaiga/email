# Generated manually to remove unique constraint on email field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('email_monitor', '0009_remove_emailsender_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='email',
            field=models.EmailField(help_text='Primary email address'),
        ),
    ]
