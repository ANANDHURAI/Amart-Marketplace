"""Admin app views: dashboard, catalog management, orders, coupons, offers, inventory."""

from django.shortcuts import render, redirect, get_object_or_404
from accounts.models import Customer, Account
from product.models import Category, Product, Inventory, ProductImage
from customer.models import OrderItem, Order
from aadmin.models import Coupon, CategoryOffer
from django.utils.text import slugify
from django.contrib import messages
from django.http import HttpResponse
from datetime import datetime, timedelta, date
from django.db.models import F, Sum
from django.db.models.functions import Coalesce
from django.db import transaction
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
import base64
from uuid import uuid4


def admin_login_required(func):
    """Decorator restricting access to authenticated superadmin users."""

    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_superadmin:
            target_url = request.build_absolute_uri()
            request.session["admin_target_url"] = target_url
            return redirect("admin_login")
        return func(request, *args, **kwargs)

    return wrapper





@admin_login_required
def admin_profile(request):
    title = "Admin Profile"
    current_page = "admin_profile"

    admin = request.user

    context = {
        "title": title,
        "current_page": current_page,
        "admin": admin,
    }
    return render(request, "aadmin/admin-profile.html", context)





@admin_login_required
def edit_admin_profile(request):
    title = "Edit Admin Profile"
    current_page = "admin_profile"

    admin = request.user

    if request.method == "POST":
        admin.first_name = request.POST.get("first_name")
        admin.last_name = request.POST.get("last_name")
        admin.mobile = request.POST.get("mobile")

        if request.FILES.get("profile_image"):
            admin.profile_image = request.FILES.get("profile_image")

        admin.save()
        messages.success(request, "Profile updated successfully")
        return redirect("admin_profile")

    context = {
        "title": title,
        "current_page": current_page,
        "admin": admin,
    }
    return render(request, "aadmin/edit-admin-profile.html", context)






@admin_login_required
def admin_dashboard(request):
    title = "Dashboard"
    current_page = "admin_dashboard"

    top_products_info = (
        OrderItem.objects.filter(product__isnull=False)
        .values("product__id", "product__name")
        .annotate(total_quantity=Coalesce(Sum("quantity"), 0))
        .order_by("-total_quantity")[:5]
    )

    top_products = []

    for product_info in top_products_info:
        try:
            product = get_object_or_404(Product, id=product_info["product__id"])
            primary_image = product.product_images.filter(priority=1).first()
            product.primary_image = primary_image
            product.total_quantity = product_info["total_quantity"]
            top_products.append(product)
        except:
            continue

    top_categories_info = (
        Product.objects.filter(main_category__isnull=False)
        .values("main_category__id")
        .annotate(total_quantity=Coalesce(Sum("orderitem__quantity"), 0))
        .order_by("-total_quantity")[:10]
    )

    top_categories = []

    for category_info in top_categories_info:
        try:
            category = get_object_or_404(
                Category, id=category_info["main_category__id"]
            )
            category.total_quantity = category_info["total_quantity"]
            top_categories.append(category)
        except:
          
            continue

    # Line chart for revenue for last year

    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    months = []
    revenue_by_month = []

    current_date = start_date
    while current_date <= end_date:
        month_start_date = current_date.replace(day=1)
        next_month_start_date = (
            current_date.replace(day=1) + timedelta(days=32)
        ).replace(day=1)

        month_label = month_start_date.strftime("%b")

        total_revenue = Order.objects.filter(
            created_at__gte=month_start_date, created_at__lt=next_month_start_date
        ).aggregate(total=Sum("total_amount"))["total"]

        months.append(month_label)
        revenue_by_month.append(total_revenue or 0)

        current_date = next_month_start_date

    total_yearly_revenue = sum(revenue_by_month)

    # Line chart for the month

    today = date.today()
    start_date = today.replace(day=1)
    end_date = today

    days = []
    revenue_by_day = []

    current_date = start_date
    while current_date <= end_date:
        total_revenue = Order.objects.filter(created_at__date=current_date).aggregate(
            total=Sum("total_amount")
        )["total"]

        days.append(current_date.day)
        revenue_by_day.append(total_revenue or 0)

        current_date += timedelta(days=1)

    total_monthly_revenue = sum(revenue_by_day)

    # To count the orders according to the status
    status_counts = {
        "pending": OrderItem.objects.filter(status="pending").count(),
        "confirmed": OrderItem.objects.filter(status="confirmed").count(),
        "shipped": OrderItem.objects.filter(status="shipped").count(),
        "delivered": OrderItem.objects.filter(status="delivered").count(),
        "cancelled": OrderItem.objects.filter(status="cancelled").count(),
    }

    context = {
        "current_page": current_page,
        "title": title,
        "top_products": top_products,
        "top_categories": top_categories,
        "months": months,
        "revenue_by_month": revenue_by_month,
        "days": days,
        "revenue_by_day": revenue_by_day,
        "total_yearly_revenue": total_yearly_revenue,
        "total_monthly_revenue": total_monthly_revenue,
        "status_counts": status_counts,
        "total_orders": OrderItem.objects.all().count(),
    }
    return render(request, "aadmin/admin-dashboard.html", context)


