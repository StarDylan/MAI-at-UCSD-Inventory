# Deployment Guide: MAI@UCSD Inventory Backend

This guide provides step-by-step instructions for deploying the MAI@UCSD Inventory backend application using **Supabase** for the database and **Render** for the backend hosting. There may be other, better options, but this is based on free-tier allowances at this time. 

## Prerequisites

Before starting the deployment process, ensure you have:
- A GitHub account with access to this repository
- A [Supabase](https://supabase.com) account (free tier available)
- A [Render](https://render.com/) account (free tier available)
- A [Cloudinary](https://cloudinary.com/) account for image storage (free tier available)
- A [Google Cloud Console](console.cloud.google.com/) account for OAuth setup (free)

## Overview

As we go through this setup, we’ll collect a few important codes and passwords. You’ll need to save these in a safe place so you can copy and paste them when needed.

The setup process includes:
1. Creating a database using Supabase
2. Connecting Google sign-in
3. Setting up Cloudinary to store images
4. Putting the backend online with Render
5. Adding the saved codes and passwords so everything works together
---

## 1. Supabase Database Setup

### 1.1 Create a Supabase Project

1. Go to [Supabase](https://supabase.com/) and sign in or create an account
2. Click **"New Organization"**
3. Fill in the organization details:
   - **Name**: `mai-ucsd-inventory` (or your preferred name)
   - **Type**: `Educational`
   - **Plan**: Free Tier ($0/month)

    ![Image of Supabase Org creation](images/supabase-new-org.png)
4. Click on "Create Organization"
5. Now you should be on the "Create a new project" screen. Fill in these details:
   - **Organization**: The one you just created.
   - **Project Name**: `mai-inventory` (or your preferred name)
   - **Database Password**: Either create a strong password or click the *Generate Password* button and save it securely
   - **Region**: Choose the region closest to your users (e.g., `West US (North California)`)
   - Under "Security Options"
      - Choose "Only Connection String"

    ![Supabase New Project](images/supabase-new-project.png)
5. Click **"Create new project"**

### 1.2 Get Database Connection Details

Once your project is created (might need to refresh a few times), you should see this:
![Supabase Status](images/supabase-status.png)

1. Find the **Connect** button at the top and click on it.

2. Copy the **Session pooler** connection string, it should look something like `postgresql://....:[YOUR-PASSWORD]@.....`. Make sure to replace the [YOUR-PASSWORD] part with your **Database Password** from the previous step. Be careful with this string. Anyone who has access to it can wipe your entire database! (That is why backups are important, as we will later discuss).

![Supabase Session Pooling](images/supabase-session-pooling.png)
---

## 2. Google OAuth Setup

Here is where we will get the keys necessary to allow our users to login via Google!

### 2.1 Create a Google Cloud Project

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Click **"Select a project"** (in the top left), then **"New Project"** (top right)
3. Enter project details:
   - **Project name**: `MAI-at-UCSD Inventory` (or your preferred name)
   - **Organization**: Select your organization if applicable
4. Click **"Create"**
5. Click on the **Select a project** button again, and select your newly created project. It should say your project in the top left corner.

### 2.2 Configure OAuth Consent Screen

1. In your Google Cloud project, go to **APIs & Services** → **OAuth consent screen**
2. Click **"Get Started"**
3. Fill in the required information:
   - **App name**: `MAI@UCSD Inventory`
   - **User support email**: Your email address
   - **Audience**: External
   - **Developer contact information**: Your email address
4. Click **"Create"**

### 2.3 Create OAuth Credentials

1. Go back to  **APIs & Services** by clicking on the hamburger menu on the left. Then go to **Credentials**.
2. Click **"Create Credentials"** → **"OAuth Client ID"**
3. Choose **"Web application"** as the application type
4. Configure the client:
   - **Name**: `MAI UCSD Inventory Web Client`
   - **IMPORTANT!** Make sure these URLs match exactly with the website you setup in Render. If you get errors such as "invalid redirect uri", please double check these URLs.
5. Click **"Create"**
6. **Important**: Save the **Client ID** and **Client Secret** - you'll need these later and the secret will not be shown again.
7. Don't close this page! We'll need to come back to it later.

![Google Create an OAuth client ID](images/google-create-oauth-id.png)

---

## 3. Cloudinary Setup

### 3.1 Create a Cloudinary Account

1. Go to [Cloudinary](https://cloudinary.com/) and sign up for a free account
2. Click "Skip" on any prompts. 
3. Complete the account setup

### 3.2 Get API Credentials

1. When logged in, in to the navigation bar to the right, go to **Settings** → **API Keys**
2. Click "**Generate New API Key**"
3. Enter the confirmation code from your email.
4. Rename the "Untitled" key to `MAI-at-UCSD Inventory Backend` (or your preferred name)
5. **Copy the Cloud Name**: Found at the end of the CLOUDINARY_URL at the top of the page after the `@` `CLOUDINARY_URL=.....@<cloud-name>`. Store it securely.
6. Note the following credentials of the key you renamed:
    - **API Key**: Fill in the public API key in your environment variable. Store it securely.
    - **API Secret**: Reveal by clicking on the eye next to the dots. Store it securely.

---

## 4. Render Deployment

### 4.1 Create a Render Account

1. Go to [Render](https://render.com/) and sign up

### 4.2 Create a Web Service

1. In your Render project dashboard, click **"+ Add New"** → **"Web Service"**
2. Connect your GitHub repository: `StarDylan/MAI-at-UCSD-Inventory`
3. Configure the service:
   - **Name**: Choose a name, this will become the URL of your website.
   - **Region**: Choose the same general region as your Supabase database
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `uv sync`
   - **Start Command**: `uv run gunicorn mai.wsgi`
   - **Instance Type**: Free ($0/month)

4. Leave the environment variables alone for now. We'll come back to it later.
5. Click "Deploy Web Service". **Note it will fail to deploy** because we have not set any environment variables. **This is expected.**

6. Copy the URL towards the top. It should look like `https://<name>.onrender.com`. Store this securely.

### 4.3 Secret Key Generation

Some parts of our website need a special code, called a secret key, to work safely. This key must be impossible for anyone to guess.

To make one, we’ll let the computer create a random code for us. We need to create one at least 50 characters long with at least 5 different characters.

1. Go to https://www.random.org/strings/
2. Generate **2** random strings that are **32 characters long**. Be sure to also check to **allow Numeric digits (0-9), Uppercase letters (A-Z), and Lowercase letters (a-z) to be generated**.

3. Click Get Strings!
4. Store your two strings one after another with no space in-between. This is your **SECRET_KEY**! Store it securely.


### 4.4 Environment Variables Configuration

Now we will set all the environment variables needed for our app to work. Be sure to refer to your notes for all the secrets we've been collecting up to this point! 


In the Environment Variables section, add the following environment variables:


| Variable                   | Description                                                                                     | Value (Blank means Copy+Paste |
|----------------------------|-------------------------------------------------------------------------------------------------|-------------------------------|
| `SECRET_KEY`               | SECRET KEY we generated                                                                         |                               |
| `DEBUG`                    | Debug mode (False for production)                                                               | `False`                       |
| `ALLOWED_HOSTS`            | Render URL that we copied                                                                       |                               |
| `DATABASE_URL`             | PostgreSQL connection string we copied from Supabase                                            |                               |
| `GOOGLE_CLIENT_ID`         | Google OAuth client ID from Google                                                              |                               |
| `GOOGLE_CLIENT_SECRET`     | Google OAuth client secret from Google                                                          |                               |
| `CLOUDINARY_CLOUD_NAME`    | Cloudinary cloud name                                                                           |                               |
| `CLOUDINARY_API_KEY`       | Cloudinary API key                                                                              |                               |
| `CLOUDINARY_API_SECRET`    | Cloudinary API secret                                                                           |                               |
| `DELETE_CLOUDINARY_IMAGES` | Whether to delete images from Cloudinary (so you can view any image that was uploaded/deleted) | `False`                        |


## 5. Update Google Config

1. If you are not where you left off in the previous Google Cloud Console step, follow this:
    - Go to [Google Cloud Console](https://console.cloud.google.com/). 
    - Go to **APIs & Services** by clicking on the hamburger menu on the left.
    - Then Then go to **Credentials**.
    - Then click on the `MAI UCSD Inventory Web Client` credential you created.

2. Under Authorized JavaScript origins, add the Render URL you copied earlier.
3. Under Authorized redirect URIs, add the Render URL and add the path `/accounts/google/login/callback/` on the end. (Note in the photo the beginning starting with `https://` isn't visible)

![Google OAuth Config](image.png)

## 6. You're Done!
Try going to your website at the Render URL!