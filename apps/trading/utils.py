from django.utils import timezone


# Funciones auxiliares
def format_operation_info(operation):
    """Formatea la información de una operación abierta"""
    return (
        f"Broker: BINANCE\n"
        f"Ativo: {operation.symbol}\n"
        f"Direccion: {'BUY' if operation.direction == 'long' else 'SELL'}\n"
        f"Apalancamiento: x{operation.leverage}\n"
        f"Inversión: USD {float(operation.investment):.2f}\n"
        f"Entrada: {float(operation.entry_price)}\n"
        f"Take Profit: {operation.take_profit}%\n"
        f"Stop Loss: {operation.stop_loss}%\n"
        f"Tiempo: {format_time_difference(operation.opened_at)}"
    )


def format_operation_result(operation):
    """Formatea los resultados de una operación cerrada"""
    time_diff = format_time_difference(operation.opened_at, operation.closed_at)
    direction = "BUY" if operation.direction == "long" else "SELL"
    profit_prefix = "+" if operation.profit_loss_percentage >= 0 else ""

    return (
        f"Broker: BINANCE\n"
        f"Ativo: {operation.symbol}\n"
        f"Direccion: {direction}\n"
        f"Apalancamiento: x{operation.leverage}\n"
        f"Inversión: USD {float(operation.investment):.2f}\n"
        f"ROI: {profit_prefix}{float(operation.profit_loss_percentage):.2f}%\n"
        f"Ganancia: USD {float(operation.profit_loss):.2f}\n"
        f"Entrada: {float(operation.entry_price)}\n"
        f"Ultimo: {float(operation.exit_price)}\n"
        f"Variación: {abs(float(operation.profit_loss_percentage) / operation.leverage):.2f}%\n"
        f"Tiempo: {time_diff}"
    )


def format_time_difference(start_time, end_time=None):
    """Formatea la diferencia de tiempo como 'Nd Nh Nm'"""
    if end_time is None:
        end_time = timezone.now()

    diff = end_time - start_time
    days = diff.days
    hours = diff.seconds // 3600
    minutes = (diff.seconds % 3600) // 60

    if days > 0:
        return f"{days}D {hours}h {minutes}m"
    elif hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"
