from datetime import timedelta
from decimal import Decimal

from django.db.models import F, Sum
from django.urls import reverse
from django.utils import timezone

from .models import Produk, Transaksi


def _format_rupiah(value: Decimal | int | None) -> str:
    amount = int(value or 0)
    return f"Rp {amount:,}".replace(",", ".")


def _next_month(month_start):
    if month_start.month == 12:
        return month_start.replace(
            year=month_start.year + 1, month=1
        )
    return month_start.replace(month=month_start.month + 1)


def dashboard_callback(request, context):
    today = timezone.localdate()
    start_date = today - timedelta(days=6)
    sales = Transaksi.objects.filter(tipe=Transaksi.Tipe.PENJUALAN)
    purchases = Transaksi.objects.filter(tipe=Transaksi.Tipe.PEMBELIAN)

    sales_total = sales.aggregate(total=Sum("total"))["total"] or Decimal("0")
    purchase_total = purchases.aggregate(total=Sum("total"))["total"] or Decimal("0")
    inventory_value = (
        Produk.objects.aggregate(total=Sum(F("harga_beli") * F("stok")))["total"]
        or Decimal("0")
    )
    gross_profit = (
        sales.aggregate(
            total=Sum(F("total") - F("kuantitas") * F("produk__harga_beli"))
        )["total"]
        or Decimal("0")
    )

    chart_values = []
    for offset in range(7):
        date = start_date + timedelta(days=offset)
        sales_amount = (
            sales.filter(tanggal=date).aggregate(total=Sum("total"))["total"]
            or Decimal("0")
        )
        purchase_amount = (
            purchases.filter(tanggal=date).aggregate(total=Sum("total"))["total"]
            or Decimal("0")
        )
        chart_values.append(
            {
                "label": date.strftime("%d-%m"),
                "amount": sales_amount,
                "sales": float(sales_amount),
                "purchases": float(purchase_amount),
                "x": 30 + offset * (620 / 6),
            }
        )

    chart_max = max((item["amount"] for item in chart_values), default=Decimal("0"))
    chart_points = []
    for index, item in enumerate(chart_values):
        x = item["x"]
        y = 172 if chart_max == 0 else 172 - float(item["amount"] / chart_max) * 140
        chart_points.append(f"{x:g},{y:g}")

    current_month = today.replace(day=1)
    monthly_values = []
    for offset in range(5, -1, -1):
        month = current_month
        for _ in range(offset):
            month = (
                month.replace(year=month.year - 1, month=12)
                if month.month == 1
                else month.replace(month=month.month - 1)
            )
        next_month = _next_month(month)
        sales_amount = (
            sales.filter(tanggal__gte=month, tanggal__lt=next_month).aggregate(
                total=Sum("total")
            )["total"]
            or Decimal("0")
        )
        purchase_amount = (
            purchases.filter(
                tanggal__gte=month, tanggal__lt=next_month
            ).aggregate(total=Sum("total"))["total"]
            or Decimal("0")
        )
        monthly_values.append(
            {
                "label": month.strftime("%b %Y"),
                "sales": float(sales_amount),
                "purchases": float(purchase_amount),
            }
        )

    low_stock = Produk.objects.filter(stok__lte=5).order_by("stok", "merek")[:5]
    recent_transactions = Transaksi.objects.select_related(
        "produk", "supplier"
    ).order_by("-tanggal", "-id")[:5]
    for transaction in recent_transactions:
        transaction.formatted_total = _format_rupiah(transaction.total)

    context["dashboard"] = {
        "metrics": [
            {"label": "Total Penjualan", "value": _format_rupiah(sales_total)},
            {"label": "Total Pembelian", "value": _format_rupiah(purchase_total)},
            {"label": "Nilai Persediaan", "value": _format_rupiah(inventory_value)},
            {"label": "Laba Kotor", "value": _format_rupiah(gross_profit)},
        ],
        "chart_values": chart_values,
        "chart_points": " ".join(chart_points),
        "chart_max": chart_max,
        "chart_data": {
            "daily": [
                {
                    "label": item["label"],
                    "sales": item["sales"],
                    "purchases": item["purchases"],
                }
                for item in chart_values
            ],
            "monthly": monthly_values,
        },
        "low_stock": low_stock,
        "recent_transactions": recent_transactions,
        "urls": {
            "sales": f"{reverse('admin:tracker_transaksi_add')}?tipe=jual",
            "purchases": f"{reverse('admin:tracker_transaksi_add')}?tipe=beli",
            "transactions": reverse("admin:tracker_transaksi_changelist"),
        },
    }
    return context
