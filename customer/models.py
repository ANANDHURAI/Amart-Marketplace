from django.db import models
from product.models import Product, Inventory
from accounts.models import Customer
from aadmin.models import Coupon
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator


class Cart(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.customer.first_name}'s Cart"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    def __str__(self):
        return f"{self.quantity} of {self.product.name}"


class Address(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    name = models.CharField(
        max_length=255,
        validators=[
            RegexValidator(
                regex=r"^[a-zA-Z]+(?:[\s-][a-zA-Z]+)*$", message="Enter a valid name."
            )
        ],
    )
    mobile = models.CharField(
        max_length=10,
        validators=[
            RegexValidator(regex=r"^[6-9]\d{9}$", message="Invalid mobile number")
        ],
    )

    pincode = models.CharField(
        max_length=6,
        validators=[
            RegexValidator(regex=r"^[1-9]\d{5}$", message="Invalid pincode")
        ],
    )

    state = models.CharField(max_length=255)
    building = models.CharField(max_length=255)
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=255, null=True, blank=True)
    district = models.CharField(max_length=255)
    address_text = models.TextField(
        null=True, blank=True
    )  # to store the whole address as text
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}, {self.building}, {self.street}, {self.district}, {self.state}"


class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "pending"),
        ("confirmed", "confirmed"),
        ("shipped", "shipped"),
        ("delivered", "delivered"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    address = models.TextField()
    total_amount = models.PositiveIntegerField()
    discount = models.PositiveIntegerField(null=True, blank=True)
    offer = models.PositiveIntegerField(null=True, blank=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    payment_method = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.id}"


class OrderItem(models.Model):

    STATUS_CHOICES = [
        ("pending", "pending"),
        ("confirmed", "confirmed"),
        ("shipped", "shipped"),
        ("delivered", "delivered"),
        ("cancelled", "cancelled"),
    ]
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    inventory = models.ForeignKey(Inventory, on_delete=models.CASCADE, default=1)
    size = models.CharField(max_length=2, default="S")
    price = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    def __str__(self):
        return f"{self.quantity} x{self.product.name}"





class FavouriteItem(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.customer.first_name}'s favourite {self.product.name}"




class Wallet(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE)
    balance = models.PositiveIntegerField(default=0)
