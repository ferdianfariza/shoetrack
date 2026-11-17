from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .dashboard import dashboard_callback
from .models import Produk, Supplier, Transaksi
from .views import FinanceReportPdfView


class SkuTests(TestCase):
    def test_sku_uses_brand_model_and_sequence(self):
        examples = (
            ("Nike Air Jordan 2s", "NK-AJ2-001"),
            ("New Balance 1923", "NB1923-001"),
            ("Vans Old Skool", "VNS-OS-001"),
        )
        for nama_produk, expected_sku in examples:
            produk = Produk.objects.create(
                nama_produk=nama_produk,
                ukuran="42",
                harga_beli=100000,
                harga_jual=150000,
            )
            self.assertEqual(produk.sku, expected_sku)

        duplicate = Produk.objects.create(
            nama_produk="Nike Air Jordan 2s",
            ukuran="43",
            harga_beli=100000,
            harga_jual=150000,
        )
        self.assertEqual(duplicate.sku, "NK-AJ2-002")


class AdminRootUrlTests(TestCase):
    def test_root_url_opens_admin_login(self):
        response = self.client.get("/")

        self.assertRedirects(response, "/login/?next=/")

    def test_unknown_url_returns_custom_not_found_page(self):
        response = self.client.get("/alamat-yang-tidak-ada/")

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "Halaman tidak ditemukan", status_code=404)


class DashboardCallbackTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(nama="Supplier")
        self.product = Produk.objects.create(
            nama_produk="Nike Air Force 1",
            ukuran="42",
            harga_beli=100000,
            harga_jual=150000,
            stok=2,
        )
        self.assertEqual(self.product.sku, "NK-AF1-001")
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


class TransactionStockTests(TestCase):
    def setUp(self):
        self.supplier = Supplier.objects.create(nama="Supplier")
        self.product = Produk.objects.create(
            nama_produk="Nike Air Force 1",
            ukuran="42",
            harga_beli=100000,
            harga_jual=150000,
            stok=2,
        )

    def test_purchase_and_sale_update_stock(self):
        Transaksi.objects.create(
            tipe=Transaksi.Tipe.PEMBELIAN,
            tanggal=timezone.localdate(),
            produk=self.product,
            supplier=self.supplier,
            kuantitas=3,
            harga_satuan=100000,
        )
        Transaksi.objects.create(
            tipe=Transaksi.Tipe.PENJUALAN,
            tanggal=timezone.localdate(),
            produk=self.product,
            kuantitas=2,
            harga_satuan=150000,
        )

        self.assertEqual(Produk.objects.get(pk=self.product.pk).stok, 3)

    def test_editing_and_deleting_transaction_reconciles_stock(self):
        transaksi = Transaksi.objects.create(
            tipe=Transaksi.Tipe.PEMBELIAN,
            tanggal=timezone.localdate(),
            produk=self.product,
            supplier=self.supplier,
            kuantitas=3,
            harga_satuan=100000,
        )
        transaksi.kuantitas = 5
        transaksi.save()
        self.assertEqual(Produk.objects.get(pk=self.product.pk).stok, 7)

        transaksi.delete()
        self.assertEqual(Produk.objects.get(pk=self.product.pk).stok, 2)


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
