set :stage, :production
set :django_settings, 'production'

# Simple Role Syntax
# ==================
# Supports bulk-adding hosts to roles, the primary
# server in each group is considered to be the first
# unless any hosts have the primary property set.
role :app, %w{pobocks@192.168.148.135}
