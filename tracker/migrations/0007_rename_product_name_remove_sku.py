from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("tracker", "0006_remove_categories_brands_and_customers"),
    ]

    operations = [
        migrations.RenameField(
            model_name="produk",
            old_name="nama_produk",
            new_name="merek",
        ),
        migrations.RemoveField(
            model_name="produk",
            name="sku",
        ),
    ]
