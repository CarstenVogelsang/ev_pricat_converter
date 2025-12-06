"""Flask-Admin configuration with role-based access control."""
from flask import redirect, url_for
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user


class SecureModelView(ModelView):
    """ModelView that requires admin role."""

    def is_accessible(self):
        """Check if current user is admin."""
        return current_user.is_authenticated and current_user.rolle == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        """Redirect to login if not accessible."""
        return redirect(url_for('auth.login'))


class SecureAdminIndexView(AdminIndexView):
    """Admin index view that requires admin role."""

    @expose('/')
    def index(self):
        """Check admin access before showing index."""
        if not (current_user.is_authenticated and current_user.rolle == 'admin'):
            return redirect(url_for('auth.login'))
        return super().index()


def init_admin(app, db):
    """Initialize Flask-Admin with all model views."""
    from app.models import Lieferant, Hersteller, Marke, Config, User

    admin = Admin(
        app,
        name='DB Admin',
        url='/db-admin',
        endpoint='dbadmin',  # Unique endpoint to avoid conflict with admin_bp
        index_view=SecureAdminIndexView(url='/db-admin', endpoint='dbadmin')
    )

    # Add model views
    admin.add_view(SecureModelView(Lieferant, db.session, name='Lieferanten'))
    admin.add_view(SecureModelView(Hersteller, db.session, name='Hersteller'))
    admin.add_view(SecureModelView(Marke, db.session, name='Marken'))
    admin.add_view(SecureModelView(Config, db.session, name='Config'))
    admin.add_view(SecureModelView(User, db.session, name='Users'))

    return admin
