# Deployment Guide: MAI@UCSD Inventory Backend

This guide provides step-by-step instructions for deploying the MAI@UCSD Inventory backend application using **Supabase** for the database and **Render** for the backend hosting.

## Prerequisites

Before starting the deployment process, ensure you have:
- A GitHub account with access to this repository
- A Supabase account (free tier available)
- A Render account (free tier available)
- A Google Cloud Console account for OAuth setup
- A Cloudinary account for image storage

## Overview

The deployment process involves:
1. Setting up a PostgreSQL database on Supabase
2. Configuring Google OAuth credentials
3. Setting up Cloudinary for image storage
4. Deploying the backend to Render
5. Configuring environment variables

---

## 1. Supabase Database Setup

### 1.1 Create a Supabase Project

1. Go to [Supabase](https://supabase.com/) and sign in or create an account
2. Click **"New Project"**
3. Choose your organization or create a new one
4. Fill in the project details:
   - **Name**: `mai-ucsd-inventory` (or your preferred name)
   - **Database Password**: Create a strong password and save it securely
   - **Region**: Choose the region closest to your users (e.g., `us-west-1` for West Coast)
5. Click **"Create new project"**

### 1.2 Get Database Connection Details

Once your project is created:

1. Go to **Settings** → **Database** in your Supabase dashboard
2. Scroll down to **Connection Info** and note the following:
   - **Host**: `db.[project-ref].supabase.co`
   - **Database name**: `postgres`
   - **Port**: `5432`
   - **User**: `postgres`
   - **Password**: The password you set during project creation

### 1.3 Configure Database Access

1. In your Supabase project, go to **Settings** → **Database**
2. Scroll down to **Connection pooling** and enable it for better performance
3. Note the **Connection pooling** URL as well (format: `postgresql://postgres:[password]@db.[project-ref].supabase.co:6543/postgres`)

---

## 2. Google OAuth Setup

### 2.1 Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** → **"New Project"**
3. Enter project details:
   - **Project name**: `MAI UCSD Inventory` (or your preferred name)
   - **Organization**: Select your organization if applicable
4. Click **"Create"**

### 2.2 Enable Google+ API

1. In your Google Cloud project, go to **APIs & Services** → **Library**
2. Search for **"Google+ API"** or **"Google Identity"**
3. Click on **"Google+ API"** and then **"Enable"**

### 2.3 Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Choose **"External"** user type (unless you have a Google Workspace domain)
3. Click **"Create"**
4. Fill in the required information:
   - **App name**: `MAI@UCSD Inventory`
   - **User support email**: Your email address
   - **App logo**: (Optional) Upload your app logo
   - **App domain**: Your Render app domain (you'll get this later)
   - **Developer contact information**: Your email address
5. Click **"Save and Continue"**
6. On the **"Scopes"** page, click **"Save and Continue"** (no additional scopes needed)
7. On the **"Test users"** page, add any test users if needed, then **"Save and Continue"**

### 2.4 Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **"Create Credentials"** → **"OAuth 2.0 Client IDs"**
3. Choose **"Web application"** as the application type
4. Configure the client:
   - **Name**: `MAI UCSD Inventory Web Client`
   - **Authorized JavaScript origins**: 
     - `https://your-app-name.onrender.com` (replace with your actual Render URL)
     - `http://localhost:8000` (for local development)
   - **Authorized redirect URIs**:
     - `https://your-app-name.onrender.com/accounts/google/login/callback/`
     - `http://localhost:8000/accounts/google/login/callback/` (for local development)
5. Click **"Create"**
6. **Important**: Save the **Client ID** and **Client Secret** - you'll need these for environment variables

---

## 3. Cloudinary Setup

### 3.1 Create a Cloudinary Account

1. Go to [Cloudinary](https://cloudinary.com/) and sign up for a free account
2. Verify your email address
3. Complete the account setup

### 3.2 Get API Credentials

1. In your Cloudinary dashboard, go to **Settings** → **API Keys**
2. Note the following credentials:
   - **Cloud Name**: Found in the dashboard URL or account details
   - **API Key**: The public API key
   - **API Secret**: The private API secret (keep this secure)

### 3.3 Configure Upload Settings (Optional)

1. Go to **Settings** → **Upload** to configure:
   - File size limits
   - Allowed file formats
   - Auto-optimization settings

---

## 4. Render Deployment

### 4.1 Create a Render Account

1. Go to [Render](https://render.com/) and sign up
2. Connect your GitHub account to Render

### 4.2 Create a Web Service

1. In your Render dashboard, click **"New +"** → **"Web Service"**
2. Connect your GitHub repository: `StarDylan/MAI-at-UCSD-Inventory`
3. Configure the service:
   - **Name**: `mai-ucsd-inventory-backend` (or your preferred name)
   - **Region**: Choose the same region as your Supabase database
   - **Branch**: `main` (or your deployment branch)
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt` (we'll create this)
   - **Start Command**: `gunicorn mai.wsgi:application`

### 4.3 Environment Variables Configuration

In the Render service settings, add the following environment variables:

#### Django Settings
```
DJANGO_SETTINGS_MODULE=mai.settings
SECRET_KEY=<generate-a-long-random-string>
DEBUG=False
ALLOWED_HOSTS=<your-render-app-name>.onrender.com
```

#### Database Configuration (Supabase)
```
DATABASE_URL=postgresql://postgres:<password>@db.<project-ref>.supabase.co:5432/postgres
```

#### Google OAuth
```
GOOGLE_CLIENT_ID=<your-google-client-id>
GOOGLE_CLIENT_SECRET=<your-google-client-secret>
```

#### Cloudinary
```
CLOUDINARY_CLOUD_NAME=<your-cloudinary-cloud-name>
CLOUDINARY_API_KEY=<your-cloudinary-api-key>
CLOUDINARY_API_SECRET=<your-cloudinary-api-secret>
DELETE_CLOUDINARY_IMAGES=True
```

### 4.4 Create Requirements File

You'll need to create a `requirements.txt` file in the backend directory. Based on the `pyproject.toml`, create:

```txt
Django>=5.2.5
django-environ>=0.12.0
django-allauth[socialaccount]>=65.11.1
djangorestframework>=3.16.1
django-crispy-forms>=2.4
crispy-bootstrap4>=2025.6
cloudinary>=1.44.1
django-ulid>=0.0.4
gunicorn>=21.0.0
psycopg2-binary>=2.9.0
whitenoise>=6.0.0
```

---

## 5. Production Settings Configuration

### 5.1 Update Django Settings

You'll need to modify the `settings.py` file to handle production deployment. Add the following configurations:

#### Database Configuration
```python
import dj_database_url

# Database configuration
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.parse(os.environ.get('DATABASE_URL'))
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
```

#### Static Files Configuration
```python
# Static files configuration for production
STATIC_URL = "static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Whitenoise for static file serving
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

#### Security Settings
```python
# Security settings for production
if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
```

#### Allowed Hosts Configuration
```python
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])
```

---

## 6. Deployment Steps

### 6.1 Prepare Your Repository

1. **Create requirements.txt**: Add the requirements file to your `backend/` directory
2. **Update settings.py**: Add the production configurations mentioned above
3. **Commit and push** your changes to GitHub

### 6.2 Deploy to Render

1. In your Render service, click **"Manual Deploy"** or wait for auto-deploy
2. Monitor the build logs for any errors
3. Once deployed, your app will be available at: `https://your-app-name.onrender.com`

### 6.3 Run Database Migrations

1. In your Render service dashboard, go to **"Shell"**
2. Run the following commands:
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 6.4 Update Google OAuth Settings

1. Go back to your Google Cloud Console
2. Update the OAuth credentials with your actual Render URL:
   - **Authorized JavaScript origins**: `https://your-actual-app-name.onrender.com`
   - **Authorized redirect URIs**: `https://your-actual-app-name.onrender.com/accounts/google/login/callback/`

---

## 7. Post-Deployment Checklist

- [ ] Verify the application loads at your Render URL
- [ ] Test Google OAuth login functionality
- [ ] Test image upload functionality (Cloudinary)
- [ ] Check admin panel access
- [ ] Verify database connectivity and data persistence
- [ ] Test all major application features

---

## 8. Environment Variables Reference

Here's a complete reference of all required environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | `your-super-secret-key-here` |
| `DEBUG` | Debug mode (False for production) | `False` |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts | `your-app.onrender.com` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:port/db` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | `123456-abc.apps.googleusercontent.com` |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret | `GOCSPX-your-secret-here` |
| `CLOUDINARY_CLOUD_NAME` | Cloudinary cloud name | `your-cloud-name` |
| `CLOUDINARY_API_KEY` | Cloudinary API key | `123456789012345` |
| `CLOUDINARY_API_SECRET` | Cloudinary API secret | `your-api-secret` |
| `DELETE_CLOUDINARY_IMAGES` | Whether to delete images from Cloudinary | `True` |

---

## 9. Troubleshooting

### Common Issues and Solutions

#### Database Connection Issues
- Verify your Supabase database credentials
- Check if your IP is whitelisted in Supabase (should be automatic for Render)
- Ensure the DATABASE_URL format is correct

#### Google OAuth Issues
- Verify the redirect URIs match exactly (including trailing slashes)
- Check that the Google+ API is enabled
- Ensure the OAuth consent screen is properly configured

#### Static Files Issues
- Run `python manage.py collectstatic` in the Render shell
- Verify WhiteNoise is properly configured
- Check that STATIC_ROOT is set correctly

#### Cloudinary Issues
- Verify all three Cloudinary credentials are correct
- Check that file upload limits aren't exceeded
- Ensure the Cloudinary account is active

### Getting Help

If you encounter issues:
1. Check the Render build and deployment logs
2. Use the Render shell to debug Django issues
3. Check the Supabase logs for database issues
4. Verify all environment variables are set correctly

---

## 10. Security Considerations

- **Never commit sensitive credentials** to your repository
- **Use strong passwords** for all services
- **Regularly rotate secrets** like API keys and passwords
- **Monitor access logs** in all services
- **Keep dependencies updated** to patch security vulnerabilities
- **Use HTTPS only** in production (enforced by Render)

---

This deployment guide should get your MAI@UCSD Inventory backend up and running on Render with Supabase and all required third-party services configured properly.