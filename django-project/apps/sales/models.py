from django.db import models
from apps.inventory.models import Product

class Customer(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)

class SalesOrder(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT)
    order_date = models.DateField()
    status = models.CharField(max_length=30, default='draft')

class SalesOrderLine(models.Model):
    order = models.ForeignKey(SalesOrder, related_name='lines', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    qty = models.DecimalField(max_digits=12, decimal_places=3)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

class Invoice(models.Model):
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT)
    invoice_date = models.DateField()
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)