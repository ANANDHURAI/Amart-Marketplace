from django.db import models
from accounts.models import Customer
from product.models import Category
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone



class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount = models.PositiveIntegerField()
    quantity = models.PositiveIntegerField(default=1)
    minimum_purchase = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.code




class CustomerCoupon(Coupon):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    is_customer_coupon = models.BooleanField(default=True)




class CategoryOffer(models.Model):
    category = models.ForeignKey(
        Category, related_name="category", on_delete=models.CASCADE
    )
    discount = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(99)]
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Offer for " + self.category.name + " - " + str(self.discount) + "%"





class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


from django.db import models
from django.utils import timezone

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()      
    all_objects = models.Manager()     

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()

