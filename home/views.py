"""
Home app views: landing, shop listing, and product detail.

All product listings use approved_objects and only show in-stock items.
Query optimization: prefetch_related for images/inventory; batch favourite checks.
"""
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Sum, Q, Min, Max

from product.models import Product, Category, ProductImage, Inventory
from customer.models import FavouriteItem
from aadmin.models import CategoryOffer


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
    Landing page: featured products (max 9) and categories.

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
        .prefetch_related("product_images", "inventory_sizes")[:9]
    )
    _enrich_products_with_display_data(products, request)
    categories = Category.objects.filter(is_deleted=False)

    return render(request, "home/home.html", {
        "products": products,
        "categories": categories,
        "title": "Home",
    })


def shop(request):
    """
    Shop listing with optional search, category filter, and sort.

    Sort/session: POST updates session; GET used for pagination.
    Uses prefetch for product_images and inventory_sizes; batch favourite check.
    """
    title = "Shop"
    sort_by = request.session.get("sort_by", "")
    selected_category = request.session.get("selected_category", "")

    if request.method == "POST":
        sort_by = request.POST.get("sort_by", "")
        selected_category = request.POST.get("selected_category", "")
        request.session["sort_by"] = sort_by
        request.session["selected_category"] = selected_category

    products = (
        Product.approved_objects.filter(main_category__is_deleted=False)
        .filter(
            inventory_sizes__is_active=True,
            inventory_sizes__stock__gt=0,
        )
        .distinct()
    )

    search = request.GET.get("search", "").strip()
    if search:
        products = products.filter(name__icontains=search)
    if selected_category:
        products = products.filter(main_category_id=selected_category)

    if sort_by == "price_asc":
        products = products.annotate(price=Min("inventory_sizes__price")).order_by("price")
    elif sort_by == "price_desc":
        products = products.annotate(price=Max("inventory_sizes__price")).order_by("-price")
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

    products = products.prefetch_related("product_images", "inventory_sizes")
    paginator = Paginator(products, 6)
    paged_products = paginator.get_page(request.GET.get("page"))

    _enrich_products_with_display_data(paged_products, request)
    categories = Category.objects.filter(is_deleted=False)

    return render(request, "home/shop.html", {
        "products": paged_products,
        "categories": categories,
        "title": title,
        "sort_by": sort_by,
        "selected_category": selected_category,
    })


def product_page(request, slug):
    """
    Single product detail: images, inventory, category offer, favourite flag.

    Uses select_related for main_category; one query for CategoryOffer.
    Favourite check only when user is authenticated.
    """
    product = get_object_or_404(
        Product.approved_objects.select_related("main_category"),
        slug=slug,
    )
    product_images = ProductImage.objects.filter(product=product).order_by("priority")
    inventory = Inventory.objects.filter(product=product)

    product.is_favourite = False
    if request.user.is_authenticated:
        product.is_favourite = FavouriteItem.objects.filter(
            customer_id=request.user.pk,
            product=product,
        ).exists()

    offer = 0
    category_offer = CategoryOffer.objects.filter(
        category=product.main_category
    ).values_list("discount", flat=True).first()
    if category_offer is not None:
        offer = category_offer

    return render(request, "home/product-page.html", {
        "product": product,
        "offer": offer,
        "inventory": inventory,
        "product_images": product_images,
        "title": product,
    })


def test_modal_view(request):
    """Placeholder view for modal test template."""
    return render(request, "home/test_modal.html")
    
