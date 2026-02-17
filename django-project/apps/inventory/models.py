from django.db import models

class Product(models.Model):
    sku = models.CharField(max_length=60, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

class Warehouse(models.Model):
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)

class StockItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    warehouse = models.ForeignKey(Warehouse, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=12, decimal_places=3, default=0)

class StockMovement(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    from_warehouse = models.ForeignKey(Warehouse, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    to_warehouse = models.ForeignKey(Warehouse, related_name='+', on_delete=models.SET_NULL, null=True, blank=True)
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    date = models.DateTimeField(auto_now_add=True)
    reference = models.CharField(max_length=200, blank=True)