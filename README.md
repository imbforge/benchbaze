# BenchBaze

BenchBaze is a Django-based laboratory inventory and purchasing management system. It provides a highly customized Django admin experience for managing biological collection items, approvals, GMO compliance (AKA Formblatt Z in Germany), purchasing, user access, as well as an built-in DNA map viewer.

## Key features

- Inventory management for plasmids, cell lines, strains (yeast and bacteria), oligos, antibodies, viruses, and related assets
- Purchasing and order tracking workflows
- Approval forms and document attachments
- GMO compliance support for German laboratories
- Custom user roles and OIDC-aware authentication
- Open Vector Editor (OVE) integration for DNA map visualization
- REST API endpoints for frontend integration

## Repository structure

- `config/` - Django configuration, settings, URL routing, and WSGI entrypoint
- `collection/` - inventory app modules for biological collections and shared utilities
- `purchasing/` - purchasing, orders, cost units, and hazardous materials support
- `approval/` - approval workflows and forms
- `common/` - shared models, admin site customizations, authentication backends, and utilities
- `formz/` - form-related models and management logic
- `frontend/` - Vue 3 + Vite frontend project used for client-side UI components (very much in development)
- `requirements/` - Python dependency manifests and environment definitions
- `templates/` - Django templates used by the admin and authentication views
- `staticfiles/` - static assets
- `uploads/` - media upload directory

## Technology stack

- Python 3.11
- Django 4.2
- PostgreSQL
- Vue 3 + Vite for frontend UI
- Mozilla Django OIDC for authentication
- django-guardian for object permissions
- django-import-export, djangoql, django-simple-history, background_task
- Open Vector Editor (OVE) integration for DNA map support

## Setup

### 1. Create `private_settings.py`

Copy the template and update the values for your environment:

```bash
cp config/private_settings_template.py config/private_settings.py
```

Edit `config/private_settings.py` to set relevant values for your database, email, and other environment-specific settings.


### 2. Install Python dependencies

Install from the pinned requirement file:

```bash
conda create -n benchbaze -f requirements/conda.yml
conda activate benchbaze
```

```bash
python -m pip install -r requirements/prod.txt
```

For development dependencies:

```bash
python -m pip install -r requirements/dev.txt
```

### 3. Initialize the database

Create and migrate the PostgreSQL database:

```bash
python manage.py migrate
```

Create a superuser:

```bash
python manage.py createsuperuser
```

### 4. Collect static assets

```bash
python manage.py collectstatic --noinput
```

## Running the application

For local development, use Django's built-in server:

```bash
python manage.py runserver
```

## License

See `LICENSE` for project licensing details.
