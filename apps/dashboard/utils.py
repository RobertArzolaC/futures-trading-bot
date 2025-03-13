from django.utils import timezone


def format_patients_orders_for_chart(patients_by_month, orders_by_month):
    months = []
    patient_counts = []
    order_counts = []

    for i in range(12):
        month = (
            timezone.now().replace(month=1) + timezone.timedelta(days=32 * i)
        ).replace(day=1)
        patient_count = next(
            (x["count"] for x in patients_by_month if x["month"].month == month.month), 0
        )
        order_count = next(
            (x["count"] for x in orders_by_month if x["month"].month == month.month), 0
        )

        months.append(month.strftime("%b"))
        patient_counts.append(patient_count)
        order_counts.append(order_count)

    return {
        "months": months,
        "series": [
            {"name": "Patients", "data": patient_counts},
            {"name": "Orders", "data": order_counts},
        ],
    }


def format_test_results_for_chart(results_queryset):
    # Setup data structure
    monthly_data = {
        "series": [
            {"name": "Normal Range", "type": "bar", "stacked": "true", "data": []},
            {"name": "Optimal Range", "type": "bar", "stacked": "true", "data": []},
            {"name": "Out of Range", "type": "bar", "stacked": "true", "data": []},
        ],
        "categories": [],
    }

    # Group results by month and level
    results_by_month = {}
    for result in results_queryset:
        month = result["month"].strftime("%b")
        level = result["level"]
        count = result["count"]

        if month not in results_by_month:
            results_by_month[month] = {1: 0, 2: 0, 3: 0}  # Initialize all levels
            monthly_data["categories"].append(month)

        results_by_month[month][level] = count

    # Fill series data
    for month in monthly_data["categories"]:
        monthly_data["series"][0]["data"].append(results_by_month[month][1])  # Normal
        monthly_data["series"][1]["data"].append(results_by_month[month][2])  # Optimal
        monthly_data["series"][2]["data"].append(
            results_by_month[month][3]
        )  # Out of Range

    return monthly_data


def format_orders_by_status(orders_queryset):
    status_map = {
        1: "Pending",
        2: "In Progress",
        3: "Completed",
        4: "Canceled",
        5: "Received",
    }

    formatted_data = []
    for order in orders_queryset:
        formatted_data.append(
            {
                "value": order["count"],
                "category": status_map.get(order["status"], "Unknown"),
            }
        )

    return formatted_data


def format_test_results_by_level(results_queryset):
    levels_map = {
        1: ("normal_range", "Normal Range"),
        2: ("optimal_range", "Optimal Range"),
        3: ("red_line_range", "Red Line Range"),
    }

    formatted_data = {
        "red_line_range": {"title": "Red Line Range", "value": 0},
        "optimal_range": {"title": "Optimal Range", "value": 0},
        "normal_range": {"title": "Normal Range", "value": 0},
        "total": 0,
    }

    for result in results_queryset:
        key, _ = levels_map.get(result["level"], ("unknown", "Unknown"))
        formatted_data[key]["value"] = result["count"]
        formatted_data["total"] += result["count"]

    return formatted_data
