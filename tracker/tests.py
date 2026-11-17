from django.contrib import admin
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from .admin import ProdukAdmin, TransaksiForm
from .dashboard import dashboard_callback
from .models import Produk, Supplier, Transaksi
from .views import FinanceReportPdfView


class ProductPricingTests(TestCase):
    def test_create_product_admin_does_not_accept_manual_selling_price(self):
        admin_instance = ProdukAdmin(Produk, admin.site)
        request = RequestFactory().get("/admin/")

        self.assertEqual(admin_instance.get_exclude(request), ("harga_jual",))

    def test_new_product_sets_selling_price_to_cost_plus_30_percent(self):
        produk = Produk.objects.create(
            merek="Nike",
            ukuran="42",
            harga_beli=100000,
            harga_jual=150000,
        )

        self.assertEqual(produk.harga_jual, 130000)


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
            merek="Nike",
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
            merek="Nike",
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

    def test_product_price_defaults_are_used_for_transactions(self):
        purchase = Transaksi.objects.create(
            tipe=Transaksi.Tipe.PEMBELIAN,
            tanggal=timezone.localdate(),
            produk=self.product,
            supplier=self.supplier,
            kuantitas=1,
            harga_satuan=100000,
        )
        self.assertEqual(purchase.harga_satuan, 100000)

        purchase_form = TransaksiForm(
            data={
                "tipe": Transaksi.Tipe.PEMBELIAN,
                "tanggal": timezone.localdate(),
                "produk": self.product.pk,
                "supplier": self.supplier.pk,
                "kuantitas": 1,
                "harga_satuan": "",
            }
        )
        self.assertTrue(purchase_form.is_valid(), purchase_form.errors)
        self.assertEqual(purchase_form.cleaned_data["harga_satuan"], 100000)

        Transaksi.objects.create(
            tipe=Transaksi.Tipe.PEMBELIAN,
            tanggal=timezone.localdate(),
            produk=self.product,
            supplier=self.supplier,
            kuantitas=1,
            harga_satuan=120000,
        )
        latest_purchase_form = TransaksiForm(
            data={
                "tipe": Transaksi.Tipe.PEMBELIAN,
                "tanggal": timezone.localdate(),
                "produk": self.product.pk,
                "supplier": self.supplier.pk,
                "kuantitas": 1,
                "harga_satuan": "",
            }
        )
        self.assertTrue(latest_purchase_form.is_valid(), latest_purchase_form.errors)
        self.assertEqual(latest_purchase_form.cleaned_data["harga_satuan"], 120000)

        sale_form = TransaksiForm(
            data={
                "tipe": Transaksi.Tipe.PENJUALAN,
                "tanggal": timezone.localdate(),
                "produk": self.product.pk,
                "supplier": "",
                "kuantitas": 1,
                "harga_satuan": "",
            }
        )
        self.assertTrue(sale_form.is_valid(), sale_form.errors)
        self.assertEqual(sale_form.cleaned_data["harga_satuan"], 130000)

        sale = Transaksi.objects.create(
            tipe=Transaksi.Tipe.PENJUALAN,
            tanggal=timezone.localdate(),
            produk=self.product,
            kuantitas=1,
            harga_satuan=self.product.harga_jual,
        )
        self.assertEqual(sale.harga_satuan, 130000)


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
