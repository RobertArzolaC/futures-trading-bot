from apps.customers import models as customer_models
from apps.laboratory import models as laboratory_models


def get_entities_summary(request):
    return {
        "account_count": customer_models.Account.objects.count(),
        "patient_count": customer_models.Patient.objects.count(),
        "panel_count": laboratory_models.Panel.objects.count(),
        "medical_test_count": laboratory_models.MedicalTest.objects.count(),
    }
