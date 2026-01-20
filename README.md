# Amart | Men’s Fashion E-Commerce Platform

Hi 👋, I’m **Anandhurai**.  
This is my **First Industrial project**, designed to **E-Commerce** seamlessly.  

---

**Amart** is a specialized e-commerce solution designed exclusively for men's fashion. Built with a robust **Django** backend and a sleek, responsive frontend, it offers a seamless shopping experience for users and a powerful management suite for administrators.

---

## 🚀 Features

### 👤 Customer Side
* **Secure Authentication:** Industry-standard Login and Signup processes with password hashing and session management.
* **Premium UI/UX:** An attractive, minimalist interface built with **HTML5** and **CSS3** tailored for the modern man.
* **Payment Integration:** Secure checkout powered by **Razorpay**, supporting multiple payment methods.
* **Wallet System:** Integrated user wallet for faster checkouts and instant refund processing.
* **Returns & Refunds:** User-friendly cancellation and refund functionality with automated wallet credits.
* **Smart Discovery:** Advanced sorting (price, popularity, new arrivals) and filtering (size, color, brand).
* **Error Handling:** Custom-designed, user-friendly error messages for a smooth browsing experience.

---

### 🛡️ Admin Side
* **Analytical Dashboard:** A "Big View" real-time dashboard displaying key metrics like total sales, user growth, and revenue.
* **User Management:** Ability to monitor user activity, with the power to **Ban/Unban** users to maintain platform integrity.
* **Data Safety (Soft Delete):** A sophisticated soft-delete system ensuring data is never permanently lost accidentally.
* **Marketing Tools:**
    * **Coupon System:** Create and manage discount codes.
    * **Offers System:** Category-wise or product-wise promotional offers.
* **Inventory Management:** Full CRUD operations for products, categories, and stock levels.
* **Order Management:** Track and update order statuses (Pending, Shipped, Delivered, Returned).
* **Sales Reports:** Generate detailed reports (Daily, Weekly, Monthly) in various formats to track business growth.

---

## 🛠️ Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Backend** | Python, Django Framework |
| **Frontend** | HTML5, CSS3, JavaScript |
| **Database** | MySQL |
| **Database Mapping** | Django ORM |
| **Payments** | Razorpay API |
| **Deployment** | AWS (Amazon Web Services) |

---

## 🏗️ System Architecture
The application follows the **MVT (Model-View-Template)** architecture:
* **Models:** Defined using Django ORM for seamless MySQL interaction.
* **Views:** Handles the business logic, from processing payments to generating sales reports.
* **Templates:** Dynamic HTML rendering for a personalized user experience.

---

## 📦 Installation & Setup

Create a Virtual Environment:

Bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install Dependencies:

Bash
pip install -r requirements.txt
Database Configuration:

Create a MySQL database named amart_db.

Update your settings.py with your MySQL credentials.

Run Migrations:

Bash
python manage.py makemigrations
python manage.py migrate
Start the Server:

Bash
python manage.py runserver
🌐 Deployment
This application is deployed on AWS, utilizing EC2 for hosting and RDS for the MySQL database management, ensuring high availability and scalability.

🤝 Contact
Developed by Anandhurai – feel free to reach out for collaborations!
