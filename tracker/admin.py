# tracker/admin.py
from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Kategori, Pelanggan, Produk, Supplier, Transaksi


@admin.register(Kategori)
class KategoriAdmin(ModelAdmin):
    list_display = ("kategori",)


@admin.register(Supplier)
class SupplierAdmin(ModelAdmin):
    list_display = ("nama", "telepon", "alamat")
    search_fields = ("nama",)


@admin.register(Pelanggan)
class PelangganAdmin(ModelAdmin):
    list_display = ("nama", "telepon", "alamat")
    search_fields = ("nama",)


@admin.register(Produk)
class ProdukAdmin(ModelAdmin):
    list_display = (
        "sku",
        "nama_produk",
        "merek",
        "kategori",
        "ukuran",
        "harga_beli",
        "harga_jual",
        "stok",
    )
    list_filter = ("kategori", "merek")
    search_fields = ("sku", "nama_produk", "merek")
    readonly_fields = ("sku",)


@admin.register(Transaksi)
class TransaksiAdmin(ModelAdmin):
    list_display = (
        "kode_transaksi",
        "tanggal",
        "tipe",
        "produk",
        "pihak",
        "kuantitas",
        "harga_satuan",
        "total",
    )
    list_filter = ("tipe", "tanggal")
    search_fields = ("kode_transaksi", "produk__nama_produk", "produk__sku")
    readonly_fields = ("kode_transaksi", "total")
