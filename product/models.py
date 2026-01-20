from django.db import models
from django.core.validators import MinValueValidator
from ecom.models import SoftDeleteModel, ApprovedProductManager
from PIL import Image


class Category(SoftDeleteModel):
    name = models.CharField(max_length=50, unique=True)
    image = models.ImageField(upload_to="images/categories")
    description = models.TextField(max_length=511, null=True, blank=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

    def __unicode__(self):
        return self.name


class Product(SoftDeleteModel):
    name = models.CharField(max_length=100)
    description = models.TextField(max_length=511, null=True, blank=True)
    
    main_category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="main_category_products"
    )
    

    subcategories = models.ManyToManyField(
        Category, related_name="subcategory_products", blank=True
    )
    
    mrp = models.PositiveIntegerField(
        validators=[MinValueValidator(1)], null=True, blank=True
    )
    
    is_available = models.BooleanField(default=True)
    slug = models.SlugField(unique=True, max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    last_modified_at = models.DateTimeField(auto_now=True)
    approved = models.BooleanField(default=True)
    approved_objects = ApprovedProductManager()

    def __str__(self):
        return f"is {self.name}"

    def __unicode__(self):
        return self.name




class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name="product_images", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="images/product_images")
    priority = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Image of {self.product.name}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        img = Image.open(self.image.path)
        min_dim = min(img.size)
        crop_box = (
            (img.width - min_dim) // 2,
            (img.height - min_dim) // 2,
            (img.width + min_dim) // 2,
            (img.height + min_dim) // 2,
        )
        img = img.crop(crop_box)

        img = img.resize((400, 400), Image.LANCZOS)

        img.save(self.image.path)



class Inventory(models.Model):
    SIZE_CHOICES = [
        ("S", "Small"),
        ("M", "Medium"),
        ("L", "Large"),
        ("XL", "Extra Large"),
    ]
    product = models.ForeignKey(
        Product, related_name="inventory_sizes", on_delete=models.CASCADE
    )
    size = models.CharField(max_length=2, choices=SIZE_CHOICES, default="S")
    price = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    stock = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} - {self.size} size"

    class Meta:
        verbose_name_plural = "Inventory"

