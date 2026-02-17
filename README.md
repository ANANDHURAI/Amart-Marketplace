# 🛍️ Amart - Men’s Fashion E-Commerce Engine

> A scalable e-commerce platform featuring automated inventory management, wallet systems.

<img width="1889" height="912" alt="Screenshot 2026-02-17 125641" src="https://github.com/user-attachments/assets/599a1487-f3d6-476f-b591-d641b705bcb0" />


![Django](https://img.shields.io/badge/django-4.0-green.svg)
![AWS](https://img.shields.io/badge/AWS-EC2-orange.svg)
![MySQL](https://img.shields.io/badge/MySQL-DB-blue.svg)
![Razorpay](https://img.shields.io/badge/Payments-Razorpay-blue.svg)

## 📌 Project Overview
Amart is a production-grade e-commerce solution designed for high-volume retail. It moves beyond basic CRUD operations to handle complex business logic like **inventory tracking**, **promotional coupon engines**, and **secure wallet transactions**.

## 🚀 Key Features

### 🛡️ Admin Management
* **Analytical Dashboard:** Real-time visualization of sales, revenue, and user growth.
* **Inventory Control:** Automated stock deduction and low-stock alerts.
* **Soft Delete:** Data safety implementation to prevent accidental permanent deletion.

### 👤 Customer Experience
* **Smart Discovery:** Advanced filtering (Size, Color, Brand) and sorting algorithms.
* **Wallet System:** Closed-loop wallet for instant refunds and faster checkout.
* **Secure Payments:** Integrated **Razorpay** gateway with webhook verification.

## 🛠️ Tech Stack

| Component | Technology |
| :--- | :--- |
| **Backend** | Python, Django Framework |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Database** | MySQL |
| **ORM** | Django ORM |
| **Payments** | Razorpay API |
| **Deployment** | AWS EC2 (Gunicorn + Nginx) |

## 🔧 Installation & Setup

1.  **Clone & Install**
    ```bash
    git clone [https://github.com/ANANDHURAI/Amart-Marketplace.git](https://github.com/ANANDHURAI/Amart-Marketplace.git)
    cd Amart-Marketplace
    pip install -r requirements.txt
    ```

2.  **Environment Secrets (.env)**
    *Create a `.env` file to store sensitive keys:*
    ```env
    SECRET_KEY=your_secret_key
    DB_NAME=amart_db
    DB_USER=root
    DB_PASSWORD=your_mysql_password
    RAZORPAY_KEY_ID=your_razorpay_key
    RAZORPAY_KEY_SECRET=your_razorpay_secret
    ```

3.  **Database Migration**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

4.  **Run Server**
    ```bash
    python manage.py runserver
    ```

## 🌐 Deployment
Deployed on **AWS EC2** using **Gunicorn** and **Nginx** as a reverse proxy. Database managed via **AWS RDS**.

## 👤 Author
**Anand Kumar** - *Independent Full Stack Developer*
