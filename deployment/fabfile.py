"""
Deployment for CodaLab Worksheets.
Usage: create a deployment.config file.
"""

import datetime
import logging
import logging.config
import os
from os.path import (abspath, dirname)
import sys
import yaml
import json

from StringIO import StringIO
from fabric.api import (cd,
                        env,
                        execute,
                        get,
                        prefix,
                        put,
                        require,
                        task,
                        roles,
                        require,
                        run,
                        settings,
                        shell_env,
                        sudo)
from fabric.contrib.files import exists
from fabric.network import ssh
from fabric.utils import fastprint

logger = logging.getLogger('deployment')

############################################################

class DeploymentConfig(object):
    """
    Defines credentials and configuration values needed to deploy CodaLab.
    """
    def __init__(self, label, filename):
        self.label = label
        with open(filename, 'r') as f:
            info = yaml.load(f)
        self._dinfo = info['deployment']
        self._svc_global = self._dinfo['service-global']
        self._svc = self._dinfo['service-configurations'][label] if label is not None else {}
        self.new_relic_key = self._dinfo['new-relic-key']

    def getNewRelicKey(self):
        return self.new_relic_key

    def getLoggerDictConfig(self):
        """Gets Dict config for logging configuration."""
        if 'logging' in self._dinfo:
            return self._dinfo['logging']
        else:
            return None

    def getServicePrefix(self):
        """Gets the unique prefix used to build the name of services and other resources."""
        return self._svc_global['prefix']

    def getServiceCertificateAlgorithm(self):
        """Gets the algorithm for the service certificate."""
        return self._svc_global['certificate']['algorithm']

    def getServiceCertificateThumbprint(self):
        """Gets the thumbprint for the service certificate."""
        return self._svc_global['certificate']['thumbprint']

    def getServiceCertificateFilename(self):
        """Gets the local path of the file holding the service certificate."""
        return self._svc_global['certificate']['filename']

    def getServiceCertificateKeyFilename(self):
        """Gets the local path of the file holding the service certificate key."""
        return self._svc_global['certificate']['key-filename']

    def getServiceCertificateFormat(self):
        """Gets the format of the service certificate."""
        return self._svc_global['certificate']['format']

    def getServiceCertificatePassword(self):
        """Gets the password for the service certificate."""
        return self._svc_global['certificate']['password']

    def getVirtualMachineLogonUsername(self):
        """Gets the username to log into a virtual machine of the service deployment."""
        return self._svc_global['vm']['username']

    def getVirtualMachineLogonPassword(self):
        """Gets the password to log into a virtual machine of the service deployment."""
        return self._svc_global['vm']['password']

    def getEmailInfo(self):
        return self._svc_global['email']

    def getAdminEmail(self):
        return self._svc_global['admin-email']

    def getServiceName(self):
        """Gets the cloud service name."""
        return "{0}{1}".format(self.getServicePrefix(), self.label)

    def getServiceOSImageName(self):
        """Gets the name of the OS image used to create virtual machines in the service deployment."""
        return self._svc['vm']['os-image']

    def getServiceInstanceCount(self):
        """Gets the number of virtual machines to create in the service deployment."""
        return self._svc['vm']['count']

    def getServiceInstanceRoleSize(self):
        """Gets the role size for each virtual machine in the service deployment."""
        return self._svc['vm']['role-size']

    def getServiceInstanceSshPort(self):
        """Gets the base SSH port value. If this value is N, the k-th web instance will have SSH port number (N+k)."""
        return self._svc['vm']['ssh-port']

    def getGitUser(self):
        """Gets the name of the Git user associated with the target source code repository."""
        return self._svc['git']['user']

    def getGitRepo(self):
        """Gets the name of the Git of the target source code repository."""
        return self._svc['git']['repo']

    def getGitTag(self):
        """Gets the Git tag defining the specific version of the source code."""
        return self._svc['git']['tag']

    def getDjangoInfo(self):
        """Gets the value of the Django secret key."""
        return self._svc['django']

    def getDatabaseAdminPassword(self):
        """Gets the password for the database admin."""
        return self._svc['database']['admin_password']

    def getSslCertificatePath(self):
        """Gets the path of the SSL certificate file to install."""
        return self._svc['ssl']['filename'] if 'ssl' in self._svc else ""

    def getSslCertificateKeyPath(self):
        """Gets the path of the SSL certificate key file to install."""
        return self._svc['ssl']['key-filename'] if 'ssl' in self._svc else ""

    def getSslCertificateInstalledPath(self):
        """Gets the path of the installed SSL certificate file."""
        if len(self.getSslCertificatePath()) > 0:
            return "/etc/ssl/certs/%s" % os.path.basename(self.getSslCertificatePath())
        else:
            return ""

    def getSslCertificateKeyInstalledPath(self):
        """Gets the path of the installed SSL certificate key file."""
        if len(self.getSslCertificateKeyPath()) > 0:
            return "/etc/ssl/private/%s" % os.path.basename(self.getSslCertificateKeyPath())
        else:
            return ""

    def getSslRewriteHosts(self):
        """Gets the list of hosts for which HTTP requests are automatically re-written as HTTPS requests."""
        if 'ssl' in self._svc and 'rewrite-hosts' in self._svc['ssl']:
            return self._svc['ssl']['rewrite-hosts']
        return []

    def getWebHostnames(self):
        """
        Gets the list of web instances. Each name in the list if of the form '<service-name>.cloudapp.net:<port>'.
        """
        service_name = self.getServiceName()  # e.g., codalab
        vm_numbers = range(1, 1 + self.getServiceInstanceCount())  # e.g., prod
        ssh_port = self.getServiceInstanceSshPort()
        return ['{0}.cloudapp.net:{1}'.format(service_name, str(ssh_port + vm_number)) for vm_number in vm_numbers]

    def getBundleServiceGitUser(self):
        """Gets the name of the Git user associated with the target source code repository for bundles."""
        return self._svc['git-bundles']['user'] if 'git-bundles' in self._svc else ""

    def getBundleServiceGitRepo(self):
        """Gets the name of the Git of the target source code repository  for bundles."""
        return self._svc['git-bundles']['repo'] if 'git-bundles' in self._svc else ""

    def getBundleServiceGitTag(self):
        """Gets the Git tag defining the specific version of the source code  for bundles."""
        return self._svc['git-bundles']['tag'] if 'git-bundles' in self._svc else ""

    def getBundleServiceDatabaseName(self):
        """Gets the bundle service database name."""
        return self._svc['database']['bundle_db_name'] if 'bundle_db_name' in self._svc['database'] else ""

    def getBundleServiceDatabaseUser(self):
        """Gets the database username."""
        return self._svc['database']['bundle_user'] if 'bundle_user' in self._svc['database'] else ""

    def getBundleServiceDatabasePassword(self):
        """Gets the password for the database user."""
        return self._svc['database']['bundle_password'] if 'bundle_password' in self._svc['database'] else ""

