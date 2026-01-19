from django.shortcuts import render, redirect
from product.models import Product, Category, ProductImage, Inventory
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.db.models import F, Sum, Q , Min ,Max
from customer.models import OrderItem, FavouriteItem
from aadmin.models import CategoryOffer
from django.db.models import Min

def home(request):
    title = "Home"
    
    products = (
        Product.approved_objects
        .filter(
            is_available=True,
            main_category__is_deleted=False,
            inventory_sizes__is_active=True,   
            inventory_sizes__stock__gt=0       
        )
        .distinct()
        .prefetch_related("product_images", "inventory_sizes")[:9]
    )

    for product in products:
       
        product.primary_image = (
            product.product_images.filter(priority=1).first()
        )

        # Only valid inventories for this product
        product.available_inventories = product.inventory_sizes.filter(
            is_active=True,
            stock__gt=0
        )

        # Lowest available price
        product.shop_price = (
            product.available_inventories.aggregate(
                Min("price")
            )["price__min"]
        )

        # Favourite check
        if request.user.is_authenticated:
            product.is_favourite = FavouriteItem.objects.filter(
                customer__id=request.user.id,
                product=product
            ).exists()
        else:
            product.is_favourite = False

    categories = Category.objects.filter(is_deleted=False)

    context = {
        "products": products,
        "categories": categories,
        "title": title,
    }
    return render(request, "home/home.html", context)



def shop(request):
    title = "Shop"

    sort_by = request.session.get("sort_by", "")
    selected_category = request.session.get("selected_category", "")

    products = Product.approved_objects.filter(
        main_category__is_deleted=False    
    )

    # Search
    if request.GET.get("search"):
        products = products.filter(
            name__icontains=request.GET["search"]
        )

    if request.method == "POST":
        sort_by = request.POST.get("sort_by", "")
        selected_category = request.POST.get("selected_category", "")

        request.session["sort_by"] = sort_by
        request.session["selected_category"] = selected_category

    # Category filter
    if selected_category:
        products = products.filter(main_category_id=selected_category)
    
    products = products.filter(
        inventory_sizes__is_active=True,
        inventory_sizes__stock__gt=0
    ).distinct()
    
    # Sorting
    if sort_by == "price_asc":
        products = products.annotate(
            price=Min("inventory_sizes__price")
        ).order_by("price")

    elif sort_by == "price_desc":
        products = products.annotate(
            price=Max("inventory_sizes__price")
        ).order_by("-price")

    elif sort_by == "new":
        products = products.order_by("-created_at")

    elif sort_by == "name_asc":
        products = products.order_by("name")

    elif sort_by == "name_desc":
        products = products.order_by("-name")

    elif sort_by == "popularity":
        products = products.annotate(
            total_sold=Sum("orderitem__quantity")
        ).order_by("-total_sold")

    
    products = products.prefetch_related(
        "product_images", "inventory_sizes"
    )

    paginator = Paginator(products, 6)
    paged_products = paginator.get_page(request.GET.get("page"))

    categories = Category.objects.filter(is_deleted=False)
    
    for product in paged_products:
        product.primary_image = (
            product.product_images
            .order_by("priority")
            .first()
        )
        
        product.available_inventories = product.inventory_sizes.filter(
            is_active=True,
            stock__gt=0
        )

        product.shop_price = (
            product.available_inventories.aggregate(
                Min("price")
            )["price__min"] or 0
        )

        

    context = {
        "products": paged_products,
        "categories": categories,
        "title": title,
        "sort_by": sort_by,
        "selected_category": selected_category,
    }
    return render(request, "home/shop.html", context)





def product_page(request, slug):
    product = Product.approved_objects.get(slug=slug)
    title = product
    product_images = ProductImage.objects.filter(product=product).order_by("priority")
    inventory = Inventory.objects.filter(product=product)
    print(product)
    if FavouriteItem.objects.filter(
        customer__id=request.user.id, product=product
    ).exists():
        product.is_favourite = True
    else:
        product.is_favourite = False

    offer = 0
    if CategoryOffer.objects.filter(category=product.main_category).exists():
        category_offer = CategoryOffer.objects.get(category=product.main_category)
        offer = category_offer.discount

    context = {
        "product": product,
        "offer": offer,
        "inventory": inventory,
        "product_images": product_images,
        "title": title,
    }
    return render(request, "home/product-page.html", context)


def test_modal_view(request):
    return render(request, "home/test_modal.html")




