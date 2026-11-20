# tracker/models.py
import random
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F


class Supplier(models.Model):
    nama = models.CharField(max_length=100)
    telepon = models.CharField(max_length=20, blank=True)
    alamat = models.TextField(blank=True)

    def __str__(self):
        return self.nama


class Produk(models.Model):
    merek = models.CharField(max_length=100)
    ukuran = models.CharField(max_length=10)
    harga_beli = models.DecimalField(max_digits=12, decimal_places=2)
    harga_jual = models.DecimalField(max_digits=12, decimal_places=2)
    stok = models.IntegerField(default=0)
    batas_minimum = models.PositiveIntegerField(default=5)

    class Meta:
        verbose_name_plural = "produk"

    def __str__(self):
        return f"{self.merek} - {self.ukuran} (ID: {self.pk})"

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.harga_jual = self.harga_beli * Decimal("1.50")
        super().save(*args, **kwargs)


class StokProduk(Produk):
    class Meta:
        proxy = True
        verbose_name = "stok produk"
        verbose_name_plural = "stok produk"


class Transaksi(models.Model):
    class Tipe(models.TextChoices):
        PEMBELIAN = "beli", "Pembelian"
        PENJUALAN = "jual", "Penjualan"

    kode_transaksi = models.CharField(max_length=10, unique=True, editable=False)
    tipe = models.CharField(max_length=5, choices=Tipe.choices)
    tanggal = models.DateField()
    produk = models.ForeignKey(Produk, on_delete=models.PROTECT)
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, null=True, blank=True
    )
    kuantitas = models.PositiveIntegerField()
    harga_satuan = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=14, decimal_places=2, editable=False)

    class Meta:
        verbose_name_plural = "transaksi"
        ordering = ["-tanggal", "-id"]

    def __str__(self):
        return f"{self.kode_transaksi} - {self.produk}"

    def clean(self):
        if self.tipe == self.Tipe.PEMBELIAN and not self.supplier:
            raise ValidationError({"supplier": "Pembelian wajib memilih supplier."})
        if (
            self.tipe == self.Tipe.PENJUALAN
            and self.pk is None
            and self.produk_id
            and self.kuantitas
            and self.kuantitas > self.produk.stok
        ):
            raise ValidationError({"kuantitas": "Stok tidak cukup."})

    def _buat_kode(self):
        prefix = "PB" if self.tipe == self.Tipe.PEMBELIAN else "PJ"
        while True:
            kode = f"{prefix}-{random.randint(1000, 9999)}"
            if not Transaksi.objects.filter(kode_transaksi=kode).exists():
                return kode

    def _stock_delta(self):
        return self.kuantitas if self.tipe == self.Tipe.PEMBELIAN else -self.kuantitas

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.total = self.kuantitas * self.harga_satuan

        if self.tipe == self.Tipe.PENJUALAN:
            self.supplier = None

        if is_new:
            self.kode_transaksi = self._buat_kode()

        with transaction.atomic():
            previous = None
            if not is_new:
                previous = Transaksi.objects.get(pk=self.pk)

            product_ids = {self.produk_id}
            if previous:
                product_ids.add(previous.produk_id)
            products = {
                product.pk: product
                for product in Produk.objects.select_for_update().filter(
                    pk__in=product_ids
                )
            }

            stock_change = self._stock_delta()
            if previous and previous.produk_id == self.produk_id:
                stock_change -= previous._stock_delta()
            if (
                self.tipe == self.Tipe.PENJUALAN
                and products[self.produk_id].stok + stock_change < 0
            ):
                raise ValidationError({"kuantitas": "Stok tidak cukup."})

            super().save(*args, **kwargs)
            if previous and previous.produk_id != self.produk_id:
                Produk.objects.filter(pk=previous.produk_id).update(
                    stok=F("stok") - previous._stock_delta()
                )
                stock_change = self._stock_delta()
            if stock_change:
                Produk.objects.filter(pk=self.produk_id).update(
                    stok=F("stok") + stock_change
                )

    def delete(self, *args, **kwargs):
        with transaction.atomic():
            product = Produk.objects.select_for_update().get(pk=self.produk_id)
            result = super().delete(*args, **kwargs)
            Produk.objects.filter(pk=product.pk).update(
                stok=F("stok") - self._stock_delta()
            )
            return result


class TransaksiPenjualan(Transaksi):
    class Meta:
        proxy = True
        verbose_name = "penjualan"
        verbose_name_plural = "penjualan"


class TransaksiPembelian(Transaksi):
    class Meta:
        proxy = True
        verbose_name = "pembelian"
        verbose_name_plural = "pembelian"
