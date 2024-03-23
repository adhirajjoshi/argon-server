# Generated by Django 4.2.3 on 2024-03-23 20:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('flight_declaration_operations', '0007_alter_flightdeclaration_state'),
    ]

    operations = [
        migrations.AlterField(
            model_name='flightdeclaration',
            name='aircraft_id',
            field=models.CharField(help_text='Specify the ID of the aircraft for this declaration', max_length=256),
        ),
    ]
