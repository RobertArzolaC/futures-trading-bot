# from django.db.models.signals import post_save
# from django.dispatch import receiver

# from apps.trading import models, tasks


# @receiver(post_save, sender=models.Signal)
# def execute_celery_task_on_signal_creation(sender, instance, created, **kwargs):
#     if created:
#         tasks.process_signal.delay(signal_id=instance.id)
