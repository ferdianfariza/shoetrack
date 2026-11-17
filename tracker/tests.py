from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .dashboard import dashboard_callback
from .models import Kategori, Pelanggan, Produk, Supplier, Transaksi
from .views import FinanceReportPdfView


class DashboardCallbackTests(TestCase):
    def setUp(self):
        kategori = Kategori.objects.create(kategori="Sneakers")
        self.supplier = Supplier.objects.create(nama="Supplier")
        self.customer = Pelanggan.objects.create(nama="Customer")
        self.product = Produk.objects.create(
            nama_produk="Nike Air Force 1",
            merek="Nike",
            kategori=kategori,
            ukuran="42",
            harga_beli=100000,
            harga_jual=150000,
            stok=2,
        )
        self.request = RequestFactory().get(reverse("admin:index"))

    def test_dashboard_contains_business_metrics_and_widgets(self):
        today = timezone.localdate()
        Transaksi.objects.create(
            tipe=Transaksi.Tipe.PEMBELIAN,
            tanggal=today,
            produk=self.product,
            supplier=self.supplier,
            kuantitas=3,
            harga_satuan=100000,
        )
        Transaksi.objects.create(
            tipe=Transaksi.Tipe.PENJUALAN,
            tanggal=today,
            produk=self.product,
            pelanggan=self.customer,
            kuantitas=2,
            harga_satuan=150000,
        )

        context = dashboard_callback(self.request, {})

        metrics = context["dashboard"]["metrics"]
        self.assertEqual([metric["value"] for metric in metrics], [
            "Rp 300.000",
            "Rp 300.000",
            "Rp 300.000",
            "Rp 100.000",
        ])
        self.assertEqual(len(context["dashboard"]["chart_values"]), 7)
        self.assertEqual(len(context["dashboard"]["recent_transactions"]), 2)
        self.assertEqual(list(context["dashboard"]["low_stock"]), [self.product])


class FinanceReportPdfTests(TestCase):
    def test_finance_report_returns_a4_pdf_attachment(self):
        request = RequestFactory().get("/admin/reports/finance/pdf/")

        response = FinanceReportPdfView().get(request)

        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(
            response["Content-Disposition"],
            'attachment; filename="laporan-keuangan-shoetrack.pdf"',
        )
        self.assertTrue(response.content.startswith(b"%PDF-"))
