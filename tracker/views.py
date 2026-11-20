# tracker/views.py
from decimal import Decimal

from django.db.models import F, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from unfold.views import UnfoldSiteViewMixin

from .models import Produk, Transaksi

COMPANY_NAME = "SHOETRACK"
COMPANY_ADDRESS = "xxx"
COMPANY_CONTACT = "xxx"


def page_not_found(request, exception=None):
    return render(request, "404.html", status=404)


def _format_rupiah(value):
    return f"Rp {int(value or 0):,}".replace(",", ".")


def _get_finance_report():
    sales = Transaksi.objects.filter(tipe=Transaksi.Tipe.PENJUALAN)
    purchases = Transaksi.objects.filter(tipe=Transaksi.Tipe.PEMBELIAN)

    sales_total = sales.aggregate(total=Sum("total"))["total"] or Decimal(0)
    cost_of_goods_sold = sales.aggregate(
        total=Sum(F("kuantitas") * F("produk__harga_beli"))
    )["total"] or Decimal(0)
    gross_profit = sales_total - cost_of_goods_sold
    purchase_total = purchases.aggregate(total=Sum("total"))["total"] or Decimal(0)
    inventory_value = Produk.objects.aggregate(total=Sum(F("stok") * F("harga_beli")))[
        "total"
    ] or Decimal(0)

    items_sold = sales.aggregate(n=Sum("kuantitas"))["n"] or 0
    items_bought = purchases.aggregate(n=Sum("kuantitas"))["n"] or 0
    items_in_stock = Produk.objects.aggregate(n=Sum("stok"))["n"] or 0
    sales_count = sales.count()
    purchase_count = purchases.count()
    product_count = Produk.objects.count()

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
        "details": {
            "Penjualan": f"{sales_count} transaksi penjualan, total item terjual: {items_sold}",
            "Harga Pokok Penjualan": f"Total item terjual: {items_sold} (dihitung dari harga beli produk)",
            "Laba Kotor": f"Total item terjual: {items_sold} (penjualan dikurangi HPP)",
            "Total Pembelian (arus pembelian)": f"{purchase_count} transaksi pembelian, total item dibeli: {items_bought}",
            "Nilai Persediaan Akhir": f"Total item tersedia: {items_in_stock} dari {product_count} produk (stok x harga beli)",
        },
    }


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