@admin_login_required
def customer_list(request):
    title = "Customers"
    current_page = "customer_list"

    customers = Customer.objects.all()
    request.session["selection"] = "all"

    if request.method == "POST":
        filter_option = request.POST.get("filter_option")

        if filter_option == "banned":
            customers = Customer.objects.filter(is_active=False)
            request.session["selection"] = "ban"

        elif filter_option == "active":
            customers = Customer.objects.filter(is_active=True)
            request.session["selection"] = "active"

    context = {
        "customers": customers,
        "current_page": current_page,
        "title": title,
    }
    return render(request, "aadmin/customer-list.html", context)



@admin_login_required
def customer_approval(request, pk):
    customer = Customer.objects.get(pk=pk)
    customer.is_active = not customer.is_active
    customer.save()

    if customer.is_active:
        messages.success(request, f"{customer.email} has been unblocked.")
    else:
        messages.success(request, f"{customer.email} has been blocked.")

    return redirect("customer_list")


@admin_login_required
def category_list(request):
    title = "Categories"
    current_page = "category_list"

    search_query = request.GET.get("search", "")
    filter_option = request.GET.get("filter_option", "listed_categories")

    if filter_option == "deleted_categories":
        categories = Category.all_objects.filter(is_deleted=True).order_by("name")
        request.session["selection"] = "deleted_categories"
    else:
        categories = Category.objects.all().order_by("name")
        request.session["selection"] = "listed_categories"

    if search_query:
        categories = categories.filter(name__icontains=search_query)

    for category in categories:
        category.count = Product.all_objects.filter(
            main_category=category
        ).count()

    paginator = Paginator(categories, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "categories": page_obj,
        "title": title,
        "current_page": current_page,
        "search_query": search_query,
        "filter_option": filter_option,
    }
    return render(request, "aadmin/category-list.html", context)




import base64
from django.core.files.base import ContentFile

@admin_login_required
def add_category(request):
    title = "New Category"
    current_page = "add_category"

    if request.method == "POST":
        category_name = request.POST.get("category_name", "").strip()
        category_description = request.POST.get("category_description", "").strip()
        cropped_image = request.POST.get("cropped_image")


        if not category_name or len(category_name) < 3:
            messages.error(request, "Category name must be at least 3 characters")
            return redirect("add_category")

        if not category_name.replace(" ", "").isalpha():
            messages.error(request, "Category name must contain only letters")
            return redirect("add_category")

        if Category.objects.filter(name__iexact=category_name).exclude(
                id=getattr(request, "category_id", None)
            ).exists():
            messages.error(request, "Category already exists")
            return redirect("add_category")

        
        if not cropped_image:
            messages.error(request, "Please upload and crop an image")
            return redirect("add_category")

     
        try:
            format, imgstr = cropped_image.split(";base64,")
            ext = format.split("/")[-1]
            image_file = ContentFile(
                base64.b64decode(imgstr),
                name=f"{slugify(category_name)}.{ext}"
            )
        except Exception:
            messages.error(request, "Invalid image data")
            return redirect("add_category")

        Category.objects.create(
            name=category_name.title(),
            description=category_description,
            image=image_file,
            slug=slugify(category_name),
        )

        messages.success(request, "Category added successfully")
        return redirect("category_list")

    context = {"title": title, "current_page": current_page}
    return render(request, "aadmin/category-form.html", context)





