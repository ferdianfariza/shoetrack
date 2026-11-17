from decimal import Decimal

from django.db.models import F, Sum
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from unfold.views import UnfoldSiteViewMixin

from .models import Produk, Transaksi


def _format_rupiah(value):
    return f"Rp {int(value or 0):,}".replace(",", ".")


class FinanceReportView(UnfoldSiteViewMixin, TemplateView):
    template_name = "admin/finance_report.html"
    title = "Laporan Keuangan"
    permission_required = "tracker.view_transaksi"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report = _get_finance_report()
        report["pdf_url"] = reverse("admin:finance_report_pdf")
        context["report"] = report
        return context


def _get_finance_report():
    sales = Transaksi.objects.filter(tipe=Transaksi.Tipe.PENJUALAN)
    purchases = Transaksi.objects.filter(tipe=Transaksi.Tipe.PEMBELIAN)
    sales_total = sales.aggregate(total=Sum("total"))["total"] or Decimal("0")
    cost_of_goods_sold = (
        sales.aggregate(
            total=Sum(F("kuantitas") * F("produk__harga_beli"))
        )["total"]
        or Decimal("0")
    )
    gross_profit = sales_total - cost_of_goods_sold
    purchase_total = purchases.aggregate(total=Sum("total"))["total"] or Decimal("0")
    inventory_value = (
        Produk.objects.aggregate(total=Sum(F("stok") * F("harga_beli")))["total"]
        or Decimal("0")
    )

    return {
        "cards": [
            {"label": "Total Penjualan", "value": _format_rupiah(sales_total)},
            {"label": "HPP Penjualan", "value": _format_rupiah(cost_of_goods_sold)},
            {"label": "Laba Kotor", "value": _format_rupiah(gross_profit)},
        ],
        "rows": [
            ("Penjualan", _format_rupiah(sales_total)),
            ("Harga Pokok Penjualan", _format_rupiah(cost_of_goods_sold)),
            ("Laba Kotor", _format_rupiah(gross_profit)),
            ("Total Pembelian (arus pembelian)", _format_rupiah(purchase_total)),
            ("Nilai Persediaan Akhir", _format_rupiah(inventory_value)),
        ],
    }


class FinanceReportPdfView(UnfoldSiteViewMixin, TemplateView):
    permission_required = "tracker.view_transaksi"

    def get(self, request, *args, **kwargs):
        report = _get_finance_report()
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            'attachment; filename="laporan-keuangan-shoetrack.pdf"'
        )

        document = SimpleDocTemplate(
            response,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=17 * mm,
            bottomMargin=18 * mm,
            title="Laporan Keuangan Shoetrack",
            author="Shoetrack",
        )
        styles = getSampleStyleSheet()
        styles.add(
            ParagraphStyle(
                name="ReportBrand",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=10,
                textColor=colors.HexColor("#a87950"),
                spaceAfter=4,
            )
        )
        styles.add(
            ParagraphStyle(
                name="ReportTitle",
                parent=styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=22,
                leading=27,
                textColor=colors.HexColor("#252d50"),
                spaceAfter=5,
            )
        )
        styles.add(
            ParagraphStyle(
                name="ReportSubtitle",
                parent=styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#62584f"),
                spaceAfter=16,
            )
        )
        styles.add(
            ParagraphStyle(
                name="MetricLabel",
                parent=styles["Normal"],
                fontSize=8,
                textColor=colors.HexColor("#62584f"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="MetricValue",
                parent=styles["Normal"],
                fontName="Helvetica-Bold",
                fontSize=14,
                leading=18,
                textColor=colors.HexColor("#252d50"),
                spaceBefore=5,
            )
        )
        styles.add(
            ParagraphStyle(
                name="SectionTitle",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=12,
                textColor=colors.HexColor("#252d50"),
                spaceBefore=18,
                spaceAfter=8,
            )
        )
        styles.add(
            ParagraphStyle(
                name="TableCell",
                parent=styles["Normal"],
                fontSize=9,
                textColor=colors.HexColor("#414b78"),
            )
        )
        styles.add(
            ParagraphStyle(
                name="TableAmount",
                parent=styles["TableCell"],
                alignment=TA_RIGHT,
            )
        )
        styles.add(
            ParagraphStyle(
                name="Note",
                parent=styles["Normal"],
                fontSize=8,
                leading=11,
                textColor=colors.HexColor("#7884ae"),
                spaceBefore=10,
            )
        )

        story = [
            Paragraph("SHOETRACK", styles["ReportBrand"]),
            Paragraph("Laporan Keuangan", styles["ReportTitle"]),
            Paragraph(
                f"Ringkasan transaksi per {timezone.localdate().strftime('%d-%m-%Y')}",
                styles["ReportSubtitle"],
            ),
        ]

        metric_cells = []
        for card in report["cards"]:
            metric_cells.append(
                [
                    Paragraph(card["label"], styles["MetricLabel"]),
                    Paragraph(card["value"], styles["MetricValue"]),
                ]
            )
        metrics = Table([metric_cells], colWidths=[57 * mm] * len(metric_cells))
        metrics.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f5efe7")),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e9ded0")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.6, colors.HexColor("#e9ded0")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ]
            )
        )
        story.extend([metrics, Spacer(1, 8), Paragraph("Ringkasan Laba Rugi", styles["SectionTitle"])])

        table_data = [
            [
                Paragraph("<b>Keterangan</b>", styles["TableCell"]),
                Paragraph("<b>Jumlah</b>", styles["TableAmount"]),
            ]
        ]
        table_data.extend(
            [
                [
                    Paragraph(label, styles["TableCell"]),
                    Paragraph(amount, styles["TableAmount"]),
                ]
                for label, amount in report["rows"]
            ]
        )
        report_table = Table(table_data, colWidths=[125 * mm, 46 * mm], repeatRows=1)
        report_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#252d50")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#e9ded0")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e9ded0")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 9),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ]
            )
        )
        story.extend(
            [
                report_table,
                Paragraph(
                    "Laporan ini merupakan ringkasan operasional sederhana, bukan laporan keuangan lengkap sesuai SAK. Pembelian tidak dikurangkan langsung dari penjualan untuk menghitung laba kotor.",
                    styles["Note"],
                ),
            ]
        )

        def draw_footer(canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(colors.HexColor("#e9ded0"))
            canvas.line(18 * mm, 12 * mm, A4[0] - 18 * mm, 12 * mm)
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#7884ae"))
            canvas.drawString(18 * mm, 7 * mm, "Shoetrack • Laporan Keuangan")
            canvas.drawRightString(
                A4[0] - 18 * mm, 7 * mm, f"Halaman {doc.page}"
            )
            canvas.restoreState()

        document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
        return response