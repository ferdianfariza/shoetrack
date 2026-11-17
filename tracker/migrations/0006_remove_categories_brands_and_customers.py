from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0005_transaksipembelian_transaksipenjualan"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="produk",
            name="kategori",
        ),
        migrations.RemoveField(
            model_name="produk",
            name="merek",
        ),
        migrations.RemoveField(
            model_name="transaksi",
            name="pelanggan",
        ),
        migrations.AlterField(
            model_name="produk",
            name="sku",
            field=models.CharField(editable=False, max_length=100, unique=True),
        ),
        migrations.DeleteModel(
            name="Kategori",
        ),
        migrations.DeleteModel(
            name="Pelanggan",
        ),
    ]
