"""
Home app views: landing, shop listing, and product detail.

All product listings use approved_objects and only show in-stock items.
Query optimization: prefetch_related for images/inventory; batch favourite checks.
"""
from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Sum, Q, Min, Max
from django.db.models.functions import Lower
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
    title = "Shop"
    
    # 1. Retrieve filter values from Session or POST
    if request.method == "POST":
        sort_by = request.POST.get("sort_by", "")
        selected_category = request.POST.get("selected_category", "")
        min_price = request.POST.get("min_price", "")
        max_price = request.POST.get("max_price", "")
        
        # Store in session for persistence
        request.session["sort_by"] = sort_by
        request.session["selected_category"] = selected_category
        request.session["min_price"] = min_price
        request.session["max_price"] = max_price
    else:
        sort_by = request.session.get("sort_by", "")
        selected_category = request.session.get("selected_category", "")
        min_price = request.session.get("min_price", "")
        max_price = request.session.get("max_price", "")

    # 2. Base Queryset (Optimized)
    products = Product.approved_objects.filter(
        main_category__is_deleted=False,
        inventory_sizes__is_active=True,
        inventory_sizes__stock__gt=0
    ).distinct()

    # 3. Apply Filters
    search = request.GET.get("search", "").strip()
    if search:
        products = products.filter(Q(name__icontains=search) | Q(description__icontains=search))
    
    if selected_category:
        products = products.filter(main_category_id=selected_category)

    # Price Range Filter Logic
    if min_price:
        products = products.filter(inventory_sizes__price__gte=min_price)
    if max_price:
        products = products.filter(inventory_sizes__price__lte=max_price)

    # 4. Apply Sorting
        
    if sort_by == "price_asc":
        products = products.annotate(min_p=Min("inventory_sizes__price")).order_by("min_p")
    elif sort_by == "price_desc":
        products = products.annotate(max_p=Max("inventory_sizes__price")).order_by("-max_p")
    elif sort_by == "popularity":
        products = products.annotate(total_sold=Sum("orderitem__quantity")).order_by("-total_sold")
    elif sort_by == "new":
        products = products.order_by("-created_at")
    elif sort_by == "name_asc":
        # Industry level: sort by lowercase name to avoid Case Sensitivity issues
        products = products.annotate(name_lower=Lower('name')).order_by("name_lower")
    elif sort_by == "name_desc":
        products = products.annotate(name_lower=Lower('name')).order_by("-name_lower")
    else:
        # Default sort (newest first is usually better than -id)
        products = products.order_by("-created_at")

    # 5. Performance Optimization & Pagination
    products = products.prefetch_related("product_images", "inventory_sizes")
    paginator = Paginator(products, 9) # Increased per page for better UI
    page_number = request.GET.get("page")
    paged_products = paginator.get_page(page_number)

    _enrich_products_with_display_data(paged_products, request)
    categories = Category.objects.filter(is_deleted=False)

    context = {
        "products": paged_products,
        "categories": categories,
        "title": title,
        "sort_by": sort_by,
        "selected_category": selected_category,
        "min_price": min_price,
        "max_price": max_price,
    }
    return render(request, "home/shop.html", context)






def product_page(request, slug):
    product = get_object_or_404(
        Product.approved_objects.select_related("main_category"),
        slug=slug,
    )
    product_images = ProductImage.objects.filter(product=product).order_by("priority")
    inventory = Inventory.objects.filter(product=product, is_active=True)

    # Get Category Discount
    discount = CategoryOffer.objects.filter(
        category=product.main_category
    ).values_list("discount", flat=True).first() or 0

    # Calculate discounted price for each size
    for item in inventory:
        if discount > 0:
            item.discounted_price = int(item.price * (1 - discount / 100))
        else:
            item.discounted_price = item.price

    product.is_favourite = False
    if request.user.is_authenticated:
        product.is_favourite = FavouriteItem.objects.filter(
            customer_id=request.user.pk,
            product=product,
        ).exists()

    return render(request, "home/product-page.html", {
        "product": product,
        "offer": discount,
        "inventory": inventory,
        "product_images": product_images,
        "title": product.name,
    })