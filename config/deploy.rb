set :application, 'metadata_server'

set :repo_url, 'git@github.com:harvard-library/metadata_server.git'
set :scm, :git
ask :branch, proc { `git rev-parse --abbrev-ref HEAD`.chomp }

set :deploy_to, '/opt/django_projects/metadata_server'


# Django stuff
set :django_settings_dir, 'metadata_server'
set :pip_requirements, 'requirements.txt'
set :wsgi_file, 'metadata_server/wsgi.py'

# set :format, :pretty
# set :log_level, :debug
set :pty, true

set :linked_files, %w{.env db.sqlite3}

set :shared_virtualenv, true

# set :default_env, { path: "/opt/ruby/bin:$PATH" }

set :keep_releases, 3

set :default_env, {'LD_LIBRARY_PATH' => "/usr/local/lib"}

namespace :deploy do
  desc 'Restart web server'
  task :restart do
    on roles(:app), in: :sequence, wait: 5 do
      sudo "/usr/bin/systemctl restart httpd.service"
    end
  end

  after :publishing, 'deploy:restart'

  after :finishing, 'deploy:cleanup'
end
