# 🏠 HomeHero - Hyperlocal Household Service Booking Marketplace

> **A Full-Stack Hyperlocal Household Service Marketplace MVP** connecting customers with nearby verified service providers (Plumbers, Electricians, Cleaners, Carpenters, Painters, and Appliance Technicians) within a 10 km radius using the Haversine distance algorithm, atomic concurrency-safe job dispatch, and live status tracking.
>
> *Designed and built as a Major Project / Internship Demonstration.*

---

## 📌 1. Project Concept & Problem Statement

### The Problem
When households experience sudden plumbing leaks, electrical sparking, broken appliances, or need deep cleaning, finding a reliable, nearby worker quickly is difficult. Traditional word-of-mouth contacts are often unavailable or far away, while standard aggregator platforms often suffer from high commissions, delayed allocations, and lack of transparency.

### The Solution: HomeHero
HomeHero implements a dispatch marketplace inspired by ride-hailing platforms (like Rapido) tailored for household services:
1. **Customer posts a service request** with a description, category, and location.
2. **System matches active, approved workers** within a 10 km radius offering that specific service using the **Haversine formula**.
3. **Nearby workers receive incoming radar alerts** (with problem details and distance, but customer phone/exact flat number protected).
4. **First-Come, First-Served Atomic Acceptance**: The first worker to click **Accept** gets assigned the job. Database-level atomic conditional locking prevents race conditions if multiple workers click Accept simultaneously.
5. **Customer Details Unlocked**: The assigned worker gains access to the customer's phone number and complete address.
6. **Live Lifecycle Tracking**: Customer tracks worker status (`Assigned` &rarr; `On The Way` &rarr; `Service Started` &rarr; `Completed`).
7. **Review & Rating**: Customer rates the service (1–5 stars), which dynamically recalculates the worker's average rating.
8. **Admin Operations**: Admin oversees all users, verifies/approves worker profiles, manages service categories, and monitors live platform KPIs.

---

## 🏛️ 2. System Architecture & Workflow

```
+-----------------------------------------------------------------------------------+
|                                 CUSTOMER PANEL                                    |
|   1. Selects Service Category -> Enters Problem -> Selects Location (GPS/Preset)   |
|   2. Broadcasts Request (Status = 'SEARCHING')                                    |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                        MATCHING & DISPATCH ENGINE                                 |
|   1. Query active, approved workers offering requested service.                   |
|   2. Compute great-circle distance between (lat1, lon1) and (lat2, lon2).         |
|   3. Filter workers where distance <= 10 km and worker has no ongoing active job. |
|   4. Broadcast radar alerts to eligible workers.                                 |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                             WORKER RADAR PANEL                                    |
|   1. Worker receives incoming card: Service, Problem, Distance (~2.3 km), Budget   |
|   2. Worker clicks [Accept Job]                                                   |
|   3. Atomic SQL Lock: UPDATE WHERE status='SEARCHING' -> sets status='ASSIGNED'   |
|      (If another worker clicked first, graceful conflict message is returned)     |
|   4. Customer Address & Phone Number are UNLOCKED for the assigned worker.        |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                             JOB EXECUTION LIFECYCLE                               |
|   Worker:  [On The Way] --------> [Service Started] --------> [Mark Completed]    |
|   Customer: Live Tracker Stepper updates automatically via AJAX polling           |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                             FEEDBACK & REPUTATION                                 |
|   Customer submits 1-5 Star Rating & Review -> Worker rating recalculated live    |
|   Admin inspects platform volume, worker verification, and metrics dashboard       |
+-----------------------------------------------------------------------------------+
```

---

## 🌟 3. Key Feature Highlights (Viva Ready)

| Feature | Technical Implementation |
| :--- | :--- |
| **Hyperlocal Matching** | Great-circle distance calculation via Python `math` (**Haversine Algorithm**) with configurable radius (10 km). |
| **Atomic Concurrency Acceptance** | Race condition prevention using atomic SQL conditional queries: `UPDATE service_requests SET status='ASSIGNED' WHERE id=:id AND status='SEARCHING'`. |
| **Information Privacy Shield** | Customer address and phone number are hidden until a worker successfully accepts the booking. |
| **Live UI Polling Engine** | Robust asynchronous JavaScript polling (every 3–4 seconds) for seamless real-time demo without WebSocket dropouts. |
| **1-Click Viva Demo Bar** | Pre-configured demo switcher on every page to switch seamlessly between Customer, Plumber, Electrician, Cleaner, and Admin roles. |
| **Role-Based Access Control** | Dedicated route decorators (`@customer_required`, `@worker_required`, `@admin_required`). |
| **Reputation System** | Incremental review rating calculation recalculating `rating_avg` and `rating_count`. |