class FinanceReportPdfView(UnfoldSiteViewMixin, TemplateView):
    permission_required = "tracker.view_transaksi"

    def get(self, request, *args, **kwargs):
        report = _get_finance_report()
        today = timezone.localdate()
        printed_at = timezone.localtime()
        user_name = request.user.get_full_name() or request.user.get_username()

        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = (
            'attachment; filename="laporan-keuangan-shoetrack.pdf"'
        )

        doc = SimpleDocTemplate(
            response,
            pagesize=A4,
            leftMargin=20 * mm,
            rightMargin=20 * mm,
            topMargin=18 * mm,
            bottomMargin=20 * mm,
            title="Laporan Keuangan Shoetrack",
            author=COMPANY_NAME,
        )
        content_width = A4[0] - 40 * mm

        base = getSampleStyleSheet()["Normal"]
        st = {
            "company": ParagraphStyle(
                "company",
                parent=base,
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=20,
                alignment=TA_CENTER,
            ),
            "address": ParagraphStyle(
                "address",
                parent=base,
                fontSize=8.5,
                leading=12,
                alignment=TA_CENTER,
                textColor=colors.HexColor("#444444"),
            ),
            "title": ParagraphStyle(
                "title",
                parent=base,
                fontName="Helvetica-Bold",
                fontSize=13,
                leading=17,
                alignment=TA_CENTER,
            ),
            "period": ParagraphStyle(
                "period",
                parent=base,
                fontSize=9.5,
                leading=13,
                alignment=TA_CENTER,
            ),
            "cell": ParagraphStyle("cell", parent=base, fontSize=10, leading=14),
            "cell_bold": ParagraphStyle(
                "cell_bold",
                parent=base,
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=14,
            ),
            "detail": ParagraphStyle(
                "detail",
                parent=base,
                fontSize=8,
                leading=11,
                textColor=colors.HexColor("#555555"),
            ),
            "amount": ParagraphStyle(
                "amount",
                parent=base,
                fontSize=10,
                leading=14,
                alignment=TA_RIGHT,
            ),
            "amount_bold": ParagraphStyle(
                "amount_bold",
                parent=base,
                fontName="Helvetica-Bold",
                fontSize=10,
                leading=14,
                alignment=TA_RIGHT,
            ),
            "note": ParagraphStyle(
                "note",
                parent=base,
                fontSize=8,
                leading=11,
                textColor=colors.HexColor("#555555"),
            ),
            "sign": ParagraphStyle(
                "sign",
                parent=base,
                fontSize=10,
                leading=14,
                alignment=TA_CENTER,
            ),
        }

        # ---------- Kop laporan ----------
        story = [
            Paragraph(COMPANY_NAME, st["company"]),
            Paragraph(COMPANY_ADDRESS, st["address"]),
            Paragraph(COMPANY_CONTACT, st["address"]),
            Spacer(1, 4),
            HRFlowable(width="100%", thickness=1.8, color=colors.black, spaceAfter=1),
            HRFlowable(width="100%", thickness=0.5, color=colors.black, spaceAfter=10),
            Paragraph("LAPORAN KEUANGAN", st["title"]),
            Paragraph("Ringkasan Laba Rugi", st["period"]),
            Paragraph(f"Per tanggal {today:%d-%m-%Y}", st["period"]),
            Spacer(1, 14),
        ]

        # ---------- Tabel laporan ----------
        total_labels = {"Laba Kotor", "Nilai Persediaan Akhir"}
        data = [
            [
                Paragraph("<b>No</b>", st["cell"]),
                Paragraph("<b>Keterangan</b>", st["cell"]),
                Paragraph("<b>Jumlah</b>", st["amount"]),
            ]
        ]
        bold_rows = []
        for i, (label, amount) in enumerate(report["rows"], start=1):
            is_total = label in total_labels
            if is_total:
                bold_rows.append(i)
            keterangan = [Paragraph(label, st["cell_bold" if is_total else "cell"])]
            detail = report["details"].get(label)
            if detail:
                keterangan.append(Paragraph(detail, st["detail"]))
            data.append(
                [
                    Paragraph(str(i), st["cell"]),
                    keterangan,
                    Paragraph(amount, st["amount_bold" if is_total else "amount"]),
                ]
            )

        table = Table(
            data,
            colWidths=[12 * mm, content_width - 12 * mm - 45 * mm, 45 * mm],
            repeatRows=1,
        )
        style = [
            ("LINEABOVE", (0, 0), (-1, 0), 1, colors.black),
            ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.black),
            ("LINEBELOW", (0, 1), (-1, -2), 0.25, colors.HexColor("#BBBBBB")),
            ("LINEBELOW", (0, -1), (-1, -1), 1, colors.black),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F2F2")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
        for r in bold_rows:
            style.append(("LINEABOVE", (0, r), (-1, r), 0.6, colors.black))
        table.setStyle(TableStyle(style))
        story.append(table)

        story.append(Spacer(1, 8))
        story.append(
            Paragraph(
                "Catatan: laporan ini merupakan ringkasan operasional sederhana "
                "dan bukan laporan keuangan lengkap sesuai SAK. Total pembelian "
                "adalah arus pembelian barang, tidak dikurangkan langsung dari "
                "penjualan untuk menghitung laba kotor.",
                st["note"],
            )
        )

        # ---------- Tanda tangan ----------
        sign = Table(
            [
                [Paragraph(f"Semarang, {today:%d-%m-%Y}", st["sign"])],
                [Paragraph("Dibuat oleh,", st["sign"])],
                [Spacer(1, 40)],
                [Paragraph(f"<u>{user_name}</u>", st["sign"])],
            ],
            colWidths=[60 * mm],
        )
        sign.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        wrapper = Table([[None, sign]], colWidths=[content_width - 60 * mm, 60 * mm])
        wrapper.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.extend([Spacer(1, 28), wrapper])

        # ---------- Footer ----------
        def footer(canvas, doc_):
            canvas.saveState()
            canvas.setStrokeColor(colors.black)
            canvas.setLineWidth(0.5)
            canvas.line(20 * mm, 14 * mm, A4[0] - 20 * mm, 14 * mm)
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#444444"))
            canvas.drawString(
                20 * mm,
                9.5 * mm,
                f"Dicetak: {printed_at:%d-%m-%Y %H:%M}  |  {COMPANY_NAME}",
            )
            canvas.drawRightString(A4[0] - 20 * mm, 9.5 * mm, f"Halaman {doc_.page}")
            canvas.restoreState()

        doc.build(story, onFirstPage=footer, onLaterPages=footer)
        return response
