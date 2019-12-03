import os

from invoke import task, Exit

from environment import base_dir, environment

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.%s' % environment)
manage_file = os.path.join(base_dir, 'manage.py')


@task
def pip(context):
    context.run('pip-compile requirements.in', pty=True)
    context.run('pip-sync requirements.txt', pty=True)


@task
def createsuperuser(context):
    import django
    from django.conf import settings
    django.setup()

    if not settings.DEBUG:
        print("DEBUG is False!")
        Exit()
        return

    from django.contrib.auth.models import User
    User.objects.create_superuser('admin', 'admin@localhost', 'admin')


###
#  reset database stuff
###

@task
def createdatabase(context):
    import django
    from django.conf import settings
    django.setup()

    user = settings.DATABASES['default']['USER']
    password = settings.DATABASES['default']['PASSWORD']
    name = settings.DATABASES['default']['NAME']

    if password:
        context.run(
            'mysql -u{} -p{} -e "CREATE DATABASE {} CHARACTER SET utf8mb4 '
            'COLLATE utf8mb4_unicode_ci"'.format(user, password, name)
        )
    else:
        context.run(
            'mysql -u{} -e "CREATE DATABASE {} CHARACTER SET utf8mb4 '
            'COLLATE utf8mb4_unicode_ci"'.format(user, name)
        )


@task
def migrate(context):
    context.run('{} migrate'.format(manage_file), pty=True)


@task
def reset(context):
    """ Recreates database.
    """
    import django
    from django.conf import settings
    django.setup()

    if not settings.DEBUG:
        print("DEBUG is False!")
        Exit()
        return
    _recreate_database(context, settings)
    migrate(context)
    createsuperuser(context)


def _recreate_database(context, settings):
    user = settings.DATABASES['default']['USER']
    password = settings.DATABASES['default']['PASSWORD']
    name = settings.DATABASES['default']['NAME']

    if password:
        context.run(
            'mysql -u{} -p{} -e "DROP DATABASE {}"'.format(user, password, name)
        )
        context.run(
            'mysql -u{} -p{} -e "CREATE DATABASE {} CHARACTER SET utf8mb4 '
            'COLLATE utf8mb4_unicode_ci"'.format(user, password, name)
        )
    else:
        context.run(
            'mysql -u{} -e "DROP DATABASE IF EXISTS {}"'.format(user, name)
        )
        context.run(
            'mysql -u{} -e "CREATE DATABASE {} CHARACTER SET utf8mb4 '
            'COLLATE utf8mb4_unicode_ci"'.format(user, name)
        )