@admin_login_required
def edit_category(request, slug):
    title = f"{slug.capitalize()} | Edit Category"
    category = Category.objects.get(slug=slug)
    image_url = category.image.url if category.image else None

    if request.method == "POST":
        category_name = request.POST.get("category_name").title().strip()
        category_description = request.POST.get("category_description").strip()
        category_image = request.FILES.get("category_image")
        new_slug = slugify(category_name)

      
        if (
            category.name == category_name and
            category.description == category_description and
            not category_image
        ):
            messages.info(request, "No changes were made")
            return redirect("edit_category", slug=slug)

       
        if Category.objects.filter(name=category_name).exclude(id=category.id).exists():
            messages.error(request, "Category already exists")
            return redirect("edit_category", slug=slug)

        
        category.name = category_name
        category.description = category_description
        category.slug = new_slug

        if category_image:
            category.image = category_image

        category.save()
        messages.success(request, "Category updated successfully")
        return redirect("category_list")

    context = {
        "title": title,
        "category": category,
        "image_url": image_url,
    }
    return render(request, "aadmin/category-form.html", context)




@admin_login_required
def delete_category(request, slug):
    category = get_object_or_404(Category, slug=slug)
    category.delete()  
    return redirect("category_list")



@admin_login_required
def restore_category(request, slug):
    category = Category.all_objects.get(slug=slug)

    category.restore()

    Product.all_objects.filter(main_category=category).update(
        is_deleted=False,
        deleted_at=None
    )

    return redirect("category_list")