---

## 💻 4. Technology Stack

- **Backend**: Python 3.12, Flask 3.0+
- **ORM & Database**: Flask-SQLAlchemy, SQLite (`instance/household_app.db`)
- **Authentication**: Flask-Login, Werkzeug Password Hashing (`pbkdf2:sha256`)
- **Frontend**: HTML5, Vanilla JavaScript (Fetch API AJAX), Modern CSS Design Tokens, Bootstrap 5.3, FontAwesome 6
- **Architecture Pattern**: Application Factory (`create_app`), Blueprint modular routing (`auth`, `customer`, `worker`, `admin`, `api`), MVC structure

---

## 🗄️ 5. Database Schema

### 1. `users`
- `id` (PK, Integer)
- `name` (String 120)
- `email` (String 120, Unique, Index)
- `phone` (String 20)
- `password_hash` (String 256)
- `role` ('customer' | 'worker' | 'admin')
- `status` ('active' | 'suspended')
- `created_at` (DateTime)

### 2. `worker_profiles`
- `id` (PK, Integer)
- `user_id` (FK &rarr; `users.id`)
- `experience_years` (Integer)
- `hourly_rate` (Float)
- `bio` (Text)
- `latitude`, `longitude` (Float, GPS Coordinates)
- `location_name` (String 150)
- `is_available` (Boolean, Online/Offline Toggle)
- `is_approved` (Boolean, Admin Verification)
- `rating_avg` (Float, Cached Average)
- `rating_count` (Integer)
- `total_jobs_completed` (Integer)

### 3. `services` (Categories)
- `id` (PK, Integer)
- `name` (String 100, e.g. "Plumbing", "Electrical", "Cleaning")
- `icon` (String 50, FontAwesome class)
- `description` (Text)
- `base_price` (Float)
- `is_active` (Boolean)

### 4. `worker_services` (Association Table)
- `worker_profile_id` (FK &rarr; `worker_profiles.id`)
- `service_id` (FK &rarr; `services.id`)

### 5. `service_requests`
- `id` (PK, Integer)
- `customer_id` (FK &rarr; `users.id`)
- `service_id` (FK &rarr; `services.id`)
- `assigned_worker_id` (FK &rarr; `users.id`, Nullable until accepted)
- `title`, `description`, `address`, `location_name`
- `latitude`, `longitude`
- `budget` (Float)
- `status` (`SEARCHING` | `ASSIGNED` | `ON_THE_WAY` | `IN_PROGRESS` | `COMPLETED` | `CANCELLED`)
- `created_at`, `accepted_at`, `started_at`, `completed_at`, `cancelled_at`

### 6. `reviews`
- `id` (PK, Integer)
- `request_id` (FK &rarr; `service_requests.id`, Unique)
- `customer_id` (FK &rarr; `users.id`)
- `worker_id` (FK &rarr; `users.id`)
- `rating` (Integer, 1–5)
- `comment` (Text)

---

## 🔑 6. Demo Accounts & Credentials

The application auto-seeds complete demonstration accounts upon first startup:

| Role | Name | Email | Password | Pre-configured Location |
| :--- | :--- | :--- | :--- | :--- |
| **Customer** | Sneha Roy | `customer@example.com` | `Customer@123` | Paltan Bazaar, Guwahati |
| **Plumber** | Rahul Sharma | `rahul@example.com` | `Worker@123` | Paltan Bazaar, Guwahati |
| **Electrician** | Amit Das | `amit@example.com` | `Worker@123` | GS Road, Guwahati |
| **Cleaner** | Rohit Kalita | `rohit@example.com` | `Worker@123` | Zoo Road, Guwahati |
| **AC & Appliance** | Priya Boro | `priya@example.com` | `Worker@123` | Dispur Last Gate, Guwahati |
| **Carpenter** | Manoj Paul | `manoj@example.com` | `Worker@123` | Jalukbari, Guwahati |
| **Admin** | Administrator | `admin@example.com` | `Admin@123` | Central HQ |

> 💡 **Viva Tip:** You can simply click the **1-Click Demo Logins** banner at the top of the webpage or on the Login screen to switch roles instantly!

---

## 🚀 7. Installation & How to Run

