set :application, 'metadata_server'

set :repo_url, 'git@github.com:harvard-library/metadata_server.git'
set :scm, :git
ask :branch, proc { `git rev-parse --abbrev-ref HEAD`.chomp }

set :deploy_to, '/opt/django_projects'
set :current_dir, 'metadata_server'
set :releases_path, 'mds_releases'
set :shared_path, 'mds_shared'

# Django stuff
set :django_settings_dir, 'metadata_server/settings'
set :pip_requirements, 'requirements.txt'
set :wsgi_file, 'metadata_server/wsgi.py'

# set :format, :pretty
# set :log_level, :debug
# set :pty, true

set :linked_files, %w{.env metadata_server/settings.py db.sqlite3}

# set :default_env, { path: "/opt/ruby/bin:$PATH" }

set :keep_releases, 3

namespace :deploy do
  after :finishing, 'deploy:cleanup'
end