@admin_login_required
def product_list(request):
    title = "Products"
    current_page = "product_list"

    products = (
        Product.objects
        .all()
        .prefetch_related("product_images")
        .order_by("-created_at")
    )

    request.session["selection"] = "all"

    if request.method == "POST":
        filter_option = request.POST.get("filter_option")
        if filter_option == "awaiting_listing":
            products = products.filter(approved=False)
            request.session["selection"] = "awaiting_listing"
        elif filter_option == "listed_products":
            products = products.filter(approved=True)
            request.session["selection"] = "listed_products"

    search_query = request.GET.get("search", "")
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(mrp__icontains=search_query)
        )

    paginator = Paginator(products, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    for product in page_obj:
        inventory = Inventory.objects.filter(product=product)
        product.total_stock = sum(inv.stock for inv in inventory)

        product.primary_image = (
            product.product_images
            .order_by("priority")
            .first()
        )

    context = {
        "products": page_obj,
        "current_page": current_page,
        "title": title,
        "search_query": search_query,
    }
    return render(request, "aadmin/product-list.html", context)






@admin_login_required
def product_form(request, product_id=None):
    product = None
    is_edit = False

    if product_id:
        product = get_object_or_404(Product, id=product_id)
        is_edit = True

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        description = request.POST.get("description", "").strip()
        category_id = request.POST.get("category")

        cropped_images = [
            request.POST.get("cropped_image_1"),
            request.POST.get("cropped_image_2"),
            request.POST.get("cropped_image_3"),
        ]

      
        if not name or len(name) < 3:
            messages.error(request, "Product name must be at least 3 characters")
            return redirect(
                "edit_product", product_id=product.id
            ) if is_edit else redirect("add_product")

        if not category_id or not Category.objects.filter(id=category_id).exists():
            messages.error(request, "Please select a valid category")
            return redirect(
                "edit_product", product_id=product.id
            ) if is_edit else redirect("add_product")

        if not is_edit and any(not img for img in cropped_images):
            messages.error(request, "Please upload and crop all 3 product images")
            return redirect("add_product")

       
        if not is_edit:
            product = Product.objects.create(
                name=name,
                description=description,
                main_category_id=category_id,
                slug=slugify(name),
                is_available=request.POST.get("is_available") == "on",
                approved=request.POST.get("approved") == "on",
            )
        else:
            product.name = name
            product.description = description
            product.main_category_id = category_id
            product.slug = slugify(name)
            product.is_available = request.POST.get("is_available") == "on"
            product.approved = request.POST.get("approved") == "on"
            product.save()

        
        for img_data in cropped_images:
            if not img_data:
                continue

            fmt, imgstr = img_data.split(";base64,")
            ext = fmt.split("/")[-1]

            image_file = ContentFile(
                base64.b64decode(imgstr),
                name=f"{product.slug}-{uuid4()}.{ext}"
            )

            ProductImage.objects.create(product=product, image=image_file)

        messages.success(
            request,
            "Product updated successfully" if is_edit else "Product added successfully"
        )
        return redirect("product_list")

    
    categories = Category.objects.all()
    existing_images = product.product_images.all() if product else []

    return render(request, "aadmin/product-form.html", {
        "product": product,
        "categories": categories,
        "is_edit": is_edit,
        "existing_images": existing_images,
    })





def remove_product_image(request, image_id):
    image = get_object_or_404(ProductImage, id=image_id)
    if request.method == "POST":
        image.delete()
        messages.success(request, "Image removed successfully.")
    return redirect("edit_product", product_id=image.product.id)


def delete_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.delete()
    messages.success(request, "Product deleted successfully.")
    return redirect("product_list")


@admin_login_required
def product_approval(request, pk):
    product = Product.objects.get(pk=pk)
    product.approved = not product.approved
    product.save()
    return redirect("product_list")






@admin_login_required
def order_list(request):
    title = "Orders"
    current_page = "order_list"

    filter_option = request.GET.get("filter_option", "all")
    search_query = request.GET.get("search", "")

    # Filter orders based on search query
    order_items = OrderItem.objects.all().select_related(
        "order", "product", "inventory", "order__customer"
    ).order_by('-id') 

    if search_query:
        order_items = order_items.filter(product__name__icontains=search_query)

    # Filter orders based on status
    if filter_option != "all":
        order_items = order_items.filter(status=filter_option)

    paginator = Paginator(order_items, 5)
    page = request.GET.get("page")

    try:
        order_items = paginator.page(page)
    except PageNotAnInteger:
        order_items = paginator.page(1)
    except EmptyPage:
        order_items = paginator.page(paginator.num_pages)

    context = {
        "order_items": order_items,
        "current_page": current_page,
        "title": title,
        "search_query": search_query,
        "filter_option": filter_option,
    }
    return render(request, "aadmin/order-list.html", context=context)






@admin_login_required
def admin_order_detail(request, order_id):
    title = "Order Details"
    current_page = "order_list"

    order = get_object_or_404(
        Order.objects.select_related("customer", "coupon"),
        id=order_id
    )

    order_items = (
        OrderItem.objects
        .filter(order=order)
        .select_related("product", "inventory")
    )

    context = {
        "order": order,
        "order_items": order_items,
        "title": title,
        "current_page": current_page,
    }
    return render(request, "aadmin/order-detail.html", context)







@admin_login_required
def update_order_status(request, order_item_id):
    if request.method == "POST":
        new_status = request.POST.get("new_status")
        order_item = get_object_or_404(OrderItem, id=order_item_id)
        order_item.status = new_status
        order_item.save()
        messages.success(
            request, f"Status for order item {order_item_id} updated to {new_status}"
        )
    return redirect("order_list")




@admin_login_required
def sales_report(request):
    title = "Sales Report"
    current_page = "sales_report"

    start_date = datetime.now() - timedelta(days=30)
    end_date = datetime.now()
    request.session["selection"] = "1_month"

    if request.method == "POST":
        filter_option = request.POST.get("filter_option")

        if filter_option == "today":
            start_date = datetime.now() - timedelta(days=1)
            request.session["selection"] = "today"
        elif filter_option == "1_week":
            start_date = datetime.now() - timedelta(days=7)
            request.session["selection"] = "1_week"
        elif filter_option == "1_month":
            start_date = datetime.now() - timedelta(days=30)
            request.session["selection"] = "1_month"
        elif filter_option == "6_months":
            start_date = datetime.now() - timedelta(days=180)
            request.session["selection"] = "6_months"
        elif filter_option == "1_year":
            start_date = datetime.now() - timedelta(days=360)
            request.session["selection"] = "1_year"
        elif "custom_date" in request.POST:

            start_date_str = request.POST.get("start_date")
            end_date_str = request.POST.get("end_date")

            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
            except ValueError:
                messages.error(request, "Invalid date format.")
                return redirect("sales_report")

            if start_date > end_date:
                messages.error(request, "Start date cannot be after end date!")
                return redirect("sales_report")
            if end_date > datetime.now():
                messages.error(request, "End date cannot be in the future!")
                return redirect("sales_report")

            request.session["selection"] = "custom"

    orders = Order.objects.filter(created_at__range=[start_date, end_date]).order_by(
        "-created_at"
    )
    order_items = OrderItem.objects.filter(order__in=orders).annotate(
        order_created_at=F("order__created_at")
    )
    order_items = order_items.order_by("-order_created_at")

    paginator = Paginator(order_items, 10)
    page = request.GET.get("page")
    try:
        order_items_paginated = paginator.page(page)
    except PageNotAnInteger:
        order_items_paginated = paginator.page(1)
    except EmptyPage:
        order_items_paginated = paginator.page(paginator.num_pages)

    overall_amount = sum(item.inventory.price * item.quantity for item in order_items)
    overall_count = order_items.count()

    start_date_str = start_date.strftime("%d-%m-%Y")
    end_date_str = end_date.strftime("%d-%m-%Y")
    pdf_name = f"amart-sales-report-{start_date_str}-{end_date_str}"

    context = {
        "order_items": order_items_paginated,
        "current_page": current_page,
        "title": title,
        "start_date": start_date,
        "end_date": end_date,
        "pdf_name": pdf_name,
        "overall_amount": overall_amount,
        "overall_count": overall_count,
        "paginator": paginator,
        "page_obj": order_items_paginated,
    }

    return render(request, "aadmin/sales-report.html", context=context)




@admin_login_required
def coupon_list(request):
    title = "Coupons"
    current_page = "coupon_list"
    coupons = Coupon.objects.all().order_by("-created_at")
    request.session["selection"] = "all_coupons"

    if request.method == "POST":
        filter_option = request.POST.get("filter_option")
        if filter_option == "active_coupons":
            coupons = Coupon.objects.filter(is_active=True)
            request.session["selection"] = "active_coupons"
        elif filter_option == "inactive_coupons":
            coupons = Coupon.objects.filter(is_active=False)
            request.session["selection"] = "inactive_coupons"
        elif filter_option == "expired_coupons":
            coupons = Coupon.objects.filter(quantity=0)
            request.session["selection"] = "expired_coupons"

    # Pagination
    paginator = Paginator(coupons, 2) 
    page = request.GET.get("page")

    try:
        coupons_page = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        coupons_page = paginator.page(1)
    except EmptyPage:
        # If page is out of range deliver last page of results.
        coupons_page = paginator.page(paginator.num_pages)

    context = {
        "title": title,
        "current_page": current_page,
        "coupons": coupons_page,
        "paginator": paginator,
    }
    return render(request, "aadmin/coupon-list.html", context)



def validate_coupon_fields(code, discount, quantity, minimum_purchase):
    errors = []

    if not code:
        errors.append("Coupon code is required.")
    elif len(code) < 4:
        errors.append("Coupon code must be at least 4 characters.")

    try:
        discount = int(discount)
        if discount <= 0:
            errors.append("Discount must be greater than zero.")
    except:
        errors.append("Enter a valid discount amount.")

    try:
        quantity = int(quantity)
        if quantity < 1:
            errors.append("Quantity must be at least 1.")
    except:
        errors.append("Enter a valid quantity.")

    try:
        minimum_purchase = int(minimum_purchase)
        if minimum_purchase <= 0:
            errors.append("Minimum purchase must be greater than zero.")
    except:
        errors.append("Enter a valid minimum purchase amount.")

    if isinstance(discount, int) and isinstance(minimum_purchase, int):
        if discount >= minimum_purchase:
            errors.append(
                "Discount amount must be less than minimum purchase amount."
            )

    return errors



@admin_login_required
def add_coupon(request):
    title = "New Coupon"
    current_page = "add_coupon"

    if request.method == "POST":
        code = request.POST.get("code", "").upper().strip()
        discount = request.POST.get("discount")
        quantity = request.POST.get("quantity")
        minimum_purchase = request.POST.get("minimum_purchase")
        active = request.POST.get("active") == "1"

        errors = validate_coupon_fields(
            code, discount, quantity, minimum_purchase
        )

        if Coupon.objects.filter(code=code).exists():
            errors.append("This coupon code already exists.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("add_coupon")

        Coupon.objects.create(
            code=code,
            discount=int(discount),
            quantity=int(quantity),
            minimum_purchase=int(minimum_purchase),
            is_active=active,
        )

        messages.success(request, "Coupon added successfully.")
        return redirect("coupon_list")

    return render(request, "aadmin/coupon-form.html", {
        "title": title,
        "current_page": current_page
    })




@admin_login_required
def edit_coupon(request, id):
    coupon = Coupon.objects.get(id=id)

    if request.method == "POST":
        code = request.POST.get("code", "").upper().strip()
        discount = request.POST.get("discount")
        quantity = request.POST.get("quantity")
        minimum_purchase = request.POST.get("minimum_purchase")
        active = request.POST.get("active") == "1"

        errors = validate_coupon_fields(
            code, discount, quantity, minimum_purchase
        )

        if Coupon.objects.filter(code=code).exclude(id=coupon.id).exists():
            errors.append("This coupon code already exists.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("edit_coupon", id=coupon.id)

        coupon.code = code
        coupon.discount = int(discount)
        coupon.quantity = int(quantity)
        coupon.minimum_purchase = int(minimum_purchase)
        coupon.is_active = active
        coupon.save()

        messages.success(request, "Coupon updated successfully.")
        return redirect("coupon_list")

    return render(request, "aadmin/coupon-form.html", {
        "coupon": coupon
    })


@admin_login_required
def delete_coupon(request, id):
    coupon = Coupon.objects.get(id=id)
    coupon.delete()
    return redirect("coupon_list")


@admin_login_required
def offer_list(request):
    title = "Offers"
    current_page = "offer_list"

    offers = CategoryOffer.objects.all().order_by("discount")

    if request.method == "POST":
        filter_option = request.POST.get("filter_option")
        if filter_option == "active_offers":
            offers = offers.filter(is_active=True)
        elif filter_option == "inactive_offers":
            offers = offers.filter(is_active=False)

    search_query = request.GET.get("search", "")
    if search_query:
        offers = offers.filter(
            Q(category__name__icontains=search_query)
            | Q(discount__icontains=search_query)
        )

    paginator = Paginator(offers, 2)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    request.session["selection"] = "all_offers"

    context = {
        "title": title,
        "current_page": current_page,
        "offers": page_obj,
        "search_query": search_query,
    }
    return render(request, "aadmin/offer-list.html", context)


@admin_login_required
def add_offer(request):
    title = "Add Offer"
    current_page = "add_offer"
    categories = Category.objects.all()

    if request.method == "POST":
        category_id = request.POST.get("category_id")
        discount_str = request.POST.get("discount")
        active = request.POST.get("active")

        if not category_id:
            messages.error(request, "Please select a category")
            return redirect("add_offer")

        try:
            discount = int(discount_str)
        except (ValueError, TypeError):
            messages.error(request, "Discount must be a number")
            return redirect("add_offer")

        if discount < 1 or discount > 50:
            messages.error(request, "Discount must be between 1% and 50%")
            return redirect("add_offer")

        category = Category.objects.get(id=category_id)

        if CategoryOffer.objects.filter(category=category).exists():
            messages.error(request, "An offer already exists for this category")
            return redirect("add_offer")

       
        CategoryOffer.objects.create(
            category=category,
            discount=discount,
            is_active=active,
        )

        messages.success(request, "Offer added successfully!")
        return redirect("offer_list")

    context = {
        "title": title,
        "current_page": current_page,
        "categories": categories,
    }
    return render(request, "aadmin/offer-form.html", context)




@admin_login_required
def edit_offer(request, id):
    title = "Edit Offer"
    current_page = "edit_offer"
    offer = CategoryOffer.objects.get(id=id)
    categories = Category.objects.all()

    if request.method == "POST":
        category_id = request.POST.get("category_id")
        discount = int(request.POST.get("discount"))
        active = request.POST.get("active")
        category = Category.objects.get(id=category_id)

        if discount > 100 or discount < 1:
            error_message = "Invalid Discount Percentage"
            messages.error(request, error_message)
            return redirect("edit_offer", id=offer.id)

        if (
            CategoryOffer.objects.filter(category=category)
            .exclude(id=offer.id)
            .exists()
        ):
            error_message = "An offer already exists for this category"
            messages.error(request, error_message)
            return redirect("edit_offer", id=offer.id)

        offer.category = category
        offer.discount = discount
        offer.is_active = active
        offer.save()

        return redirect("offer_list")

    context = {
        "title": title,
        "current_page": current_page,
        "offer": offer,
        "categories": categories,
    }
    return render(request, "aadmin/offer-form.html", context)





@admin_login_required
def delete_offer(request, id):
    try:
        offer = CategoryOffer.objects.get(id=id)
        offer.delete()
        messages.success(request, "Offer deleted successfully!")
    except CategoryOffer.DoesNotExist:
        messages.error(request, "Offer not found.")
    
    return redirect('offer_list')





@admin_login_required
def inventory_list(request):
   
    search_query = request.GET.get("search", "")

    
    inventory = Inventory.objects.select_related("product").filter(
        Q(product__name__icontains=search_query) | Q(size__icontains=search_query)
    ).order_by('-id')


    paginator = Paginator(inventory, 5)  
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
    }
    return render(request, "aadmin/inventory-list.html", context)


@admin_login_required
def add_edit_inventory(request, inventory_id=None):

    if inventory_id:
        inventory = get_object_or_404(Inventory, pk=inventory_id)
    else:
        inventory = None

    
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        price = request.POST.get("price")
        size = request.POST.get("size")
        stock = request.POST.get("stock")


        if not product_id or not price or not size or not stock:
            messages.error(request, "All fields are required.")
        elif int(price) < 1:
            messages.error(request, "Price must be greater than 0.")
        elif int(stock) < 0:
            messages.error(request, "Stock cannot be negative.")
        else:
            product = get_object_or_404(Product, pk=product_id)

            existing_inventory = (
                Inventory.objects.filter(product=product, size=size)
                .exclude(pk=inventory_id)
                .first()
            )

            if existing_inventory:
               
                messages.error(
                    request,
                    f"An inventory item with size '{size}' already exists for the selected product.",
                )
            else:
                if inventory:
                   
                    inventory.product = product
                    inventory.price = price
                    inventory.size = size
                    inventory.stock = stock
                    inventory.save()
                    messages.success(request, "Inventory item updated successfully.")
                else:
              
                    Inventory.objects.create(
                        product=product, price=price, size=size, stock=stock
                    )
                    messages.success(
                        request, "New inventory item created successfully."
                    )

                return redirect(
                    "inventory_list"
                ) 


    products = Product.objects.all()
    sizes = Inventory.SIZE_CHOICES

    context = {"inventory": inventory, "products": products, "sizes": sizes}

    return render(request, "aadmin/inventory-add.html", context)


@admin_login_required
def inventory_status(request, inventory_id):
    inventory_item = get_object_or_404(Inventory, id=inventory_id)
    inventory_item.is_active = not inventory_item.is_active
    inventory_item.save()
    return redirect("inventory_list")


@admin_login_required
def delete_inventory(request, inventory_id):
    inventory_item = get_object_or_404(Inventory, id=inventory_id)
    inventory_item.delete()
    return redirect("inventory_list")
