from django.apps import AppConfig


class WalletsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "wallets"
    
    _scheduler_started = False

    def ready(self):
        if not self._scheduler_started:
            from .utils import iniciar_agendamento
            iniciar_agendamento()
            self._scheduler_started = True