############################################################

def getWebsiteConfig(config):
    """
    Generates the ~/.codalab/website-config.json file.
    """
    # Use the same allowed hosts for SSL and not SSL
    allowed_hosts = ssl_allowed_hosts = \
        config.getSslRewriteHosts() + \
        ['{0}.cloudapp.net'.format(config.getServiceName())]

    if len(config.getSslCertificateInstalledPath()) > 0:
        bundle_auth_scheme = "https"
    else:
        bundle_auth_scheme = "http"
    bundle_auth_host = allowed_hosts[0]
    bundle_auth_url = "{0}://{1}".format(bundle_auth_scheme, bundle_auth_host)

    return {
        'ALLOWED_HOSTS': allowed_hosts,
        'SSL_PORT': 443,
        'SSL_CERTIFICATE': config.getSslCertificateInstalledPath(),
        'SSL_CERTIFICATE_KEY': config.getSslCertificateKeyInstalledPath(),
        'SSL_ALLOWED_HOSTS': ssl_allowed_hosts,
        'django': config.getDjangoInfo(),
        'DJANGO_USE_UWSGI': True,
        # For generating the bundle_server_config.json file.
        'email': config.getEmailInfo(),
        'admin-email': config.getAdminEmail(),
        'BUNDLE_DB_NAME': config.getBundleServiceDatabaseName(),
        'BUNDLE_DB_USER': config.getBundleServiceDatabaseUser(),
        'BUNDLE_DB_PASSWORD': config.getBundleServiceDatabasePassword(),
        # New relic
        'NEW_RELIC_KEY': config.getNewRelicKey(),
    }

############################################################
# Configuration (run every time)

@task
def using(path):
    """
    Specifies a location for the CodaLab configuration file (e.g., deployment.config)
    """
    env.cfg_path = path

