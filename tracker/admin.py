# tracker/admin.py
from django.contrib import admin
from django.db.models import F
from unfold.admin import ModelAdmin

from .models import (
    Kategori,
    Pelanggan,
    Produk,
    StokProduk,
    Supplier,
    Transaksi,
    TransaksiPembelian,
    TransaksiPenjualan,
)


class StokStatusFilter(admin.SimpleListFilter):
    title = "status stok"
    parameter_name = "status_stok"

    def lookups(self, request, model_admin):
        return (("restock", "Perlu restock"), ("aman", "Aman"))

    def queryset(self, request, queryset):
        if self.value() == "restock":
            return queryset.filter(stok__lte=F("batas_minimum"))
        if self.value() == "aman":
            return queryset.filter(stok__gt=F("batas_minimum"))
        return queryset


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
        "batas_minimum",
    )
    list_filter = ("kategori", "merek", StokStatusFilter)
    search_fields = ("sku", "nama_produk", "merek")
    readonly_fields = ("sku",)

    @admin.display(description="Status", ordering="stok")
    def status_stok(self, obj):
        return "Perlu restock" if obj.stok <= obj.batas_minimum else "Aman"

    @admin.display(description="Nilai Stok", ordering="harga_beli")
    def nilai_stok(self, obj):
        return f"Rp {int(obj.harga_beli * obj.stok):,}".replace(",", ".")


@admin.register(StokProduk)
class StokProdukAdmin(ModelAdmin):
    list_display = (
        "sku",
        "nama_produk",
        "stok",
        "batas_minimum",
        "status_stok",
        "nilai_stok",
    )
    list_filter = (StokStatusFilter, "merek")
    search_fields = ("sku", "nama_produk", "merek")
    readonly_fields = (
        "sku",
        "nama_produk",
        "merek",
        "kategori",
        "ukuran",
        "harga_beli",
        "harga_jual",
        "stok",
        "batas_minimum",
    )

    @admin.display(description="Status", ordering="stok")
    def status_stok(self, obj):
        return "Perlu restock" if obj.stok <= obj.batas_minimum else "Aman"

    @admin.display(description="Nilai Stok", ordering="harga_beli")
    def nilai_stok(self, obj):
        return f"Rp {int(obj.harga_beli * obj.stok):,}".replace(",", ".")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


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

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        tipe = request.GET.get("tipe")
        if tipe in Transaksi.Tipe.values:
            initial["tipe"] = tipe
        return initial

    def delete_queryset(self, request, queryset):
        for transaksi in queryset:
            transaksi.delete()


@admin.register(TransaksiPenjualan)
class TransaksiPenjualanAdmin(TransaksiAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(tipe=Transaksi.Tipe.PENJUALAN)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial["tipe"] = Transaksi.Tipe.PENJUALAN
        return initial


@admin.register(TransaksiPembelian)
class TransaksiPembelianAdmin(TransaksiAdmin):
    def get_queryset(self, request):
        return super().get_queryset(request).filter(tipe=Transaksi.Tipe.PEMBELIAN)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        initial["tipe"] = Transaksi.Tipe.PEMBELIAN
        return initial
