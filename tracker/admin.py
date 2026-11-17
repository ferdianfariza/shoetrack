# tracker/admin.py
from django.contrib import admin
from django import forms
from django.db.models import F
from unfold.admin import ModelAdmin

from .models import (
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


class TransaksiForm(forms.ModelForm):
    harga_satuan = forms.DecimalField(required=False)

    class Meta:
        model = Transaksi
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        produk = cleaned_data.get("produk")
        tipe = cleaned_data.get("tipe")
        harga_satuan = cleaned_data.get("harga_satuan")

        if harga_satuan is None and produk:
            if tipe == Transaksi.Tipe.PENJUALAN:
                cleaned_data["harga_satuan"] = produk.harga_jual
            elif tipe == Transaksi.Tipe.PEMBELIAN:
                supplier = cleaned_data.get("supplier")
                if supplier:
                    harga_satuan = (
                        Transaksi.objects.filter(
                            tipe=Transaksi.Tipe.PEMBELIAN,
                            produk=produk,
                            supplier=supplier,
                        )
                        .order_by("-tanggal", "-id")
                        .values_list("harga_satuan", flat=True)
                        .first()
                    )
                cleaned_data["harga_satuan"] = harga_satuan or produk.harga_beli
        return cleaned_data


@admin.register(Supplier)
class SupplierAdmin(ModelAdmin):
    list_display = ("nama", "telepon", "alamat")
    search_fields = ("nama",)


@admin.register(Produk)
class ProdukAdmin(ModelAdmin):
    list_display = (
        "id",
        "merek",
        "ukuran",
        "harga_beli",
        "harga_jual",
        "stok",
        "batas_minimum",
    )
    list_filter = (StokStatusFilter,)
    search_fields = ("merek",)

    def get_exclude(self, request, obj=None):
        if obj is None:
            return ("harga_jual",)
        return super().get_exclude(request, obj)

    @admin.display(description="Status", ordering="stok")
    def status_stok(self, obj):
        return "Perlu restock" if obj.stok <= obj.batas_minimum else "Aman"

    @admin.display(description="Nilai Stok", ordering="harga_beli")
    def nilai_stok(self, obj):
        return f"Rp {int(obj.harga_beli * obj.stok):,}".replace(",", ".")


@admin.register(StokProduk)
class StokProdukAdmin(ModelAdmin):
    list_display = (
        "id",
        "merek",
        "stok",
        "batas_minimum",
        "status_stok",
        "nilai_stok",
    )
    list_filter = (StokStatusFilter,)
    search_fields = ("merek",)
    readonly_fields = (
        "id",
        "merek",
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
    form = TransaksiForm
    list_display = (
        "kode_transaksi",
        "tanggal",
        "tipe",
        "produk",
        "supplier",
        "kuantitas",
        "harga_satuan",
        "total",
    )
    list_filter = ("tipe", "tanggal")
    search_fields = ("kode_transaksi", "produk__merek")
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
    list_display = tuple(
        field for field in TransaksiAdmin.list_display if field != "supplier"
    )

    exclude = ("supplier",)

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