@task
def config(label):
    """
    Reads deployment parameters for the given setup.
    label: Label identifying the desired setup (e.g., prod, test, etc.)
    """
    env.cfg_label = label
    print "Deployment label is:", env.cfg_label
    print "Loading configuration from:", env.cfg_path
    configuration = DeploymentConfig(label, env.cfg_path)
    print "Configuring logger..."
    logging.config.dictConfig(configuration.getLoggerDictConfig())
    env.roledefs = {'web' : configuration.getWebHostnames()}

    # Credentials
    env.user = configuration.getVirtualMachineLogonUsername()
    env.password = configuration.getVirtualMachineLogonPassword()
    env.key_filename = configuration.getServiceCertificateKeyFilename()

    # Repository
    env.git_codalab_tag = configuration.getGitTag()
    env.git_codalab_cli_tag = configuration.getBundleServiceGitTag()
    env.deploy_codalab_worksheets_dir = 'codalab-worksheets'
    env.deploy_codalab_cli_dir = 'codalab-cli'

    env.django_settings_module = 'codalab.settings'
    env.django_configuration = configuration.getDjangoInfo()['configuration']  # Prod or Dev
    env.config_http_port = '80'
    env.config_server_name = "{0}.cloudapp.net".format(configuration.getServiceName())

    env.configuration = True
    env.SHELL_ENV = {}

def setup_env():
    env.SHELL_ENV.update(dict(
        DJANGO_SETTINGS_MODULE=env.django_settings_module,
        DJANGO_CONFIGURATION=env.django_configuration,
        CONFIG_HTTP_PORT=env.config_http_port,
        CONFIG_SERVER_NAME=env.config_server_name,
    ))
    return prefix('source ~/%s/venv/bin/activate' % env.deploy_codalab_worksheets_dir), shell_env(**env.SHELL_ENV)

############################################################
# Installation (one-time)

@roles('web')
@task
def install():
    '''
    Install everything from scratch (idempotent).
    '''
    # Install Linux packages
    sudo('apt-get install -y git xclip python-virtualenv virtualenvwrapper zip')
    sudo('apt-get install -y python-dev libmysqlclient-dev libjpeg-dev')
    sudo('apt-get install -y nginx supervisor')

    # Install Node.js
    # https://nodejs.org/en/download/package-manager/#debian-and-ubuntu-based-linux-distributions
    sudo('curl -sL https://deb.nodesource.com/setup_4.x | bash -')
    sudo('apt-get install -y nodejs')

    # Setup repositories
    def ensure_repo_exists(repo, dest):
        run('[ -e %s ] || git clone %s %s' % (dest, repo, dest))
    ensure_repo_exists('https://github.com/codalab/codalab-worksheets', env.deploy_codalab_worksheets_dir)
    ensure_repo_exists('https://github.com/codalab/codalab-cli', env.deploy_codalab_cli_dir)

    # Initial setup
    with cd(env.deploy_codalab_worksheets_dir):
        run('git checkout %s' % env.git_codalab_tag)
        run('./setup.sh')
    with cd(env.deploy_codalab_cli_dir):
        run('git checkout %s' % env.git_codalab_cli_tag)
        run('./setup.sh server')
        run('venv/bin/pip install MySQL-Python')

    # Deploy!
    _deploy()

@roles('web')
@task
def install_mysql(choice='all'):
    """
    Installs a local instance of MySQL of the web instance. This will only work
    if the number of web instances is one.

    choice: Indicates which assets to create/install:
        'mysql'      -> just install MySQL; don't create the databases
        'bundles_db' -> just create the bundle service database
        'all' or ''  -> install everything
    """
    require('configuration')
    if len(env.roledefs['web']) != 1:
        raise Exception("Task install_mysql requires exactly one web instance.")

    if choice == 'mysql':
        choices = {'mysql'}
    elif choice == 'bundles_db':
        choices = {'bundles_db'}
    elif choice == 'all':
        choices = {'mysql', 'bundles_db'}
    else:
        raise ValueError("Invalid choice: %s. Valid choices are: 'build', 'web' or 'all'." % (choice))

    configuration = DeploymentConfig(env.cfg_label, env.cfg_path)
    dba_password = configuration.getDatabaseAdminPassword()

    if 'mysql' in choices:
        sudo('DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server')
        sudo('mysqladmin -u root password {0}'.format(dba_password))

    if 'bundles_db' in choices:
        db_name = configuration.getBundleServiceDatabaseName()
        db_user = configuration.getBundleServiceDatabaseUser()
        db_password = configuration.getBundleServiceDatabasePassword()
        cmds = ["create database {0};".format(db_name),
                "create user '{0}'@'localhost' IDENTIFIED BY '{1}';".format(db_user, db_password),
                "GRANT ALL PRIVILEGES ON {0}.* TO '{1}'@'localhost' WITH GRANT OPTION;".format(db_name, db_user)]
        run('mysql --user=root --password={0} --execute="{1}"'.format(dba_password, " ".join(cmds)))


############################################################
# Deployment (after each update)

