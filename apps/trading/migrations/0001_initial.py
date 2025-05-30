# Generated by Django 4.2.16 on 2025-03-13 20:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import model_utils.fields


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Operation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('symbol', models.CharField(max_length=20)),
                ('direction', models.CharField(choices=[('long', 'Long'), ('short', 'Short')], max_length=10)),
                ('status', models.CharField(choices=[('open', 'Open'), ('closed', 'Closed')], default='open', max_length=10)),
                ('entry_price', models.DecimalField(decimal_places=8, max_digits=16)),
                ('exit_price', models.DecimalField(blank=True, decimal_places=8, max_digits=16, null=True)),
                ('quantity', models.DecimalField(decimal_places=8, max_digits=16)),
                ('leverage', models.IntegerField()),
                ('investment', models.DecimalField(decimal_places=8, max_digits=16)),
                ('take_profit', models.IntegerField()),
                ('stop_loss', models.IntegerField()),
                ('profit_loss', models.DecimalField(blank=True, decimal_places=8, max_digits=16, null=True)),
                ('profit_loss_percentage', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('opened_at', models.DateTimeField(auto_now_add=True)),
                ('closed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operations', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-opened_at'],
            },
        ),
        migrations.CreateModel(
            name='Signal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('ticker', models.CharField(max_length=20)),
                ('signal_type', models.CharField(choices=[('buy', 'Buy'), ('sell', 'Sell')], max_length=10)),
                ('timeframe', models.CharField(max_length=10)),
                ('strategy', models.CharField(max_length=50)),
                ('price_close', models.DecimalField(decimal_places=8, max_digits=16)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('processed', models.BooleanField(default=False)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='TradingSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('api_key', models.CharField(blank=True, max_length=255)),
                ('api_secret', models.CharField(blank=True, max_length=255)),
                ('webhook_url', models.URLField(blank=True)),
                ('telegram_bot_token', models.CharField(blank=True, max_length=255)),
                ('telegram_chat_id', models.CharField(blank=True, max_length=255)),
                ('investment_percentage', models.IntegerField(default=100)),
                ('leverage', models.IntegerField(default=25)),
                ('take_profit', models.IntegerField(default=25)),
                ('stop_loss', models.IntegerField(default=25)),
                ('symbol', models.CharField(default='BTCUSDT', max_length=20)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='trading_settings', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='SignalGroup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('direction', models.CharField(choices=[('buy', 'Buy'), ('sell', 'Sell')], max_length=10)),
                ('operation', models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='signal_group', to='trading.operation')),
                ('signals', models.ManyToManyField(related_name='signal_groups', to='trading.signal')),
            ],
            options={
                'ordering': ['-created'],
            },
        ),
        migrations.CreateModel(
            name='BotStatus',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', model_utils.fields.AutoCreatedField(default=django.utils.timezone.now, editable=False, verbose_name='created')),
                ('modified', model_utils.fields.AutoLastModifiedField(default=django.utils.timezone.now, editable=False, verbose_name='modified')),
                ('status', models.CharField(choices=[('idle', 'Idle'), ('listening', 'Listening'), ('confirming', 'Confirming'), ('operating', 'Operating')], default='idle', max_length=20)),
                ('confirming_count', models.IntegerField(default=0)),
                ('last_updated', models.DateTimeField(auto_now=True)),
                ('current_operation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='bot_status', to='trading.operation')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='bot_status', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