### Step 1: Navigate to the Project Directory
```bash
cd C:\Users\asus\.gemini\antigravity\scratch\household_service_app
```

### Step 2: Install Required Dependencies
```bash
python -m pip install -r requirements.txt
```

### Step 3: Run the Application
```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🧪 8. Automated Test Suite

Run the unit tests and end-to-end integration tests:

```bash
python -m unittest discover tests
```

Tests include:
- `test_haversine_distance`: Verifies mathematical accuracy of great-circle distance.
- `test_user_authentication_and_roles`: Validates password hashing and RBAC checks.
- `test_concurrency_atomic_acceptance`: Validates race condition handling between competing workers.
- `test_service_request_lifecycle_and_matching`: Validates end-to-end lifecycle from creation to rating.
- `test_full_demo_workflow`: Full end-to-end API test verifying all panels.

---

## 🎬 9. Live Viva Demonstration Flow

Follow this exact walkthrough during your presentation:

1. **Open Browser 1 (Normal Tab)**:
   - Click **Customer (Sneha Roy)** from the top demo bar.
   - Click **"Book New Service"**.
   - Select **Plumbing**, enter title *"Kitchen tap leaking continuously"*, choose *"Paltan Bazaar, Guwahati"* as location, and click **"Request Service Now"**.
   - The customer screen begins radar pulsing: *"Searching for nearby active workers..."*.

2. **Open Browser 2 (Incognito / Second Browser Window)**:
   - Click **Plumber (Rahul Sharma)** from the top demo bar.
   - On Rahul's Dashboard, observe the **Nearby Job Radar**: The plumbing request appears immediately with distance (~0.2 km away) and estimated budget!
   - Notice that the customer's phone number and exact street address are hidden.
   - Click **[Accept Job]**.

3. **Observe Browser 1 (Customer Screen)**:
   - Without refreshing, the customer screen automatically updates via live polling to **"Worker Assigned"** showing **Rahul Sharma**, his 4.8★ rating, and a direct "Call Worker" button!

4. **In Browser 2 (Worker Workspace)**:
   - Customer's full address and phone number are now revealed.
   - Click **"Mark On The Way"** &rarr; status updates to *On The Way*.
   - Click **"Mark Service Started"** &rarr; status updates to *In Progress*.
   - Click **"Mark Service Completed"** &rarr; job is finished.

5. **In Browser 1 (Customer Screen)**:
   - Customer screen updates to **"Service Completed!"** with a 5-star rating selector.
   - Submit a 5-star rating and comment.

6. **Open Admin Panel**:
   - Click **Admin** from the demo bar.
   - Show the examiner the live KPI counters (Completed Jobs +1, Revenue update), the verified workers list, and the newly submitted review.

---

## 🎓 10. Viva Q&A / Oral Exam Guide

#### Q1: What algorithm did you use for finding nearby workers?
> **Answer:** We implemented the **Haversine Great-Circle Distance Algorithm** in `utils/geo.py`. It computes the shortest distance over the earth's curved surface between the customer's `(latitude, longitude)` and each worker's base coordinates in kilometers. We then filter workers within a 10 km radius who offer that specific service category and are currently online.

#### Q2: How do you prevent two workers from accepting the same request at the same time?
> **Answer:** We implemented **atomic database conditional updates** in `routes/worker.py`. When a worker clicks Accept, we execute `ServiceRequest.query.filter(id==req_id, status=='SEARCHING').update({'status':'ASSIGNED', 'assigned_worker_id':worker.id})`. Because SQLite/relational databases execute transactions atomically, only the first transaction updates 1 row; subsequent concurrent requests update 0 rows and receive a *"Request already claimed"* notice.

#### Q3: How is customer privacy protected?
> **Answer:** During the `SEARCHING` phase, workers only see the general neighborhood name (e.g., "Paltan Bazaar") and distance in kilometers (e.g., "2.1 km away"). The exact flat/house number and customer phone number remain hidden and are only revealed in the worker console after successful assignment.

#### Q4: Why did you use AJAX polling instead of WebSockets?
> **Answer:** For an MVP project, client-side polling with `fetch()` every 3 seconds provides reliable real-time updates across browsers without requiring dedicated WebSocket servers, background Redis workers, or complex fallback mechanisms, ensuring zero downtime during a viva demonstration.

#### Q5: How are passwords stored securely?
> **Answer:** Passwords are never stored in plaintext. They are hashed using **Werkzeug's PBKDF2 with SHA-256** and unique cryptographic salts (`generate_password_hash` and `check_password_hash`).
