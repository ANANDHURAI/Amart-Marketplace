"""
Home app views: landing, shop listing, and product detail.

All product listings use approved_objects and only show in-stock items.
Query optimization: prefetch_related for images/inventory; batch favourite checks.
"""


from django.shortcuts import render
from django.core.paginator import Paginator
from django.db.models import Sum, Q, Min
from django.db.models.functions import Lower

from product.models import Product, Category
from customer.models import FavouriteItem


def _enrich_products_with_display_data(products, request):
    """
    Attach primary_image, available_inventories, shop_price, and is_favourite
    to each product. Uses prefetched product_images and inventory_sizes;
    runs one batch query for favourites when user is authenticated.
    """
    product_ids = [p.id for p in products]
    favourite_product_ids = set()
    if request.user.is_authenticated and product_ids:
        favourite_product_ids = set(
            FavouriteItem.objects.filter(
                customer_id=request.user.pk,
                product_id__in=product_ids,
            ).values_list("product_id", flat=True)
        )

    for product in products:
        product.primary_image = product.product_images.order_by("priority").first()
        product.available_inventories = product.inventory_sizes.filter(
            is_active=True, stock__gt=0
        )
        product.shop_price = (
            product.available_inventories.aggregate(min_price=Min("price"))["min_price"]
            or 0
        )
        product.is_favourite = product.id in favourite_product_ids


def home(request):
    """
    Landing page: featured products and categories.

    Uses prefetch for product_images and inventory_sizes; single batch query
    for favourite flags when the user is authenticated.
    """
    products = (
        Product.approved_objects.filter(
            is_available=True,
            main_category__is_deleted=False,
            inventory_sizes__is_active=True,
            inventory_sizes__stock__gt=0,
        )
        .distinct()
        .prefetch_related("product_images", "inventory_sizes")
        .order_by('-id')[:8]
    )
    
    _enrich_products_with_display_data(products, request)
    
    categories = Category.objects.filter(is_deleted=False)

    return render(request, "home/home.html", {
        "products": products,
        "categories": categories,
        "title": "Home",
    })





def shop(request):
    title = "Shop"

    if request.method == "POST":
        sort_by = request.POST.get("sort_by", "").strip()
        selected_category = request.POST.get(
            "selected_category", ""
        ).strip()
        min_price = request.POST.get("min_price", "").strip()
        max_price = request.POST.get("max_price", "").strip()

        request.session["sort_by"] = sort_by
        request.session["selected_category"] = selected_category
        request.session["min_price"] = min_price
        request.session["max_price"] = max_price

    else:
        sort_by = request.session.get("sort_by", "")
        selected_category = request.session.get(
            "selected_category", ""
        )
        min_price = request.session.get("min_price", "")
        max_price = request.session.get("max_price", "")

    try:
        min_price_value = int(min_price) if min_price else None
    except (TypeError, ValueError):
        min_price_value = None
        min_price = ""

    try:
        max_price_value = int(max_price) if max_price else None
    except (TypeError, ValueError):
        max_price_value = None
        max_price = ""


    invalid_price_range = (
        min_price_value is not None
        and max_price_value is not None
        and min_price_value > max_price_value
    )

    products = Product.approved_objects.filter(
        is_available=True,
        main_category__is_deleted=False,
        inventory_sizes__is_active=True,
        inventory_sizes__stock__gt=0,
    ).distinct()
    
    

   
    search = request.GET.get("search", "").strip()

    if search:
        products = products.filter(
            Q(name__icontains=search)
            | Q(description__icontains=search)
        )

    if selected_category:
        products = products.filter(
            main_category_id=selected_category
        )

    products = products.annotate(
        shop_price_db=Min(
            "inventory_sizes__price",
            filter=Q(
                inventory_sizes__is_active=True,
                inventory_sizes__stock__gt=0,
            ),
        )
    )

   
    if invalid_price_range:
        products = products.none()

    else:
        if min_price_value is not None:
            products = products.filter(
                shop_price_db__gte=min_price_value
            )

        if max_price_value is not None:
            products = products.filter(
                shop_price_db__lte=max_price_value
            )

    if sort_by == "price_asc":
        products = products.order_by(
            "shop_price_db"
        )

    elif sort_by == "price_desc":
        products = products.order_by(
            "-shop_price_db"
        )

    elif sort_by == "popularity":
        products = products.annotate(
            total_sold=Sum("orderitem__quantity")
        ).order_by("-total_sold")

    elif sort_by == "new":
        products = products.order_by("-created_at")

    elif sort_by == "name_asc":
        products = products.annotate(
            name_lower=Lower("name")
        ).order_by("name_lower")

    elif sort_by == "name_desc":
        products = products.annotate(
            name_lower=Lower("name")
        ).order_by("-name_lower")

    else:
        products = products.order_by("-created_at")

    products = products.prefetch_related(
        "product_images",
        "inventory_sizes",
    ).distinct()

  
    paginator = Paginator(products, 9)

    page_number = request.GET.get("page")
    paged_products = paginator.get_page(page_number)

    _enrich_products_with_display_data(
        paged_products,
        request
    )

   
    categories = Category.objects.filter(
        is_deleted=False
    )

    context = {
        "products": paged_products,
        "categories": categories,
        "title": title,
        "sort_by": sort_by,
        "selected_category": selected_category,
        "min_price": min_price,
        "max_price": max_price,
    }

    return render(
        request,
        "home/shop.html",
        context
    )