@roles('web')
@task
def supervisor(command):
    """
    Starts the supervisor on the web instances.
    """
    env_prefix, env_shell = setup_env()
    with env_prefix, env_shell, cd(env.deploy_codalab_worksheets_dir):
        if command == 'start':
            run('mkdir -p ~/logs')
            run('supervisord -c codalab/config/generated/supervisor.conf')
        elif command == 'stop':
            run('supervisorctl -c codalab/config/generated/supervisor.conf stop all')
            run('supervisorctl -c codalab/config/generated/supervisor.conf shutdown')
        elif command == 'restart':
            run('supervisorctl -c codalab/config/generated/supervisor.conf restart all')
        else:
            raise 'Unknown command: %s' % command

@roles('web')
@task
def nginx_restart():
    """
    Restarts nginx on the web server.
    """
    sudo('/etc/init.d/nginx restart')

# Maintenance and diagnostics
@roles('web')
@task
def maintenance(mode):
    """
    Begin or end maintenance (mode is 'begin' or 'end')
    """
    modes = {'begin': '1', 'end' : '0'}
    if mode not in modes:
        print "Invalid mode. Valid values are 'begin' or 'end'"
        sys.exit(1)

    require('configuration')
    env.SHELL_ENV['MAINTENANCE_MODE'] = modes[mode]

    # Update nginx.conf
    env_prefix, env_shell = setup_env()
    with env_prefix, env_shell, cd(env.deploy_codalab_worksheets_dir), cd('codalab'):
        run('python manage.py config_gen')

    nginx_restart()

@roles('web')
@task
def deploy():
    """
    Put a maintenance message, deploy, and then restore website.
    """
    maintenance('begin')
    supervisor('stop')
    _deploy()
    supervisor('start')
    maintenance('end')

def _deploy():
    # Update website
    env_prefix, env_shell = setup_env()
    with env_prefix, env_shell, cd(env.deploy_codalab_worksheets_dir):
        run('git fetch')
        run('git checkout %s' % env.git_codalab_tag)
        run('git pull')
        run('./setup.sh')

    # Update bundle service
    with cd(env.deploy_codalab_cli_dir):
        run('git fetch')
        run('git checkout %s' % env.git_codalab_cli_tag)
        run('git pull')
        run('./setup.sh server')
        run('venv/bin/pip install MySQL-Python')
        run('venv/bin/alembic upgrade head')

    # Create local.py
    cfg = DeploymentConfig(env.cfg_label, env.cfg_path)
    buf = StringIO()
    json.dump(getWebsiteConfig(cfg), buf, sort_keys=True, indent=4, separators=(',', ': '))
    buf.write('\n')
    put(buf, '.codalab/website-config.json')

    # Update the website configuration
    env_prefix, env_shell = setup_env()
    with env_prefix, env_shell, cd(env.deploy_codalab_worksheets_dir), cd('codalab'):
        # Generate configuration files (bundle_server_config, nginx, etc.)
        run('python manage.py config_gen')
        # Create static pages
        run('python manage.py collectstatic --noinput')
        # Put configuration files in place
        run('mkdir -p ~/.codalab')
        run('ln -sf `pwd`/config/generated/bundle_server_config.json ~/.codalab/config.json')
        sudo('ln -sf `pwd`/config/generated/nginx.conf /etc/nginx/sites-enabled/codalab.conf')
        sudo('ln -sf `pwd`/config/generated/supervisor.conf /etc/supervisor/conf.d/codalab.conf')
        # Setup new relic
        run('newrelic-admin generate-config %s newrelic.ini' % cfg.getNewRelicKey())

    # Set up the bundles database.
    with cd(env.deploy_codalab_cli_dir):
        run('scripts/create-root-user.py %s' % cfg.getDatabaseAdminPassword())

    # Build and install steps for JavaScript application
    with cd(env.deploy_codalab_worksheets_dir), cd('codalab/apps/web'):
        # Update NPM packages
        run('npm install')
        # Build static files (e.g. JSX and LESS)
        run('npm run build')
        # Install third-party dependencies
        run('npm run bower')

    # Install SSL certficates (/etc/ssl/certs/)
    require('configuration')
    if (len(cfg.getSslCertificateInstalledPath()) > 0) and (len(cfg.getSslCertificateKeyInstalledPath()) > 0):
        put(cfg.getSslCertificatePath(), cfg.getSslCertificateInstalledPath(), use_sudo=True)
        put(cfg.getSslCertificateKeyPath(), cfg.getSslCertificateKeyInstalledPath(), use_sudo=True)
    else:
        logger.info("Skipping certificate installation because both files are not specified.")
